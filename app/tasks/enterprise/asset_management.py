"""
Enterprise Asset Management Workflows

This module provides comprehensive IT asset lifecycle management workflows including
asset discovery, inventory management, compliance tracking, and automated provisioning.
"""

import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import json
import random
import time
from enum import Enum
from dataclasses import dataclass

from celery import chain, group, chord
from app.tasks.celery_app import celery_app
from app.tasks.orchestration.callbacks_tasks import CallbackConfig, with_callbacks

logger = logging.getLogger(__name__)


class AssetType(Enum):
    """Types of IT assets."""
    SERVER = "server"
    WORKSTATION = "workstation"
    LAPTOP = "laptop"
    MOBILE_DEVICE = "mobile_device"
    NETWORK_DEVICE = "network_device"
    SOFTWARE_LICENSE = "software_license"
    VIRTUAL_MACHINE = "virtual_machine"
    CLOUD_RESOURCE = "cloud_resource"


class AssetStatus(Enum):
    """Asset lifecycle status."""
    ORDERED = "ordered"
    RECEIVED = "received"
    DEPLOYED = "deployed"
    IN_USE = "in_use"
    MAINTENANCE = "maintenance"
    RETIRED = "retired"
    DISPOSED = "disposed"


class ComplianceStatus(Enum):
    """Asset compliance status."""
    COMPLIANT = "compliant"
    NON_COMPLIANT = "non_compliant"
    PENDING_REVIEW = "pending_review"
    EXEMPT = "exempt"


@dataclass
class AssetInfo:
    """Asset information structure."""
    asset_id: str
    asset_type: AssetType
    manufacturer: str
    model: str
    serial_number: str
    status: AssetStatus = AssetStatus.RECEIVED
    assigned_to: Optional[str] = None
    location: Optional[str] = None
    purchase_date: Optional[datetime] = None
    warranty_expiry: Optional[datetime] = None
    cost: Optional[float] = None
    specifications: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.specifications is None:
            self.specifications = {}
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "asset_id": self.asset_id,
            "asset_type": self.asset_type.value,
            "manufacturer": self.manufacturer,
            "model": self.model,
            "serial_number": self.serial_number,
            "status": self.status.value,
            "assigned_to": self.assigned_to,
            "location": self.location,
            "purchase_date": self.purchase_date.isoformat() if self.purchase_date else None,
            "warranty_expiry": self.warranty_expiry.isoformat() if self.warranty_expiry else None,
            "cost": self.cost,
            "specifications": self.specifications
        }


# =============================================================================
# ASSET DISCOVERY AND INVENTORY
# =============================================================================

@celery_app.task(bind=True, name="asset.discover_network_assets")
@with_callbacks(CallbackConfig(
    success_callbacks=["log_success", "update_metrics"],
    failure_callbacks=["log_failure", "send_slack"],
    audit_enabled=True
))
def discover_network_assets(self, discovery_config: Dict[str, Any]) -> Dict[str, Any]:
    """Discover assets on the network and update inventory."""
    task_id = self.request.id
    logger.info(f"[{task_id}] Starting network asset discovery")
    
    # Network discovery configuration
    network_ranges = discovery_config.get("network_ranges", ["192.168.1.0/24", "10.0.0.0/16"])
    discovery_methods = discovery_config.get("methods", ["ping", "snmp", "wmi", "ssh"])
    
    # Run discovery on different network segments in parallel
    discovery_tasks = []
    for network_range in network_ranges:
        for method in discovery_methods:
            discovery_tasks.append(
                scan_network_range.s(network_range, method, discovery_config)
            )
    
    # Execute all discovery tasks and aggregate results
    discovery_chord = chord(discovery_tasks)(
        aggregate_discovery_results.s(discovery_config)
    )
    
    discovery_summary = {
        "discovery_id": f"discovery_{task_id}",
        "network_ranges": network_ranges,
        "discovery_methods": discovery_methods,
        "discovery_tasks_started": len(discovery_tasks),
        "discovery_chord_id": discovery_chord.id,
        "started_at": datetime.utcnow().isoformat(),
        "initiator_task_id": task_id
    }
    
    logger.info(f"[{task_id}] Network discovery initiated for {len(network_ranges)} ranges")
    return discovery_summary


@celery_app.task(bind=True, name="asset.scan_network_range")
def scan_network_range(self, network_range: str, method: str, config: Dict[str, Any]) -> Dict[str, Any]:
    """Scan a specific network range using the specified method."""
    task_id = self.request.id
    logger.info(f"[{task_id}] Scanning {network_range} using {method}")
    
    # Simulate network scanning
    scan_duration = random.uniform(10, 30)  # Realistic scan time
    time.sleep(scan_duration)
    
    # Simulate discovered assets
    discovered_assets = []
    asset_count = random.randint(5, 50)  # Random number of assets found
    
    for i in range(asset_count):
        asset_info = generate_simulated_asset(network_range, method)
        discovered_assets.append(asset_info)
    
    scan_result = {
        "network_range": network_range,
        "discovery_method": method,
        "assets_discovered": len(discovered_assets),
        "discovered_assets": discovered_assets,
        "scan_duration_seconds": scan_duration,
        "scan_completed_at": datetime.utcnow().isoformat(),
        "scanner_task_id": task_id
    }
    
    logger.info(f"[{task_id}] Scan complete: {len(discovered_assets)} assets found in {network_range}")
    return scan_result


def generate_simulated_asset(network_range: str, method: str) -> Dict[str, Any]:
    """Generate simulated asset data for demonstration."""
    asset_types = list(AssetType)
    asset_type = random.choice(asset_types)
    
    # Generate realistic asset data based on type
    manufacturers = {
        AssetType.SERVER: ["Dell", "HP", "Lenovo", "Supermicro"],
        AssetType.WORKSTATION: ["Dell", "HP", "Lenovo", "Apple"],
        AssetType.LAPTOP: ["Dell", "HP", "Lenovo", "Apple", "ASUS"],
        AssetType.NETWORK_DEVICE: ["Cisco", "Juniper", "Aruba", "Meraki"],
        AssetType.MOBILE_DEVICE: ["Apple", "Samsung", "Google"],
    }
    
    manufacturer = random.choice(manufacturers.get(asset_type, ["Generic"]))
    
    # Generate IP address within range
    base_ip = network_range.split('/')[0].rsplit('.', 1)[0]
    ip_address = f"{base_ip}.{random.randint(1, 254)}"
    
    asset_data = {
        "ip_address": ip_address,
        "asset_type": asset_type.value,
        "manufacturer": manufacturer,
        "model": f"{manufacturer}-{random.randint(1000, 9999)}",
        "hostname": f"asset-{random.randint(100000, 999999)}",
        "mac_address": generate_mac_address(),
        "discovery_method": method,
        "last_seen": datetime.utcnow().isoformat(),
        "os_info": generate_os_info(asset_type),
        "open_ports": generate_open_ports(asset_type),
        "services": generate_services(asset_type)
    }
    
    return asset_data


def generate_mac_address() -> str:
    """Generate a random MAC address."""
    return ":".join([f"{random.randint(0, 255):02x}" for _ in range(6)])


def generate_os_info(asset_type: AssetType) -> Dict[str, str]:
    """Generate OS information based on asset type."""
    os_map = {
        AssetType.SERVER: ["Windows Server 2019", "Windows Server 2022", "Ubuntu 20.04", "RHEL 8"],
        AssetType.WORKSTATION: ["Windows 10", "Windows 11", "macOS 12", "Ubuntu 22.04"],
        AssetType.LAPTOP: ["Windows 10", "Windows 11", "macOS 12", "macOS 13"],
        AssetType.NETWORK_DEVICE: ["Cisco IOS", "Juniper JUNOS", "Aruba AOS"],
    }
    
    os_list = os_map.get(asset_type, ["Unknown"])
    selected_os = random.choice(os_list)
    
    return {
        "operating_system": selected_os,
        "version": f"{random.randint(1, 15)}.{random.randint(0, 9)}.{random.randint(0, 99)}",
        "build": str(random.randint(10000, 99999))
    }


def generate_open_ports(asset_type: AssetType) -> List[int]:
    """Generate open ports based on asset type."""
    common_ports = {
        AssetType.SERVER: [22, 80, 443, 3389, 5985, 8080],
        AssetType.WORKSTATION: [135, 445, 3389, 5357],
        AssetType.NETWORK_DEVICE: [22, 23, 80, 161, 443],
    }
    
    ports = common_ports.get(asset_type, [22, 80, 443])
    return random.sample(ports, random.randint(1, len(ports)))


def generate_services(asset_type: AssetType) -> List[str]:
    """Generate services based on asset type."""
    service_map = {
        AssetType.SERVER: ["http", "https", "ssh", "rdp", "winrm", "ftp"],
        AssetType.WORKSTATION: ["rdp", "smb", "wmi"],
        AssetType.NETWORK_DEVICE: ["ssh", "telnet", "http", "snmp"],
    }
    
    services = service_map.get(asset_type, ["ssh", "http"])
    return random.sample(services, random.randint(1, len(services)))


@celery_app.task(bind=True, name="asset.aggregate_discovery_results")
def aggregate_discovery_results(self, discovery_results: List[Dict[str, Any]], config: Dict[str, Any]) -> Dict[str, Any]:
    """Aggregate asset discovery results and update inventory."""
    task_id = self.request.id
    logger.info(f"[{task_id}] Aggregating discovery results from {len(discovery_results)} scans")
    
    # Aggregate all discovered assets
    all_discovered_assets = []
    total_scan_time = 0
    
    for result in discovery_results:
        all_discovered_assets.extend(result.get("discovered_assets", []))
        total_scan_time += result.get("scan_duration_seconds", 0)
    
    # Deduplicate assets by IP address
    unique_assets = {}
    for asset in all_discovered_assets:
        ip = asset.get("ip_address")
        if ip not in unique_assets:
            unique_assets[ip] = asset
        else:
            # Merge information from multiple discovery methods
            existing = unique_assets[ip]
            existing["discovery_methods"] = existing.get("discovery_methods", [])
            if asset.get("discovery_method") not in existing["discovery_methods"]:
                existing["discovery_methods"].append(asset.get("discovery_method"))
    
    unique_asset_list = list(unique_assets.values())
    
    # Categorize assets by type
    asset_categories = {}
    for asset in unique_asset_list:
        asset_type = asset.get("asset_type", "unknown")
        if asset_type not in asset_categories:
            asset_categories[asset_type] = 0
        asset_categories[asset_type] += 1
    
    # Update asset inventory
    inventory_updates = []
    for asset in unique_asset_list:
        update_result = update_asset_inventory.delay(asset)
        inventory_updates.append(update_result.id)
    
    # Generate discovery report
    discovery_report = {
        "discovery_id": f"discovery_{task_id}",
        "total_assets_discovered": len(unique_asset_list),
        "total_scan_time_seconds": total_scan_time,
        "asset_categories": asset_categories,
        "new_assets": len([a for a in unique_asset_list if is_new_asset(a)]),
        "updated_assets": len(unique_asset_list) - len([a for a in unique_asset_list if is_new_asset(a)]),
        "inventory_update_tasks": inventory_updates,
        "aggregated_at": datetime.utcnow().isoformat(),
        "aggregator_task_id": task_id
    }
    
    # Schedule follow-up tasks
    if config.get("enable_vulnerability_scanning", False):
        schedule_vulnerability_scan.delay([a.get("ip_address") for a in unique_asset_list])
    
    if config.get("enable_compliance_check", False):
        schedule_compliance_check.delay([a.get("ip_address") for a in unique_asset_list])
    
    logger.info(f"[{task_id}] Discovery aggregation complete: {len(unique_asset_list)} unique assets")
    return discovery_report


def is_new_asset(asset: Dict[str, Any]) -> bool:
    """Determine if asset is new (simulated check)."""
    return random.choice([True, False])  # 50% chance of being new


# =============================================================================
# ASSET LIFECYCLE MANAGEMENT
# =============================================================================

@celery_app.task(bind=True, name="asset.provision_new_asset")
def provision_new_asset(self, asset_request: Dict[str, Any]) -> Dict[str, Any]:
    """Provision a new asset through the complete lifecycle."""
    task_id = self.request.id
    logger.info(f"[{task_id}] Starting asset provisioning workflow")
    
    # Create asset record
    asset_id = f"ASSET-{random.randint(100000, 999999)}"
    asset_info = AssetInfo(
        asset_id=asset_id,
        asset_type=AssetType(asset_request["asset_type"]),
        manufacturer=asset_request["manufacturer"],
        model=asset_request["model"],
        serial_number=asset_request.get("serial_number", f"SN{random.randint(10000000, 99999999)}"),
        status=AssetStatus.ORDERED,
        assigned_to=asset_request.get("assigned_to"),
        location=asset_request.get("location", "Datacenter A"),
        cost=asset_request.get("cost", random.uniform(1000, 10000))
    )
    
    # Build provisioning workflow
    provisioning_workflow = chain(
        create_asset_record.s(asset_info.to_dict()),
        configure_asset.s(asset_request.get("configuration", {})),
        install_software.s(asset_request.get("software_packages", [])),
        apply_security_policies.s(asset_request.get("security_policies", [])),
        assign_asset_to_user.s(asset_request.get("assigned_to")),
        update_asset_status.s(AssetStatus.DEPLOYED.value)
    )
    
    # Execute provisioning workflow
    workflow_result = provisioning_workflow.apply_async()
    
    provisioning_summary = {
        "asset_id": asset_id,
        "provisioning_workflow_id": workflow_result.id,
        "asset_type": asset_info.asset_type.value,
        "assigned_to": asset_info.assigned_to,
        "estimated_completion": (datetime.utcnow() + timedelta(hours=2)).isoformat(),
        "initiated_at": datetime.utcnow().isoformat(),
        "initiator_task_id": task_id
    }
    
    logger.info(f"[{task_id}] Asset provisioning initiated: {asset_id}")
    return provisioning_summary


@celery_app.task(bind=True, name="asset.create_asset_record")
def create_asset_record(self, asset_data: Dict[str, Any]) -> Dict[str, Any]:
    """Create asset record in inventory system."""
    task_id = self.request.id
    asset_id = asset_data["asset_id"]
    
    logger.info(f"[{task_id}] Creating asset record: {asset_id}")
    
    # Simulate asset record creation
    time.sleep(random.uniform(1, 3))
    
    # Add metadata
    asset_data.update({
        "created_at": datetime.utcnow().isoformat(),
        "created_by_task": task_id,
        "inventory_location": f"rack_{random.randint(1, 50)}_slot_{random.randint(1, 20)}"
    })
    
    logger.info(f"[{task_id}] Asset record created: {asset_id}")
    return asset_data


@celery_app.task(bind=True, name="asset.configure_asset")
def configure_asset(self, asset_data: Dict[str, Any], configuration: Dict[str, Any]) -> Dict[str, Any]:
    """Apply base configuration to asset."""
    task_id = self.request.id
    asset_id = asset_data["asset_id"]
    
    logger.info(f"[{task_id}] Configuring asset: {asset_id}")
    
    # Simulate configuration application
    time.sleep(random.uniform(5, 15))
    
    # Apply configuration based on asset type
    asset_type = AssetType(asset_data["asset_type"])
    
    if asset_type == AssetType.SERVER:
        applied_config = apply_server_configuration(configuration)
    elif asset_type == AssetType.WORKSTATION:
        applied_config = apply_workstation_configuration(configuration)
    else:
        applied_config = apply_default_configuration(configuration)
    
    asset_data["configuration"] = applied_config
    asset_data["configured_at"] = datetime.utcnow().isoformat()
    asset_data["configured_by_task"] = task_id
    
    logger.info(f"[{task_id}] Asset configuration complete: {asset_id}")
    return asset_data


def apply_server_configuration(config: Dict[str, Any]) -> Dict[str, Any]:
    """Apply server-specific configuration."""
    return {
        "network_settings": {
            "ip_address": config.get("ip_address", f"10.0.1.{random.randint(10, 250)}"),
            "subnet_mask": "255.255.255.0",
            "gateway": "10.0.1.1",
            "dns_servers": ["10.0.1.2", "10.0.1.3"]
        },
        "storage_settings": {
            "raid_level": config.get("raid_level", "RAID1"),
            "disk_encryption": True
        },
        "performance_settings": {
            "power_profile": "high_performance",
            "cpu_governor": "performance"
        }
    }


def apply_workstation_configuration(config: Dict[str, Any]) -> Dict[str, Any]:
    """Apply workstation-specific configuration."""
    return {
        "network_settings": {
            "dhcp_enabled": True,
            "domain": config.get("domain", "corp.company.com")
        },
        "security_settings": {
            "firewall_enabled": True,
            "antivirus_installed": True,
            "encryption_enabled": True
        },
        "user_settings": {
            "auto_login": False,
            "screensaver_timeout": 600
        }
    }


def apply_default_configuration(config: Dict[str, Any]) -> Dict[str, Any]:
    """Apply default configuration."""
    return {
        "basic_settings": config,
        "configured_at": datetime.utcnow().isoformat()
    }


@celery_app.task(bind=True, name="asset.install_software")
def install_software(self, asset_data: Dict[str, Any], software_packages: List[str]) -> Dict[str, Any]:
    """Install required software packages on asset."""
    task_id = self.request.id
    asset_id = asset_data["asset_id"]
    
    logger.info(f"[{task_id}] Installing software on asset: {asset_id}")
    
    # Simulate software installation
    installation_time = len(software_packages) * random.uniform(2, 5)
    time.sleep(installation_time)
    
    installed_software = []
    for package in software_packages:
        # Simulate installation success/failure
        installation_success = random.choice([True, True, True, False])  # 75% success rate
        
        installed_software.append({
            "package": package,
            "version": f"{random.randint(1, 10)}.{random.randint(0, 9)}.{random.randint(0, 99)}",
            "installed": installation_success,
            "installed_at": datetime.utcnow().isoformat() if installation_success else None,
            "error": None if installation_success else f"Failed to install {package}"
        })
    
    asset_data["installed_software"] = installed_software
    asset_data["software_installation_completed_at"] = datetime.utcnow().isoformat()
    asset_data["software_installer_task"] = task_id
    
    successful_installations = sum(1 for sw in installed_software if sw["installed"])
    logger.info(f"[{task_id}] Software installation complete: {successful_installations}/{len(software_packages)} successful")
    
    return asset_data


@celery_app.task(bind=True, name="asset.apply_security_policies")
def apply_security_policies(self, asset_data: Dict[str, Any], security_policies: List[str]) -> Dict[str, Any]:
    """Apply security policies to asset."""
    task_id = self.request.id
    asset_id = asset_data["asset_id"]
    
    logger.info(f"[{task_id}] Applying security policies to asset: {asset_id}")
    
    # Simulate security policy application
    time.sleep(random.uniform(3, 8))
    
    applied_policies = []
    for policy in security_policies:
        # Simulate policy application
        application_success = random.choice([True, True, True, True, False])  # 80% success rate
        
        applied_policies.append({
            "policy": policy,
            "applied": application_success,
            "applied_at": datetime.utcnow().isoformat() if application_success else None,
            "error": None if application_success else f"Failed to apply policy {policy}"
        })
    
    asset_data["security_policies"] = applied_policies
    asset_data["security_policies_applied_at"] = datetime.utcnow().isoformat()
    asset_data["security_policy_task"] = task_id
    
    successful_policies = sum(1 for pol in applied_policies if pol["applied"])
    logger.info(f"[{task_id}] Security policies applied: {successful_policies}/{len(security_policies)} successful")
    
    return asset_data


@celery_app.task(bind=True, name="asset.assign_asset_to_user")
def assign_asset_to_user(self, asset_data: Dict[str, Any], user_id: Optional[str]) -> Dict[str, Any]:
    """Assign asset to user and update ownership records."""
    task_id = self.request.id
    asset_id = asset_data["asset_id"]
    
    if not user_id:
        logger.info(f"[{task_id}] No user assignment for asset: {asset_id}")
        return asset_data
    
    logger.info(f"[{task_id}] Assigning asset {asset_id} to user: {user_id}")
    
    # Simulate user assignment process
    time.sleep(random.uniform(1, 3))
    
    # Create assignment record
    assignment_record = {
        "assigned_to": user_id,
        "assigned_at": datetime.utcnow().isoformat(),
        "assigned_by_task": task_id,
        "assignment_type": "primary",
        "responsibility_level": "full_ownership"
    }
    
    # Notify user
    send_asset_assignment_notification.delay(asset_id, user_id, assignment_record)
    
    asset_data["assignment"] = assignment_record
    asset_data["status"] = AssetStatus.IN_USE.value
    
    logger.info(f"[{task_id}] Asset assignment complete: {asset_id} -> {user_id}")
    return asset_data


@celery_app.task(bind=True, name="asset.update_asset_status")
def update_asset_status(self, asset_data: Dict[str, Any], new_status: str) -> Dict[str, Any]:
    """Update asset status in inventory system."""
    task_id = self.request.id
    asset_id = asset_data["asset_id"]
    
    logger.info(f"[{task_id}] Updating asset status: {asset_id} -> {new_status}")
    
    # Simulate status update
    time.sleep(random.uniform(0.5, 1.5))
    
    previous_status = asset_data.get("status", "unknown")
    asset_data["status"] = new_status
    asset_data["status_updated_at"] = datetime.utcnow().isoformat()
    asset_data["status_updated_by_task"] = task_id
    
    # Log status change
    status_history = asset_data.get("status_history", [])
    status_history.append({
        "previous_status": previous_status,
        "new_status": new_status,
        "changed_at": datetime.utcnow().isoformat(),
        "changed_by_task": task_id
    })
    asset_data["status_history"] = status_history
    
    logger.info(f"[{task_id}] Asset status updated: {asset_id}")
    return asset_data


# =============================================================================
# COMPLIANCE AND MONITORING
# =============================================================================

@celery_app.task(bind=True, name="asset.run_compliance_audit")
def run_compliance_audit(self, audit_config: Dict[str, Any]) -> Dict[str, Any]:
    """Run comprehensive compliance audit across all assets."""
    task_id = self.request.id
    logger.info(f"[{task_id}] Starting compliance audit")
    
    # Get asset inventory for audit
    asset_inventory = get_asset_inventory.apply_async([audit_config.get("asset_filters", {})]).get()
    
    # Run parallel compliance checks
    compliance_tasks = []
    for asset in asset_inventory:
        compliance_tasks.append(
            check_asset_compliance.s(asset["asset_id"], audit_config.get("compliance_rules", []))
        )
    
    # Aggregate compliance results
    compliance_chord = chord(compliance_tasks)(
        aggregate_compliance_results.s(audit_config)
    )
    
    audit_summary = {
        "audit_id": f"audit_{task_id}",
        "assets_audited": len(asset_inventory),
        "compliance_checks_started": len(compliance_tasks),
        "compliance_chord_id": compliance_chord.id,
        "audit_started_at": datetime.utcnow().isoformat(),
        "auditor_task_id": task_id
    }
    
    logger.info(f"[{task_id}] Compliance audit initiated for {len(asset_inventory)} assets")
    return audit_summary


@celery_app.task(bind=True, name="asset.check_asset_compliance")
def check_asset_compliance(self, asset_id: str, compliance_rules: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Check individual asset compliance against rules."""
    task_id = self.request.id
    logger.info(f"[{task_id}] Checking compliance for asset: {asset_id}")
    
    # Get asset details
    asset_details = get_asset_details.apply_async([asset_id]).get()
    
    if not asset_details:
        return {
            "asset_id": asset_id,
            "compliance_status": ComplianceStatus.PENDING_REVIEW.value,
            "error": "Asset not found",
            "checked_at": datetime.utcnow().isoformat()
        }
    
    # Check each compliance rule
    compliance_results = []
    overall_compliant = True
    
    for rule in compliance_rules:
        rule_result = evaluate_compliance_rule(asset_details, rule)
        compliance_results.append(rule_result)
        
        if not rule_result["compliant"]:
            overall_compliant = False
    
    # Determine overall compliance status
    compliance_status = ComplianceStatus.COMPLIANT if overall_compliant else ComplianceStatus.NON_COMPLIANT
    
    compliance_report = {
        "asset_id": asset_id,
        "compliance_status": compliance_status.value,
        "overall_compliant": overall_compliant,
        "compliance_score": calculate_compliance_score(compliance_results),
        "rule_results": compliance_results,
        "non_compliant_rules": [r for r in compliance_results if not r["compliant"]],
        "checked_at": datetime.utcnow().isoformat(),
        "checker_task_id": task_id
    }
    
    # Store compliance result
    store_compliance_result.delay(asset_id, compliance_report)
    
    logger.info(f"[{task_id}] Compliance check complete: {asset_id} - {compliance_status.value}")
    return compliance_report


def evaluate_compliance_rule(asset_details: Dict[str, Any], rule: Dict[str, Any]) -> Dict[str, Any]:
    """Evaluate a single compliance rule against asset."""
    rule_type = rule.get("type", "unknown")
    rule_name = rule.get("name", "unnamed_rule")
    
    # Simulate different types of compliance rules
    if rule_type == "software_version":
        return check_software_version_compliance(asset_details, rule)
    elif rule_type == "security_patch":
        return check_security_patch_compliance(asset_details, rule)
    elif rule_type == "configuration":
        return check_configuration_compliance(asset_details, rule)
    elif rule_type == "encryption":
        return check_encryption_compliance(asset_details, rule)
    else:
        return {
            "rule_name": rule_name,
            "rule_type": rule_type,
            "compliant": random.choice([True, False]),
            "details": "Generic compliance check",
            "checked_at": datetime.utcnow().isoformat()
        }


def check_software_version_compliance(asset_details: Dict[str, Any], rule: Dict[str, Any]) -> Dict[str, Any]:
    """Check software version compliance."""
    software_name = rule.get("software_name", "")
    required_version = rule.get("minimum_version", "")
    
    # Simulate software version check
    installed_version = f"{random.randint(1, 10)}.{random.randint(0, 9)}.{random.randint(0, 99)}"
    compliant = random.choice([True, False])  # 50% chance
    
    return {
        "rule_name": rule.get("name", "Software Version Check"),
        "rule_type": "software_version",
        "software_name": software_name,
        "required_version": required_version,
        "installed_version": installed_version,
        "compliant": compliant,
        "details": f"Software {software_name} version check",
        "checked_at": datetime.utcnow().isoformat()
    }


def check_security_patch_compliance(asset_details: Dict[str, Any], rule: Dict[str, Any]) -> Dict[str, Any]:
    """Check security patch compliance."""
    patch_level = rule.get("required_patch_level", "latest")
    
    # Simulate patch level check
    current_patch_level = f"KB{random.randint(4000000, 5000000)}"
    compliant = random.choice([True, True, False])  # 67% chance
    
    return {
        "rule_name": rule.get("name", "Security Patch Check"),
        "rule_type": "security_patch",
        "required_patch_level": patch_level,
        "current_patch_level": current_patch_level,
        "compliant": compliant,
        "details": f"Security patch level check",
        "checked_at": datetime.utcnow().isoformat()
    }


def check_configuration_compliance(asset_details: Dict[str, Any], rule: Dict[str, Any]) -> Dict[str, Any]:
    """Check configuration compliance."""
    config_setting = rule.get("setting", "")
    required_value = rule.get("required_value", "")
    
    # Simulate configuration check
    current_value = rule.get("current_value", f"value_{random.randint(1, 100)}")
    compliant = random.choice([True, True, True, False])  # 75% chance
    
    return {
        "rule_name": rule.get("name", "Configuration Check"),
        "rule_type": "configuration",
        "setting": config_setting,
        "required_value": required_value,
        "current_value": current_value,
        "compliant": compliant,
        "details": f"Configuration setting {config_setting} check",
        "checked_at": datetime.utcnow().isoformat()
    }


def check_encryption_compliance(asset_details: Dict[str, Any], rule: Dict[str, Any]) -> Dict[str, Any]:
    """Check encryption compliance."""
    encryption_type = rule.get("encryption_type", "disk")
    
    # Simulate encryption check
    encryption_enabled = random.choice([True, True, False])  # 67% chance
    
    return {
        "rule_name": rule.get("name", "Encryption Check"),
        "rule_type": "encryption",
        "encryption_type": encryption_type,
        "encryption_enabled": encryption_enabled,
        "compliant": encryption_enabled,
        "details": f"{encryption_type} encryption check",
        "checked_at": datetime.utcnow().isoformat()
    }


def calculate_compliance_score(compliance_results: List[Dict[str, Any]]) -> float:
    """Calculate overall compliance score."""
    if not compliance_results:
        return 0.0
    
    compliant_count = sum(1 for result in compliance_results if result.get("compliant", False))
    return (compliant_count / len(compliance_results)) * 100


# =============================================================================
# SUPPORT TASKS
# =============================================================================

@celery_app.task(bind=True, name="asset.get_asset_inventory")
def get_asset_inventory(self, filters: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Get asset inventory with optional filters."""
    task_id = self.request.id
    
    # Simulate inventory retrieval
    time.sleep(random.uniform(1, 3))
    
    # Generate simulated inventory
    inventory = []
    asset_count = random.randint(50, 200)
    
    for i in range(asset_count):
        asset = {
            "asset_id": f"ASSET-{random.randint(100000, 999999)}",
            "asset_type": random.choice(list(AssetType)).value,
            "status": random.choice(list(AssetStatus)).value,
            "manufacturer": random.choice(["Dell", "HP", "Lenovo", "Cisco", "Apple"]),
            "location": random.choice(["Datacenter A", "Datacenter B", "Office Floor 1", "Office Floor 2"])
        }
        inventory.append(asset)
    
    return inventory


@celery_app.task(bind=True, name="asset.update_asset_inventory")
def update_asset_inventory(self, asset_data: Dict[str, Any]) -> Dict[str, Any]:
    """Update asset inventory with discovered asset."""
    task_id = self.request.id
    
    # Simulate inventory update
    time.sleep(random.uniform(0.5, 1.5))
    
    return {
        "updated": True,
        "asset_ip": asset_data.get("ip_address"),
        "asset_type": asset_data.get("asset_type"),
        "updated_at": datetime.utcnow().isoformat(),
        "updater_task_id": task_id
    }


@celery_app.task(bind=True, name="asset.send_asset_assignment_notification")
def send_asset_assignment_notification(self, asset_id: str, user_id: str, assignment_record: Dict[str, Any]) -> Dict[str, Any]:
    """Send notification about asset assignment."""
    task_id = self.request.id
    
    # Simulate notification sending
    time.sleep(random.uniform(0.3, 0.8))
    
    return {
        "notification_sent": True,
        "asset_id": asset_id,
        "user_id": user_id,
        "notification_channels": ["email", "portal"],
        "sent_at": datetime.utcnow().isoformat(),
        "sender_task_id": task_id
    }
