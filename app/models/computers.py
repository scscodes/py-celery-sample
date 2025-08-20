"""
Computer and Asset SQLAlchemy models.

This module defines database models for computer assets,
hardware inventory, and IT infrastructure tracking.
"""

from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Float, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from datetime import datetime

from app.core.database import Base


class Computer(Base):
    """
    Computer model representing enterprise computer assets.
    
    Tracks hardware inventory, specifications, status,
    and ownership information for IT asset management.
    """
    __tablename__ = "computers"
    
    # Primary identification
    id = Column(Integer, primary_key=True, index=True)
    hostname = Column(String(100), unique=True, index=True, nullable=False)
    asset_tag = Column(String(50), unique=True, nullable=True)
    serial_number = Column(String(100), unique=True, nullable=True)
    
    # Network information
    ip_address = Column(String(45), nullable=True)  # IPv4 or IPv6
    mac_address = Column(String(17), nullable=True)
    domain = Column(String(100), nullable=True)
    
    # Hardware specifications
    manufacturer = Column(String(100), nullable=True)
    model = Column(String(100), nullable=True)
    cpu = Column(String(200), nullable=True)
    ram_gb = Column(Integer, nullable=True)
    storage_gb = Column(Integer, nullable=True)
    
    # Software information
    operating_system = Column(String(100), nullable=True)
    os_version = Column(String(50), nullable=True)
    last_patch_date = Column(DateTime, nullable=True)
    
    # Ownership and assignment
    owner_id = Column(Integer, ForeignKey('users.id'), nullable=True)
    department = Column(String(100), nullable=True)
    location = Column(String(200), nullable=True)
    
    # Status and health
    status = Column(String(50), nullable=False, default="active")  # active, inactive, maintenance, retired
    health_status = Column(String(50), nullable=False, default="unknown")  # healthy, warning, critical, unknown
    is_online = Column(Boolean, default=False, nullable=False)
    last_seen = Column(DateTime, nullable=True)
    
    # Compliance and security
    is_compliant = Column(Boolean, default=True, nullable=False)
    compliance_issues = Column(Text, nullable=True)  # JSON string of compliance issues
    encryption_status = Column(String(50), nullable=True)  # encrypted, unencrypted, partial
    
    # Monitoring and metrics
    cpu_usage_percent = Column(Float, nullable=True)
    memory_usage_percent = Column(Float, nullable=True)
    disk_usage_percent = Column(Float, nullable=True)
    uptime_hours = Column(Integer, nullable=True)
    
    # Purchase and warranty information
    purchase_date = Column(DateTime, nullable=True)
    warranty_expiry = Column(DateTime, nullable=True)
    cost = Column(Float, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)
    
    # Relationships
    owner = relationship("User", back_populates="computers")
    
    # Relationship to events (computers generate events)
    events = relationship("Event", back_populates="computer", lazy="select")
    
    # Relationship to incidents (computers can be involved in incidents)
    incidents = relationship("Incident", back_populates="affected_computer", lazy="select")
    
    def __repr__(self):
        return f"<Computer(hostname='{self.hostname}', status='{self.status}')>"
    
    @property
    def owner_name(self):
        """Get the name of the computer owner."""
        return self.owner.full_name if self.owner else None
    
    @property
    def is_healthy(self):
        """Check if computer is in healthy status."""
        return self.health_status == "healthy"
    
    @property
    def needs_attention(self):
        """Check if computer needs attention (critical status or offline)."""
        return (
            self.health_status == "critical" or 
            not self.is_online or 
            not self.is_compliant
        )
    
    @property
    def warranty_expired(self):
        """Check if warranty has expired."""
        if not self.warranty_expiry:
            return None
        return datetime.utcnow() > self.warranty_expiry
    
    def update_health_metrics(self, cpu_usage: float, memory_usage: float, disk_usage: float):
        """
        Update computer health metrics and determine health status.
        
        Args:
            cpu_usage: CPU usage percentage
            memory_usage: Memory usage percentage  
            disk_usage: Disk usage percentage
        """
        self.cpu_usage_percent = cpu_usage
        self.memory_usage_percent = memory_usage
        self.disk_usage_percent = disk_usage
        self.last_seen = func.now()
        self.is_online = True
        
        # Determine health status based on thresholds
        if cpu_usage > 90 or memory_usage > 95 or disk_usage > 95:
            self.health_status = "critical"
        elif cpu_usage > 75 or memory_usage > 85 or disk_usage > 85:
            self.health_status = "warning"
        else:
            self.health_status = "healthy"
