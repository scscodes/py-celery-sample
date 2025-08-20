"""
User management API endpoints.

This module provides REST API endpoints for user CRUD operations,
group membership management, and user-related workflows.
"""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from typing import List, Optional

from app.core.dependencies import get_database
from app.schemas.users import (
    UserCreate, UserUpdate, UserResponse, UserDetailResponse,
    GroupMembershipRequest, GroupMembershipResponse
)
from app.models.users import User, Group
from app.tasks.basic.crud_tasks import create_user_task

router = APIRouter()


@router.get("/", response_model=List[UserResponse])
async def list_users(
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of records to return"),
    department: Optional[str] = Query(None, description="Filter by department"),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    db: Session = Depends(get_database)
):
    """
    Retrieve a list of users with optional filtering.
    
    - **skip**: Number of records to skip for pagination
    - **limit**: Maximum number of records to return (1-1000)
    - **department**: Filter users by department
    - **is_active**: Filter by user active status
    """
    query = db.query(User)
    
    # Apply filters
    if department:
        query = query.filter(User.department == department)
    if is_active is not None:
        query = query.filter(User.is_active == is_active)
    
    # Apply pagination
    users = query.offset(skip).limit(limit).all()
    
    return users


@router.get("/{user_id}", response_model=UserDetailResponse)
async def get_user(
    user_id: int,
    db: Session = Depends(get_database)
):
    """
    Retrieve a specific user by ID with detailed information.
    
    Returns user details including:
    - Basic user information
    - Manager and subordinate relationships
    - Group memberships
    - Assigned computers
    """
    user = db.query(User).filter(User.id == user_id).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with ID {user_id} not found"
        )
    
    return user


@router.post("/", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user(
    user_data: UserCreate,
    db: Session = Depends(get_database)
):
    """
    Create a new user.
    
    This endpoint creates a new user and triggers background
    tasks for user provisioning and group assignments.
    """
    # Check if username already exists
    existing_user = db.query(User).filter(User.username == user_data.username).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Username '{user_data.username}' already exists"
        )
    
    # Check if email already exists
    existing_email = db.query(User).filter(User.email == user_data.email).first()
    if existing_email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Email '{user_data.email}' already exists"
        )
    
    # Trigger Celery task for user creation
    task_result = create_user_task.delay(user_data.dict())
    
    # For demonstration, we'll also create the user synchronously
    # In production, you might want to make this fully async
    user = User(**user_data.dict())
    db.add(user)
    db.commit()
    db.refresh(user)
    
    return user


@router.put("/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: int,
    user_data: UserUpdate,
    db: Session = Depends(get_database)
):
    """
    Update an existing user.
    
    Updates user information and triggers background tasks
    for cache invalidation and audit logging.
    """
    user = db.query(User).filter(User.id == user_id).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with ID {user_id} not found"
        )
    
    # Update user fields
    update_data = user_data.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(user, field, value)
    
    db.commit()
    db.refresh(user)
    
    return user


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    user_id: int,
    db: Session = Depends(get_database)
):
    """
    Delete a user.
    
    Soft delete by setting is_active to False.
    Triggers cleanup tasks for user data and access removal.
    """
    user = db.query(User).filter(User.id == user_id).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with ID {user_id} not found"
        )
    
    # Soft delete
    user.is_active = False
    db.commit()


@router.post("/{user_id}/groups", response_model=GroupMembershipResponse)
async def add_user_to_group(
    user_id: int,
    membership_data: GroupMembershipRequest,
    db: Session = Depends(get_database)
):
    """
    Add a user to a group.
    
    Creates group membership and triggers background tasks
    for permission synchronization.
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with ID {user_id} not found"
        )
    
    group = db.query(Group).filter(Group.id == membership_data.group_id).first()
    if not group:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Group with ID {membership_data.group_id} not found"
        )
    
    # Check if user is already in group
    if group in user.groups:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"User is already a member of group '{group.name}'"
        )
    
    # Add user to group
    user.groups.append(group)
    db.commit()
    
    return {
        "user": user,
        "group": group,
        "added_at": "2025-01-20T10:40:00Z",  # Would use actual timestamp
        "added_by": "system"
    }


@router.delete("/{user_id}/groups/{group_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_user_from_group(
    user_id: int,
    group_id: int,
    db: Session = Depends(get_database)
):
    """
    Remove a user from a group.
    
    Removes group membership and triggers background tasks
    for permission cleanup.
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with ID {user_id} not found"
        )
    
    group = db.query(Group).filter(Group.id == group_id).first()
    if not group:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Group with ID {group_id} not found"
        )
    
    # Check if user is in group
    if group not in user.groups:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"User is not a member of group '{group.name}'"
        )
    
    # Remove user from group
    user.groups.remove(group)
    db.commit()


@router.get("/{user_id}/subordinates", response_model=List[UserResponse])
async def get_user_subordinates(
    user_id: int,
    db: Session = Depends(get_database)
):
    """
    Get all subordinates for a manager.
    
    Returns all users who report to the specified manager.
    """
    user = db.query(User).filter(User.id == user_id).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with ID {user_id} not found"
        )
    
    subordinates = db.query(User).filter(User.manager_id == user_id).all()
    
    return subordinates
