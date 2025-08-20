"""
User Domain Service

This service handles all user-related business logic including user management,
authentication, authorization, group memberships, and user lifecycle operations.
"""

import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import re

from app.services.base import BaseService, ServiceResult, service_method, ValidationError, NotFoundError, ConflictError
from app.tasks.basic.crud_tasks import create_user, get_user, update_user, delete_user, get_users
from app.tasks.basic.cache_tasks import cache_user_data, get_cached_user
from app.tasks.enterprise.user_onboarding import initiate_employee_onboarding
from app.tasks.orchestration.workflow_tasks import linear_workflow

logger = logging.getLogger(__name__)


class UserService(BaseService):
    """Service for user management and authentication."""
    
    def __init__(self):
        super().__init__("UserService")
        self._password_policy = {
            "min_length": 8,
            "require_uppercase": True,
            "require_lowercase": True,
            "require_numbers": True,
            "require_special_chars": True,
            "max_age_days": 90
        }
    
    @service_method
    async def create_user(self, user_data: Dict[str, Any], trigger_onboarding: bool = True) -> ServiceResult[Dict[str, Any]]:
        """Create a new user with validation and optional onboarding."""
        
        # Validate user data
        validation_result = self._validate_user_data(user_data)
        if not validation_result.success:
            return validation_result
        
        # Check for existing user
        existing_user = await self._check_user_exists(user_data.get("username"), user_data.get("email"))
        if existing_user:
            return ServiceResult.error_result(
                ConflictError("User already exists", existing_user)
            )
        
        # Enrich user data with defaults
        enriched_data = self._enrich_user_data(user_data)
        
        try:
            # Create user via Celery task
            task_result = create_user.delay(enriched_data)
            created_user = task_result.get(timeout=30)
            
            # Cache user data
            cache_user_data.delay(created_user["user_id"], created_user)
            
            # Trigger onboarding workflow if requested
            if trigger_onboarding and enriched_data.get("employee_type"):
                onboarding_result = initiate_employee_onboarding.delay({
                    "employee_id": created_user["user_id"],
                    "first_name": created_user["first_name"],
                    "last_name": created_user["last_name"],
                    "email": created_user["email"],
                    "department": created_user.get("department", "general"),
                    "role": created_user.get("role", "employee"),
                    "manager_id": created_user.get("manager_id"),
                    "start_date": created_user.get("start_date", datetime.utcnow().isoformat()),
                    "employee_type": enriched_data["employee_type"]
                })
                
                created_user["onboarding_task_id"] = onboarding_result.id
            
            # Emit user created event
            await self._emit_user_event("user_created", created_user)
            
            return ServiceResult.success_result(
                created_user,
                metadata={"onboarding_triggered": trigger_onboarding}
            )
            
        except Exception as e:
            self.logger.error(f"Failed to create user: {e}")
            return ServiceResult.from_exception(e)
    
    @service_method
    async def get_user(self, user_id: str, include_groups: bool = False, use_cache: bool = True) -> ServiceResult[Dict[str, Any]]:
        """Get user by ID with optional group information."""
        
        try:
            user_data = None
            
            # Try cache first if enabled
            if use_cache:
                cache_result = get_cached_user.delay(user_id)
                try:
                    user_data = cache_result.get(timeout=5)
                except:
                    pass  # Cache miss or timeout
            
            # Fetch from database if not in cache
            if not user_data:
                task_result = get_user.delay(user_id)
                user_data = task_result.get(timeout=30)
                
                if not user_data:
                    return ServiceResult.error_result(
                        NotFoundError("User", user_id)
                    )
                
                # Update cache
                if use_cache:
                    cache_user_data.delay(user_id, user_data)
            
            # Include group information if requested
            if include_groups:
                user_data["groups"] = await self._get_user_groups(user_id)
                user_data["subordinates"] = await self._get_user_subordinates(user_id)
            
            return ServiceResult.success_result(user_data)
            
        except Exception as e:
            self.logger.error(f"Failed to get user {user_id}: {e}")
            return ServiceResult.from_exception(e)
    
    @service_method
    async def update_user(self, user_id: str, update_data: Dict[str, Any], validate_changes: bool = True) -> ServiceResult[Dict[str, Any]]:
        """Update user with validation and change tracking."""
        
        # Get current user data
        current_user_result = await self.get_user(user_id, use_cache=False)
        if not current_user_result.success:
            return current_user_result
        
        current_user = current_user_result.data
        
        # Validate update data
        if validate_changes:
            validation_result = self._validate_user_update(current_user, update_data)
            if not validation_result.success:
                return validation_result
        
        # Prepare update with change tracking
        update_with_metadata = update_data.copy()
        update_with_metadata["updated_at"] = datetime.utcnow().isoformat()
        update_with_metadata["updated_by"] = update_data.get("updated_by", "system")
        
        # Track significant changes
        significant_changes = self._identify_significant_changes(current_user, update_data)
        
        try:
            # Update user via Celery task
            task_result = update_user.delay(user_id, update_with_metadata)
            updated_user = task_result.get(timeout=30)
            
            # Clear cache
            self._clear_user_cache(user_id)
            
            # Handle significant changes
            if significant_changes:
                await self._handle_significant_user_changes(user_id, significant_changes, current_user, updated_user)
            
            # Emit user updated event
            await self._emit_user_event("user_updated", updated_user, {
                "previous_data": current_user,
                "changes": significant_changes
            })
            
            return ServiceResult.success_result(
                updated_user,
                metadata={"significant_changes": significant_changes}
            )
            
        except Exception as e:
            self.logger.error(f"Failed to update user {user_id}: {e}")
            return ServiceResult.from_exception(e)
    
    @service_method
    async def delete_user(self, user_id: str, soft_delete: bool = True, transfer_ownership: str = None) -> ServiceResult[Dict[str, Any]]:
        """Delete user with cleanup and ownership transfer."""
        
        # Get user to be deleted
        user_result = await self.get_user(user_id, include_groups=True)
        if not user_result.success:
            return user_result
        
        user_data = user_result.data
        
        try:
            # Handle ownership transfer if specified
            if transfer_ownership:
                await self._transfer_user_ownership(user_id, transfer_ownership)
            
            # Remove from groups
            if user_data.get("groups"):
                await self._remove_user_from_all_groups(user_id)
            
            # Handle subordinates
            if user_data.get("subordinates"):
                await self._reassign_subordinates(user_id, transfer_ownership)
            
            # Delete or deactivate user
            if soft_delete:
                # Soft delete - deactivate account
                deactivation_data = {
                    "status": "inactive",
                    "deactivated_at": datetime.utcnow().isoformat(),
                    "deactivated_by": transfer_ownership or "system"
                }
                task_result = update_user.delay(user_id, deactivation_data)
                result_user = task_result.get(timeout=30)
                result_user["deleted"] = False
            else:
                # Hard delete
                task_result = delete_user.delay(user_id)
                task_result.get(timeout=30)
                result_user = {"user_id": user_id, "deleted": True}
            
            # Clear cache
            self._clear_user_cache(user_id)
            
            # Emit user deleted event
            await self._emit_user_event("user_deleted", result_user, {
                "soft_delete": soft_delete,
                "transfer_ownership": transfer_ownership
            })
            
            return ServiceResult.success_result(result_user)
            
        except Exception as e:
            self.logger.error(f"Failed to delete user {user_id}: {e}")
            return ServiceResult.from_exception(e)
    
    @service_method
    async def search_users(self, filters: Dict[str, Any], pagination: Dict[str, Any] = None) -> ServiceResult[Dict[str, Any]]:
        """Search users with filters and pagination."""
        
        try:
            # Prepare search parameters
            search_params = {
                "filters": filters,
                "limit": pagination.get("limit", 50) if pagination else 50,
                "offset": pagination.get("offset", 0) if pagination else 0,
                "sort_by": pagination.get("sort_by", "created_at") if pagination else "created_at",
                "sort_order": pagination.get("sort_order", "desc") if pagination else "desc"
            }
            
            # Execute search via Celery task
            task_result = get_users.delay(search_params)
            search_results = task_result.get(timeout=30)
            
            return ServiceResult.success_result(search_results)
            
        except Exception as e:
            self.logger.error(f"Failed to search users: {e}")
            return ServiceResult.from_exception(e)
    
    @service_method
    async def authenticate_user(self, username: str, password: str) -> ServiceResult[Dict[str, Any]]:
        """Authenticate user credentials."""
        
        try:
            # Get user by username
            user_search = await self.search_users({"username": username})
            if not user_search.success or not user_search.data.get("users"):
                return ServiceResult.error_result(
                    NotFoundError("User", username)
                )
            
            user = user_search.data["users"][0]
            
            # Check if user is active
            if user.get("status") != "active":
                return ServiceResult.error_result(
                    ValidationError("User account is not active")
                )
            
            # Validate password (simplified - in production use proper hashing)
            if not self._verify_password(password, user.get("password_hash")):
                # Log failed attempt
                await self._log_failed_login(user["user_id"], username)
                return ServiceResult.error_result(
                    ValidationError("Invalid credentials")
                )
            
            # Check password age
            password_age = self._get_password_age(user)
            if password_age > self._password_policy["max_age_days"]:
                user["password_expired"] = True
            
            # Update last login
            update_user.delay(user["user_id"], {
                "last_login": datetime.utcnow().isoformat(),
                "login_count": user.get("login_count", 0) + 1
            })
            
            # Remove sensitive data from response
            auth_result = {k: v for k, v in user.items() if k not in ["password_hash", "password_salt"]}
            
            # Emit authentication event
            await self._emit_user_event("user_authenticated", auth_result)
            
            return ServiceResult.success_result(auth_result)
            
        except Exception as e:
            self.logger.error(f"Failed to authenticate user {username}: {e}")
            return ServiceResult.from_exception(e)
    
    @service_method
    async def change_password(self, user_id: str, old_password: str, new_password: str) -> ServiceResult[bool]:
        """Change user password with validation."""
        
        try:
            # Get current user
            user_result = await self.get_user(user_id)
            if not user_result.success:
                return user_result
            
            user = user_result.data
            
            # Verify old password
            if not self._verify_password(old_password, user.get("password_hash")):
                return ServiceResult.error_result(
                    ValidationError("Current password is incorrect")
                )
            
            # Validate new password
            password_validation = self._validate_password(new_password)
            if not password_validation["valid"]:
                return ServiceResult.error_result(
                    ValidationError(f"Password policy violation: {', '.join(password_validation['errors'])}")
                )
            
            # Hash new password
            password_hash, salt = self._hash_password(new_password)
            
            # Update password
            update_result = update_user.delay(user_id, {
                "password_hash": password_hash,
                "password_salt": salt,
                "password_changed_at": datetime.utcnow().isoformat(),
                "password_change_required": False
            })
            update_result.get(timeout=30)
            
            # Clear cache
            self._clear_user_cache(user_id)
            
            # Emit password changed event
            await self._emit_user_event("password_changed", {"user_id": user_id})
            
            return ServiceResult.success_result(True)
            
        except Exception as e:
            self.logger.error(f"Failed to change password for user {user_id}: {e}")
            return ServiceResult.from_exception(e)
    
    # Helper methods
    
    def _validate_user_data(self, user_data: Dict[str, Any]) -> ServiceResult[bool]:
        """Validate user data for creation."""
        errors = []
        
        # Required fields
        required_fields = ["username", "email", "first_name", "last_name"]
        for field in required_fields:
            if not user_data.get(field):
                errors.append(f"Missing required field: {field}")
        
        # Username validation
        username = user_data.get("username", "")
        if not re.match(r"^[a-zA-Z0-9._-]+$", username):
            errors.append("Username contains invalid characters")
        
        if len(username) < 3 or len(username) > 50:
            errors.append("Username must be between 3 and 50 characters")
        
        # Email validation
        email = user_data.get("email", "")
        if not re.match(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$", email):
            errors.append("Invalid email format")
        
        # Password validation if provided
        if "password" in user_data:
            password_validation = self._validate_password(user_data["password"])
            if not password_validation["valid"]:
                errors.extend(password_validation["errors"])
        
        if errors:
            return ServiceResult.error_result(
                ValidationError(f"Validation failed: {', '.join(errors)}")
            )
        
        return ServiceResult.success_result(True)
    
    def _validate_password(self, password: str) -> Dict[str, Any]:
        """Validate password against policy."""
        errors = []
        policy = self._password_policy
        
        if len(password) < policy["min_length"]:
            errors.append(f"Minimum length is {policy['min_length']} characters")
        
        if policy["require_uppercase"] and not re.search(r"[A-Z]", password):
            errors.append("Must contain at least one uppercase letter")
        
        if policy["require_lowercase"] and not re.search(r"[a-z]", password):
            errors.append("Must contain at least one lowercase letter")
        
        if policy["require_numbers"] and not re.search(r"\d", password):
            errors.append("Must contain at least one number")
        
        if policy["require_special_chars"] and not re.search(r"[!@#$%^&*(),.?\":{}|<>]", password):
            errors.append("Must contain at least one special character")
        
        return {
            "valid": len(errors) == 0,
            "errors": errors
        }
    
    def _enrich_user_data(self, user_data: Dict[str, Any]) -> Dict[str, Any]:
        """Enrich user data with defaults and computed fields."""
        enriched = user_data.copy()
        
        # Add default values
        enriched.setdefault("status", "active")
        enriched.setdefault("created_at", datetime.utcnow().isoformat())
        enriched.setdefault("role", "user")
        enriched.setdefault("department", "general")
        
        # Generate password hash if password provided
        if "password" in enriched:
            password_hash, salt = self._hash_password(enriched["password"])
            enriched["password_hash"] = password_hash
            enriched["password_salt"] = salt
            enriched["password_changed_at"] = datetime.utcnow().isoformat()
            del enriched["password"]  # Remove plain text password
        
        # Generate display name
        enriched["display_name"] = f"{enriched['first_name']} {enriched['last_name']}"
        
        return enriched
    
    async def _check_user_exists(self, username: str, email: str) -> Optional[str]:
        """Check if user already exists by username or email."""
        try:
            # Check by username
            username_search = await self.search_users({"username": username})
            if username_search.success and username_search.data.get("users"):
                return "username"
            
            # Check by email
            email_search = await self.search_users({"email": email})
            if email_search.success and email_search.data.get("users"):
                return "email"
            
            return None
        except:
            return None
    
    def _hash_password(self, password: str) -> tuple[str, str]:
        """Hash password with salt (simplified implementation)."""
        import hashlib
        import secrets
        
        salt = secrets.token_hex(16)
        password_hash = hashlib.pbkdf2_hmac('sha256', password.encode(), salt.encode(), 100000)
        return password_hash.hex(), salt
    
    def _verify_password(self, password: str, stored_hash: str) -> bool:
        """Verify password against stored hash (simplified implementation)."""
        # In production, implement proper password verification
        return True  # Simplified for demo
    
    def _get_password_age(self, user: Dict[str, Any]) -> int:
        """Get password age in days."""
        password_changed = user.get("password_changed_at")
        if not password_changed:
            return 999  # Very old if no change date
        
        changed_date = datetime.fromisoformat(password_changed.replace('Z', '+00:00'))
        return (datetime.utcnow() - changed_date).days
    
    async def _emit_user_event(self, event_type: str, user_data: Dict[str, Any], metadata: Dict[str, Any] = None):
        """Emit user-related events."""
        # In production, implement proper event emission
        self.logger.info(f"User event: {event_type} for user {user_data.get('user_id', 'unknown')}")
    
    def _clear_user_cache(self, user_id: str):
        """Clear user cache."""
        # Implementation would clear Redis cache
        pass
    
    # Placeholder methods for group and subordinate management
    async def _get_user_groups(self, user_id: str) -> List[Dict[str, Any]]:
        """Get user's group memberships."""
        return []  # Implemented by GroupService integration
    
    async def _get_user_subordinates(self, user_id: str) -> List[Dict[str, Any]]:
        """Get user's subordinates."""
        return []  # Implemented by organizational hierarchy
    
    async def _remove_user_from_all_groups(self, user_id: str):
        """Remove user from all groups."""
        pass  # Implemented by GroupService integration
    
    async def _reassign_subordinates(self, user_id: str, new_manager_id: str):
        """Reassign subordinates to new manager."""
        pass  # Implemented by organizational hierarchy
    
    async def _transfer_user_ownership(self, user_id: str, new_owner_id: str):
        """Transfer ownership of user's resources."""
        pass  # Implemented by asset/resource management
    
    def _validate_user_update(self, current_user: Dict[str, Any], update_data: Dict[str, Any]) -> ServiceResult[bool]:
        """Validate user update data."""
        # Implementation for update validation
        return ServiceResult.success_result(True)
    
    def _identify_significant_changes(self, current_user: Dict[str, Any], update_data: Dict[str, Any]) -> List[str]:
        """Identify significant changes that require special handling."""
        significant_fields = ["email", "role", "department", "manager_id", "status"]
        changes = []
        
        for field in significant_fields:
            if field in update_data and update_data[field] != current_user.get(field):
                changes.append(field)
        
        return changes
    
    async def _handle_significant_user_changes(self, user_id: str, changes: List[str], old_data: Dict[str, Any], new_data: Dict[str, Any]):
        """Handle significant user changes with appropriate workflows."""
        # Implementation for handling significant changes
        pass
    
    async def _log_failed_login(self, user_id: str, username: str):
        """Log failed login attempt."""
        self.logger.warning(f"Failed login attempt for user {username} (ID: {user_id})")
