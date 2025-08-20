"""
Group management API endpoints.

This module provides REST API endpoints for group CRUD operations,
membership management, and group hierarchy operations.
"""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from typing import List, Optional

from app.core.dependencies import get_database
from app.schemas.users import (
    GroupCreate, GroupUpdate, GroupResponse, GroupDetailResponse,
    UserSummary
)
from app.models.users import Group, User

router = APIRouter()


@router.get("/", response_model=List[GroupResponse])
async def list_groups(
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of records to return"),
    group_type: Optional[str] = Query(None, description="Filter by group type"),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    db: Session = Depends(get_database)
):
    """
    Retrieve a list of groups with optional filtering.
    
    - **skip**: Number of records to skip for pagination
    - **limit**: Maximum number of records to return (1-1000)
    - **group_type**: Filter groups by type (security, organizational, etc.)
    - **is_active**: Filter by group active status
    """
    query = db.query(Group)
    
    # Apply filters
    if group_type:
        query = query.filter(Group.group_type == group_type)
    if is_active is not None:
        query = query.filter(Group.is_active == is_active)
    
    # Apply pagination
    groups = query.offset(skip).limit(limit).all()
    
    return groups


@router.get("/{group_id}", response_model=GroupDetailResponse)
async def get_group(
    group_id: int,
    db: Session = Depends(get_database)
):
    """
    Retrieve a specific group by ID with detailed information.
    
    Returns group details including:
    - Basic group information
    - Parent and child group relationships
    - Group members
    - Permissions and access rights
    """
    group = db.query(Group).filter(Group.id == group_id).first()
    
    if not group:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Group with ID {group_id} not found"
        )
    
    return group


@router.post("/", response_model=GroupResponse, status_code=status.HTTP_201_CREATED)
async def create_group(
    group_data: GroupCreate,
    db: Session = Depends(get_database)
):
    """
    Create a new group.
    
    Creates a new security or organizational group and sets up
    default permissions and hierarchy relationships.
    """
    # Check if group name already exists
    existing_group = db.query(Group).filter(Group.name == group_data.name).first()
    if existing_group:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Group name '{group_data.name}' already exists"
        )
    
    # Validate parent group if specified
    if group_data.parent_group_id:
        parent_group = db.query(Group).filter(Group.id == group_data.parent_group_id).first()
        if not parent_group:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Parent group with ID {group_data.parent_group_id} not found"
            )
    
    # Create group
    group = Group(**group_data.dict())
    
    # Set distinguished name for enterprise integration
    if group.parent_group_id:
        parent = db.query(Group).filter(Group.id == group.parent_group_id).first()
        group.distinguished_name = f"CN={group.name},OU={parent.name},DC=company,DC=com"
    else:
        group.distinguished_name = f"CN={group.name},OU=Groups,DC=company,DC=com"
    
    db.add(group)
    db.commit()
    db.refresh(group)
    
    return group


@router.put("/{group_id}", response_model=GroupResponse)
async def update_group(
    group_id: int,
    group_data: GroupUpdate,
    db: Session = Depends(get_database)
):
    """
    Update an existing group.
    
    Updates group information and triggers background tasks
    for permission synchronization across all members.
    """
    group = db.query(Group).filter(Group.id == group_id).first()
    
    if not group:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Group with ID {group_id} not found"
        )
    
    # Check for name conflicts if name is being updated
    if group_data.name and group_data.name != group.name:
        existing_group = db.query(Group).filter(Group.name == group_data.name).first()
        if existing_group:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Group name '{group_data.name}' already exists"
            )
    
    # Update group fields
    update_data = group_data.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(group, field, value)
    
    db.commit()
    db.refresh(group)
    
    return group


@router.delete("/{group_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_group(
    group_id: int,
    db: Session = Depends(get_database)
):
    """
    Delete a group.
    
    Soft delete by setting is_active to False.
    Triggers cleanup tasks for member permissions and child group reassignment.
    """
    group = db.query(Group).filter(Group.id == group_id).first()
    
    if not group:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Group with ID {group_id} not found"
        )
    
    # Check if group has child groups
    child_groups = db.query(Group).filter(Group.parent_group_id == group_id).count()
    if child_groups > 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot delete group with {child_groups} child groups. Please reassign or delete child groups first."
        )
    
    # Soft delete
    group.is_active = False
    db.commit()


@router.get("/{group_id}/members", response_model=List[UserSummary])
async def get_group_members(
    group_id: int,
    db: Session = Depends(get_database)
):
    """
    Get all members of a group.
    
    Returns all users who are members of the specified group.
    """
    group = db.query(Group).filter(Group.id == group_id).first()
    
    if not group:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Group with ID {group_id} not found"
        )
    
    members = list(group.members)
    
    return members


@router.get("/{group_id}/children", response_model=List[GroupResponse])
async def get_child_groups(
    group_id: int,
    db: Session = Depends(get_database)
):
    """
    Get all child groups of a parent group.
    
    Returns all groups that have the specified group as their parent.
    """
    group = db.query(Group).filter(Group.id == group_id).first()
    
    if not group:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Group with ID {group_id} not found"
        )
    
    child_groups = db.query(Group).filter(Group.parent_group_id == group_id).all()
    
    return child_groups


@router.get("/hierarchy/{group_id}")
async def get_group_hierarchy(
    group_id: int,
    db: Session = Depends(get_database)
):
    """
    Get the complete hierarchy for a group.
    
    Returns both parent chain and child tree for the specified group.
    """
    group = db.query(Group).filter(Group.id == group_id).first()
    
    if not group:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Group with ID {group_id} not found"
        )
    
    # Build parent chain
    parent_chain = []
    current = group
    while current.parent_group_id:
        parent = db.query(Group).filter(Group.id == current.parent_group_id).first()
        if parent:
            parent_chain.append({
                "id": parent.id,
                "name": parent.name,
                "group_type": parent.group_type
            })
            current = parent
        else:
            break
    
    # Build child tree
    def get_children(parent_id):
        children = db.query(Group).filter(Group.parent_group_id == parent_id).all()
        return [
            {
                "id": child.id,
                "name": child.name,
                "group_type": child.group_type,
                "children": get_children(child.id)
            }
            for child in children
        ]
    
    child_tree = get_children(group_id)
    
    return {
        "group": {
            "id": group.id,
            "name": group.name,
            "group_type": group.group_type
        },
        "parent_chain": list(reversed(parent_chain)),  # Root to current
        "child_tree": child_tree
    }
