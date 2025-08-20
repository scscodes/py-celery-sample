"""
User and Group SQLAlchemy models.

This module defines the database models for users and groups,
based on Active Directory-style enterprise patterns.
"""

from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Table
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from datetime import datetime

from app.core.database import Base


# Association table for many-to-many relationship between users and groups
user_group_association = Table(
    'user_group_membership',
    Base.metadata,
    Column('user_id', Integer, ForeignKey('users.id'), primary_key=True),
    Column('group_id', Integer, ForeignKey('groups.id'), primary_key=True),
    Column('added_at', DateTime, default=func.now()),
    Column('added_by', String, nullable=True)  # Who added the user to the group
)


class User(Base):
    """
    User model representing enterprise users.
    
    Based on Active Directory user attributes commonly used
    in enterprise IT environments.
    """
    __tablename__ = "users"
    
    # Primary identification
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(100), unique=True, index=True, nullable=False)
    email = Column(String(255), unique=True, index=True, nullable=False)
    
    # Personal information
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=False)
    display_name = Column(String(200), nullable=True)
    
    # Organizational information
    department = Column(String(100), nullable=True)
    title = Column(String(200), nullable=True)
    manager_id = Column(Integer, ForeignKey('users.id'), nullable=True)
    employee_id = Column(String(50), unique=True, nullable=True)
    
    # Account status and security
    is_active = Column(Boolean, default=True, nullable=False)
    is_locked = Column(Boolean, default=False, nullable=False)
    password_last_changed = Column(DateTime, nullable=True)
    last_login = Column(DateTime, nullable=True)
    failed_login_attempts = Column(Integer, default=0)
    
    # Contact information
    phone = Column(String(20), nullable=True)
    office_location = Column(String(100), nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)
    
    # Relationships
    groups = relationship(
        "Group", 
        secondary=user_group_association, 
        back_populates="members",
        lazy="dynamic"
    )
    
    # Self-referential relationship for manager hierarchy
    subordinates = relationship(
        "User", 
        backref="manager", 
        remote_side=[id]
    )
    
    # Relationship to computers (users can own/be assigned computers)
    computers = relationship("Computer", back_populates="owner", lazy="dynamic")
    
    # Relationship to incidents (users can be assignees or reporters)
    assigned_incidents = relationship(
        "Incident", 
        foreign_keys="Incident.assignee_id",
        back_populates="assignee",
        lazy="dynamic"
    )
    
    reported_incidents = relationship(
        "Incident",
        foreign_keys="Incident.reporter_id", 
        back_populates="reporter",
        lazy="dynamic"
    )
    
    def __repr__(self):
        return f"<User(username='{self.username}', email='{self.email}')>"
    
    @property
    def full_name(self):
        """Get user's full name."""
        return f"{self.first_name} {self.last_name}"
    
    @property
    def is_manager(self):
        """Check if user is a manager (has subordinates)."""
        return self.subordinates.count() > 0


class Group(Base):
    """
    Group model representing enterprise security/organizational groups.
    
    Based on Active Directory group concepts for access control
    and organizational structure.
    """
    __tablename__ = "groups"
    
    # Primary identification
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, index=True, nullable=False)
    description = Column(String(500), nullable=True)
    
    # Group classification
    group_type = Column(String(50), nullable=False, default="security")  # security, distribution, organizational
    scope = Column(String(50), nullable=False, default="global")  # global, domain, universal
    
    # Group hierarchy and organization
    parent_group_id = Column(Integer, ForeignKey('groups.id'), nullable=True)
    distinguished_name = Column(String(500), nullable=True)  # AD-style DN
    
    # Group status and management
    is_active = Column(Boolean, default=True, nullable=False)
    managed_by = Column(String(100), nullable=True)  # Username of group manager
    
    # Permissions and access (simplified representation)
    permissions = Column(String(1000), nullable=True)  # JSON string of permissions
    
    # Timestamps
    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)
    
    # Relationships
    members = relationship(
        "User", 
        secondary=user_group_association, 
        back_populates="groups",
        lazy="dynamic"
    )
    
    # Self-referential relationship for group hierarchy
    child_groups = relationship(
        "Group", 
        backref="parent_group", 
        remote_side=[id]
    )
    
    def __repr__(self):
        return f"<Group(name='{self.name}', type='{self.group_type}')>"
    
    @property
    def member_count(self):
        """Get count of group members."""
        return self.members.count()
    
    @property
    def is_nested_group(self):
        """Check if group has parent groups (is nested)."""
        return self.parent_group_id is not None
