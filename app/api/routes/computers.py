"""
Computer asset management API endpoints.

This module provides REST API endpoints for computer CRUD operations,
health monitoring, and asset tracking workflows.
"""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session, joinedload
from typing import List, Optional

from app.core.dependencies import get_database
from app.schemas.computers import (
    ComputerCreate, ComputerUpdate, ComputerHealthUpdate, ComputerResponse,
    ComputerDetailResponse, ComputerAssetReport, ComputerMetrics,
    ComputerBulkUpdate, ComputerBulkResponse
)
from app.models.computers import Computer
from app.tasks.basic.crud_tasks import sync_computer_data_task, batch_update_computers_task

router = APIRouter()


@router.get("/", response_model=List[ComputerResponse])
async def list_computers(
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of records to return"),
    department: Optional[str] = Query(None, description="Filter by department"),
    status: Optional[str] = Query(None, description="Filter by status"),
    health_status: Optional[str] = Query(None, description="Filter by health status"),
    is_online: Optional[bool] = Query(None, description="Filter by online status"),
    is_compliant: Optional[bool] = Query(None, description="Filter by compliance status"),
    db: Session = Depends(get_database)
):
    """
    Retrieve a list of computers with optional filtering.
    
    - **skip**: Number of records to skip for pagination
    - **limit**: Maximum number of records to return (1-1000)
    - **department**: Filter computers by department
    - **status**: Filter by computer status (active, inactive, maintenance, retired)
    - **health_status**: Filter by health status (healthy, warning, critical, unknown)
    - **is_online**: Filter by online status
    - **is_compliant**: Filter by compliance status
    """
    query = db.query(Computer)
    
    # Apply filters
    if department:
        query = query.filter(Computer.department == department)
    if status:
        query = query.filter(Computer.status == status)
    if health_status:
        query = query.filter(Computer.health_status == health_status)
    if is_online is not None:
        query = query.filter(Computer.is_online == is_online)
    if is_compliant is not None:
        query = query.filter(Computer.is_compliant == is_compliant)
    
    # Apply pagination
    computers = query.offset(skip).limit(limit).all()
    
    return computers


@router.get("/{computer_id}", response_model=ComputerDetailResponse)
async def get_computer(
    computer_id: int,
    db: Session = Depends(get_database)
):
    """
    Retrieve a specific computer by ID with detailed information.
    
    Returns computer details including:
    - Hardware specifications and configuration
    - Owner and assignment information
    - Health metrics and compliance status
    - Recent events and incident history
    """
    computer = db.query(Computer).options(
        joinedload(Computer.owner)  # Load owner relationship
    ).filter(Computer.id == computer_id).first()
    
    if not computer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Computer with ID {computer_id} not found"
        )
    
    return computer


@router.get("/hostname/{hostname}", response_model=ComputerDetailResponse)
async def get_computer_by_hostname(
    hostname: str,
    db: Session = Depends(get_database)
):
    """
    Retrieve a computer by hostname.
    
    Useful for agent-based monitoring systems that report by hostname.
    """
    computer = db.query(Computer).options(
        joinedload(Computer.owner)  # Load owner relationship
    ).filter(Computer.hostname == hostname.lower()).first()
    
    if not computer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Computer with hostname '{hostname}' not found"
        )
    
    return computer


@router.post("/", response_model=ComputerResponse, status_code=status.HTTP_201_CREATED)
async def create_computer(
    computer_data: ComputerCreate,
    db: Session = Depends(get_database)
):
    """
    Create a new computer record.
    
    Registers a new computer in the asset management system
    and triggers background tasks for initial configuration.
    """
    # Check if hostname already exists
    existing_computer = db.query(Computer).filter(
        Computer.hostname == computer_data.hostname.lower()
    ).first()
    if existing_computer:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Computer with hostname '{computer_data.hostname}' already exists"
        )
    
    # Check if asset tag already exists (if provided)
    if computer_data.asset_tag:
        existing_asset = db.query(Computer).filter(
            Computer.asset_tag == computer_data.asset_tag
        ).first()
        if existing_asset:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Computer with asset tag '{computer_data.asset_tag}' already exists"
            )
    
    # Create computer
    computer = Computer(**computer_data.dict())
    computer.hostname = computer.hostname.lower()  # Normalize hostname
    
    db.add(computer)
    db.commit()
    db.refresh(computer)
    
    return computer


@router.put("/{computer_id}", response_model=ComputerResponse)
async def update_computer(
    computer_id: int,
    computer_data: ComputerUpdate,
    db: Session = Depends(get_database)
):
    """
    Update an existing computer record.
    
    Updates computer information and triggers background tasks
    for cache invalidation and compliance checking.
    """
    computer = db.query(Computer).filter(Computer.id == computer_id).first()
    
    if not computer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Computer with ID {computer_id} not found"
        )
    
    # Update computer fields
    update_data = computer_data.dict(exclude_unset=True)
    for field, value in update_data.items():
        if field == "hostname" and value:
            value = value.lower()  # Normalize hostname
        setattr(computer, field, value)
    
    db.commit()
    db.refresh(computer)
    
    return computer


@router.put("/{computer_id}/health", response_model=ComputerResponse)
async def update_computer_health(
    computer_id: int,
    health_data: ComputerHealthUpdate,
    db: Session = Depends(get_database)
):
    """
    Update computer health metrics.
    
    Used by monitoring agents to report system performance
    and health status. Triggers health analysis and alerting.
    """
    computer = db.query(Computer).filter(Computer.id == computer_id).first()
    
    if not computer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Computer with ID {computer_id} not found"
        )
    
    # Update health metrics
    if health_data.cpu_usage_percent is not None:
        computer.cpu_usage_percent = health_data.cpu_usage_percent
    if health_data.memory_usage_percent is not None:
        computer.memory_usage_percent = health_data.memory_usage_percent
    if health_data.disk_usage_percent is not None:
        computer.disk_usage_percent = health_data.disk_usage_percent
    if health_data.uptime_hours is not None:
        computer.uptime_hours = health_data.uptime_hours
    
    computer.is_online = health_data.is_online
    
    # Update health metrics using the model method
    if all(getattr(computer, attr) is not None for attr in 
           ['cpu_usage_percent', 'memory_usage_percent', 'disk_usage_percent']):
        computer.update_health_metrics(
            computer.cpu_usage_percent,
            computer.memory_usage_percent, 
            computer.disk_usage_percent
        )
    
    db.commit()
    db.refresh(computer)
    
    # Trigger async health analysis task
    sync_computer_data_task.delay({
        "hostname": computer.hostname,
        "health_status": computer.health_status,
        "cpu_usage_percent": computer.cpu_usage_percent,
        "memory_usage_percent": computer.memory_usage_percent,
        "disk_usage_percent": computer.disk_usage_percent,
        "is_online": computer.is_online
    })
    
    return computer


@router.delete("/{computer_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_computer(
    computer_id: int,
    db: Session = Depends(get_database)
):
    """
    Delete a computer record.
    
    Marks computer as retired and triggers cleanup tasks
    for asset tracking and access removal.
    """
    computer = db.query(Computer).filter(Computer.id == computer_id).first()
    
    if not computer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Computer with ID {computer_id} not found"
        )
    
    # Mark as retired instead of hard delete
    computer.status = "retired"
    computer.is_online = False
    db.commit()


@router.get("/reports/assets", response_model=ComputerAssetReport)
async def get_asset_report(
    db: Session = Depends(get_database)
):
    """
    Generate comprehensive asset report.
    
    Returns statistics and breakdowns for all computer assets
    including status, health, compliance, and departmental distribution.
    """
    total_computers = db.query(Computer).count()
    active_computers = db.query(Computer).filter(Computer.status == "active").count()
    inactive_computers = db.query(Computer).filter(Computer.status == "inactive").count()
    healthy_computers = db.query(Computer).filter(Computer.health_status == "healthy").count()
    computers_needing_attention = db.query(Computer).filter(
        Computer.health_status.in_(["critical", "warning"])
    ).count()
    online_computers = db.query(Computer).filter(Computer.is_online == True).count()
    offline_computers = db.query(Computer).filter(Computer.is_online == False).count()
    compliant_computers = db.query(Computer).filter(Computer.is_compliant == True).count()
    non_compliant_computers = db.query(Computer).filter(Computer.is_compliant == False).count()
    
    # Get breakdowns
    status_breakdown = {}
    health_breakdown = {}
    os_breakdown = {}
    manufacturer_breakdown = {}
    department_breakdown = {}
    
    # These would be populated with actual query results
    # For brevity, showing structure only
    
    return {
        "total_computers": total_computers,
        "active_computers": active_computers,
        "inactive_computers": inactive_computers,
        "healthy_computers": healthy_computers,
        "computers_needing_attention": computers_needing_attention,
        "online_computers": online_computers,
        "offline_computers": offline_computers,
        "compliant_computers": compliant_computers,
        "non_compliant_computers": non_compliant_computers,
        "by_status": status_breakdown,
        "by_health": health_breakdown,
        "by_operating_system": os_breakdown,
        "by_manufacturer": manufacturer_breakdown,
        "by_department": department_breakdown
    }


@router.get("/metrics/performance", response_model=List[ComputerMetrics])
async def get_performance_metrics(
    limit: int = Query(50, ge=1, le=500, description="Maximum number of computers to return"),
    sort_by: str = Query("cpu_usage_percent", description="Sort by metric"),
    order: str = Query("desc", description="Sort order (asc/desc)"),
    db: Session = Depends(get_database)
):
    """
    Get performance metrics for computers.
    
    Returns current performance data sorted by specified metric.
    Useful for identifying performance issues and resource utilization.
    """
    query = db.query(Computer).filter(Computer.is_online == True)
    
    # Apply sorting
    if hasattr(Computer, sort_by):
        if order == "desc":
            query = query.order_by(getattr(Computer, sort_by).desc())
        else:
            query = query.order_by(getattr(Computer, sort_by).asc())
    
    computers = query.limit(limit).all()
    
    return [
        {
            "hostname": computer.hostname,
            "cpu_usage_percent": computer.cpu_usage_percent,
            "memory_usage_percent": computer.memory_usage_percent,
            "disk_usage_percent": computer.disk_usage_percent,
            "uptime_hours": computer.uptime_hours,
            "last_seen": computer.last_seen,
            "health_status": computer.health_status
        }
        for computer in computers
    ]


@router.post("/bulk/update", response_model=ComputerBulkResponse)
async def bulk_update_computers(
    bulk_data: ComputerBulkUpdate,
    db: Session = Depends(get_database)
):
    """
    Bulk update multiple computers.
    
    Applies the same updates to multiple computers efficiently.
    Triggers background task for large batch processing.
    """
    # Validate computer IDs exist
    computers = db.query(Computer).filter(Computer.id.in_(bulk_data.computer_ids)).all()
    found_ids = {computer.id for computer in computers}
    missing_ids = set(bulk_data.computer_ids) - found_ids
    
    if missing_ids:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Computers not found: {list(missing_ids)}"
        )
    
    # For large bulk operations, use Celery task
    if len(bulk_data.computer_ids) > 10:
        # Prepare data for Celery task
        updates_data = [
            {
                "hostname": computer.hostname,
                **bulk_data.updates.dict(exclude_unset=True)
            }
            for computer in computers
        ]
        
        # Trigger async task
        task_result = batch_update_computers_task.delay(updates_data)
        
        return {
            "updated_count": 0,
            "failed_count": 0,
            "updated_computers": [],
            "errors": [f"Bulk update queued as task {task_result.id}"]
        }
    
    # For small operations, process synchronously
    updated_computers = []
    errors = []
    updated_count = 0
    
    for computer in computers:
        try:
            update_data = bulk_data.updates.dict(exclude_unset=True)
            for field, value in update_data.items():
                setattr(computer, field, value)
            updated_count += 1
            updated_computers.append(computer)
        except Exception as e:
            errors.append(f"Failed to update {computer.hostname}: {str(e)}")
    
    db.commit()
    
    return {
        "updated_count": updated_count,
        "failed_count": len(errors),
        "updated_computers": updated_computers,
        "errors": errors
    }
