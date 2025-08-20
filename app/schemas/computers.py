"""
Pydantic schemas for Computer models.

This module defines request/response schemas for FastAPI endpoints
that handle computer and asset management operations.
"""

from pydantic import BaseModel, validator, IPvAnyAddress
from typing import Optional
from datetime import datetime


# Base schema for common computer attributes
class ComputerBase(BaseModel):
    """Base Computer schema with common attributes."""
    hostname: str
    asset_tag: Optional[str] = None
    serial_number: Optional[str] = None
    ip_address: Optional[str] = None
    mac_address: Optional[str] = None
    domain: Optional[str] = None
    manufacturer: Optional[str] = None
    model: Optional[str] = None
    cpu: Optional[str] = None
    ram_gb: Optional[int] = None
    storage_gb: Optional[int] = None
    operating_system: Optional[str] = None
    os_version: Optional[str] = None
    department: Optional[str] = None
    location: Optional[str] = None
    status: str = "active"
    encryption_status: Optional[str] = None
    
    @validator('hostname')
    def hostname_valid(cls, v):
        """Validate hostname format."""
        if not v.replace('-', '').replace('.', '').isalnum():
            raise ValueError('Hostname must contain only alphanumeric characters, hyphens, and dots')
        return v.lower()
    
    @validator('mac_address')
    def mac_address_format(cls, v):
        """Validate MAC address format."""
        if v is None:
            return v
        # Remove common separators and validate length
        mac_clean = v.replace(':', '').replace('-', '').replace('.', '')
        if len(mac_clean) != 12 or not all(c in '0123456789ABCDEFabcdef' for c in mac_clean):
            raise ValueError('MAC address must be in valid format (e.g., 00:11:22:33:44:55)')
        # Normalize to colon-separated format
        return ':'.join(mac_clean[i:i+2] for i in range(0, 12, 2)).upper()
    
    @validator('ram_gb', 'storage_gb')
    def positive_numbers(cls, v):
        """Validate that RAM and storage are positive numbers."""
        if v is not None and v <= 0:
            raise ValueError('RAM and storage must be positive numbers')
        return v


# Request schemas (for creating/updating)
class ComputerCreate(ComputerBase):
    """Schema for creating a new computer."""
    owner_id: Optional[int] = None
    purchase_date: Optional[datetime] = None
    warranty_expiry: Optional[datetime] = None
    cost: Optional[float] = None


class ComputerUpdate(BaseModel):
    """Schema for updating an existing computer."""
    hostname: Optional[str] = None
    asset_tag: Optional[str] = None
    serial_number: Optional[str] = None
    ip_address: Optional[str] = None
    mac_address: Optional[str] = None
    domain: Optional[str] = None
    manufacturer: Optional[str] = None
    model: Optional[str] = None
    cpu: Optional[str] = None
    ram_gb: Optional[int] = None
    storage_gb: Optional[int] = None
    operating_system: Optional[str] = None
    os_version: Optional[str] = None
    owner_id: Optional[int] = None
    department: Optional[str] = None
    location: Optional[str] = None
    status: Optional[str] = None
    encryption_status: Optional[str] = None
    last_patch_date: Optional[datetime] = None
    purchase_date: Optional[datetime] = None
    warranty_expiry: Optional[datetime] = None
    cost: Optional[float] = None


class ComputerHealthUpdate(BaseModel):
    """Schema for updating computer health metrics."""
    cpu_usage_percent: Optional[float] = None
    memory_usage_percent: Optional[float] = None
    disk_usage_percent: Optional[float] = None
    uptime_hours: Optional[int] = None
    is_online: bool = True
    
    @validator('cpu_usage_percent', 'memory_usage_percent', 'disk_usage_percent')
    def validate_percentages(cls, v):
        """Validate percentages are between 0 and 100."""
        if v is not None and (v < 0 or v > 100):
            raise ValueError('Percentage values must be between 0 and 100')
        return v


# Response schemas
class ComputerResponse(ComputerBase):
    """Schema for computer API responses."""
    id: int
    owner_id: Optional[int]
    health_status: str
    is_online: bool
    last_seen: Optional[datetime]
    is_compliant: bool
    compliance_issues: Optional[str]
    cpu_usage_percent: Optional[float]
    memory_usage_percent: Optional[float]
    disk_usage_percent: Optional[float]
    uptime_hours: Optional[int]
    last_patch_date: Optional[datetime]
    purchase_date: Optional[datetime]
    warranty_expiry: Optional[datetime]
    cost: Optional[float]
    created_at: datetime
    updated_at: datetime
    
    # Computed properties
    owner_name: Optional[str] = None
    is_healthy: Optional[bool] = None
    needs_attention: Optional[bool] = None
    warranty_expired: Optional[bool] = None
    
    class Config:
        from_attributes = True


# Summary schema for references
class ComputerSummary(BaseModel):
    """Summary schema for computer references in other responses."""
    id: int
    hostname: str
    status: str
    health_status: str
    is_online: bool
    owner_name: Optional[str]
    
    class Config:
        from_attributes = True


# Extended response schema with relationships
class ComputerDetailResponse(ComputerResponse):
    """Detailed computer response including owner information."""
    owner: Optional['UserSummary'] = None  # Forward reference
    
    class Config:
        from_attributes = True


# Asset reporting schemas
class ComputerAssetReport(BaseModel):
    """Schema for computer asset reporting."""
    total_computers: int
    active_computers: int
    inactive_computers: int
    healthy_computers: int
    computers_needing_attention: int
    online_computers: int
    offline_computers: int
    compliant_computers: int
    non_compliant_computers: int
    
    # Breakdown by categories
    by_status: dict
    by_health: dict
    by_operating_system: dict
    by_manufacturer: dict
    by_department: dict


class ComputerMetrics(BaseModel):
    """Schema for computer performance metrics."""
    hostname: str
    cpu_usage_percent: Optional[float]
    memory_usage_percent: Optional[float]
    disk_usage_percent: Optional[float]
    uptime_hours: Optional[int]
    last_seen: Optional[datetime]
    health_status: str
    
    class Config:
        from_attributes = True


# Bulk operations schemas
class ComputerBulkUpdate(BaseModel):
    """Schema for bulk computer updates."""
    computer_ids: list[int]
    updates: ComputerUpdate


class ComputerBulkResponse(BaseModel):
    """Schema for bulk operation responses."""
    updated_count: int
    failed_count: int
    updated_computers: list[ComputerSummary]
    errors: list[str]


# Import user summary for type hinting
from app.schemas.users import UserSummary

# Update forward references
ComputerDetailResponse.model_rebuild()
