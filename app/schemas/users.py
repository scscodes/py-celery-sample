"""
Pydantic schemas for User and Group models.

This module defines request/response schemas for FastAPI endpoints
that handle user and group operations, providing validation and serialization.
"""

from pydantic import BaseModel, EmailStr, validator
from typing import Optional, List
from datetime import datetime


# Base schemas for common attributes
class UserBase(BaseModel):
    """Base User schema with common attributes."""
    username: str
    email: EmailStr
    first_name: str
    last_name: str
    display_name: Optional[str] = None
    department: Optional[str] = None
    title: Optional[str] = None
    employee_id: Optional[str] = None
    phone: Optional[str] = None
    office_location: Optional[str] = None
    is_active: bool = True


class GroupBase(BaseModel):
    """Base Group schema with common attributes."""
    name: str
    description: Optional[str] = None
    group_type: str = "security"
    scope: str = "global"
    managed_by: Optional[str] = None
    permissions: Optional[str] = None
    is_active: bool = True


# Request schemas (for creating/updating)
class UserCreate(UserBase):
    """Schema for creating a new user."""
    manager_id: Optional[int] = None
    
    @validator('username')
    def username_alphanumeric(cls, v):
        """Validate username contains only alphanumeric characters and underscores."""
        if not v.replace('_', '').replace('.', '').isalnum():
            raise ValueError('Username must contain only alphanumeric characters, dots, and underscores')
        return v.lower()


class UserUpdate(BaseModel):
    """Schema for updating an existing user."""
    email: Optional[EmailStr] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    display_name: Optional[str] = None
    department: Optional[str] = None
    title: Optional[str] = None
    manager_id: Optional[int] = None
    phone: Optional[str] = None
    office_location: Optional[str] = None
    is_active: Optional[bool] = None
    is_locked: Optional[bool] = None


class GroupCreate(GroupBase):
    """Schema for creating a new group."""
    parent_group_id: Optional[int] = None


class GroupUpdate(BaseModel):
    """Schema for updating an existing group."""
    name: Optional[str] = None
    description: Optional[str] = None
    managed_by: Optional[str] = None
    permissions: Optional[str] = None
    is_active: Optional[bool] = None
    parent_group_id: Optional[int] = None


# Basic response schema without relationships (Phase 1: Stability)
class UserResponse(UserBase):
    """Basic user API response without relationships."""
    id: int
    manager_id: Optional[int]
    is_locked: bool
    password_last_changed: Optional[datetime]
    last_login: Optional[datetime]
    failed_login_attempts: int
    created_at: datetime
    updated_at: datetime
    
    # Computed properties - safely handled
    full_name: Optional[str] = None
    is_manager: Optional[bool] = None
    
    class Config:
        from_attributes = True
        
    @validator('full_name', always=True, pre=False)
    def set_full_name(cls, v, values):
        """Set full name from first and last name if not already set."""
        if v is not None:
            return v
        first_name = values.get('first_name', '')
        last_name = values.get('last_name', '') 
        return f"{first_name} {last_name}".strip() if first_name or last_name else None
        
    @validator('is_manager', always=True, pre=False)
    def set_is_manager(cls, v, values):
        """Safely set is_manager property."""
        if v is not None:
            return v
        return False  # Default to False for basic response


class GroupResponse(GroupBase):
    """Schema for group API responses."""
    id: int
    parent_group_id: Optional[int]
    distinguished_name: Optional[str]
    created_at: datetime
    updated_at: datetime
    
    # Computed properties - will be populated from SQLAlchemy model properties
    member_count: Optional[int] = None
    is_nested_group: Optional[bool] = None
    
    class Config:
        from_attributes = True


# Schemas for relationships
class UserSummary(BaseModel):
    """Summary schema for user references in other responses."""
    id: int
    username: str
    full_name: str
    email: EmailStr
    department: Optional[str]
    is_active: bool
    
    class Config:
        from_attributes = True


class GroupSummary(BaseModel):
    """Summary schema for group references in other responses."""
    id: int
    name: str
    group_type: str
    description: Optional[str]
    is_active: bool
    
    class Config:
        from_attributes = True


# Extended response schemas with safe relationship handling
class UserDetailResponse(UserResponse):
    """Detailed user response with safe relationship handling."""
    # Use simple references instead of full nested objects initially
    manager: Optional['UserSummary'] = None
    subordinates: List['UserSummary'] = []
    groups: List['GroupSummary'] = []
    
    # Add safe computed fields
    subordinate_count: int = 0
    group_count: int = 0
    
    class Config:
        from_attributes = True
        
    @validator('subordinates', always=True, pre=False)
    def ensure_subordinates_list(cls, v):
        """Ensure subordinates is always a list, never None."""
        return v if v is not None else []
        
    @validator('groups', always=True, pre=False) 
    def ensure_groups_list(cls, v):
        """Ensure groups is always a list, never None."""
        return v if v is not None else []
        
    @validator('subordinate_count', always=True, pre=False)
    def set_subordinate_count(cls, v, values):
        """Set subordinate count from subordinates list."""
        subordinates = values.get('subordinates', [])
        return len(subordinates) if subordinates else 0
        
    @validator('group_count', always=True, pre=False)
    def set_group_count(cls, v, values):
        """Set group count from groups list."""
        groups = values.get('groups', [])
        return len(groups) if groups else 0


class GroupDetailResponse(GroupResponse):
    """Detailed group response with safe relationship handling."""
    parent_group: Optional['GroupSummary'] = None
    child_groups: List['GroupSummary'] = []
    members: List['UserSummary'] = []
    
    # Add safe computed fields
    child_group_count: int = 0
    
    class Config:
        from_attributes = True
        
    @validator('child_groups', always=True, pre=False)
    def ensure_child_groups_list(cls, v):
        """Ensure child_groups is always a list, never None."""
        return v if v is not None else []
        
    @validator('members', always=True, pre=False)
    def ensure_members_list(cls, v):
        """Ensure members is always a list, never None."""
        return v if v is not None else []
        
    @validator('child_group_count', always=True, pre=False)
    def set_child_group_count(cls, v, values):
        """Set child group count from child_groups list."""
        child_groups = values.get('child_groups', [])
        return len(child_groups) if child_groups else 0


# Membership management schemas
class GroupMembershipRequest(BaseModel):
    """Schema for adding/removing users from groups."""
    user_id: int
    group_id: int


class GroupMembershipResponse(BaseModel):
    """Schema for group membership operation responses."""
    user: UserSummary
    group: GroupSummary
    added_at: datetime
    added_by: Optional[str]
    
    class Config:
        from_attributes = True
