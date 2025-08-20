"""
Enterprise Workflow Module

This module provides comprehensive enterprise-grade workflows for complex business processes
including incident management, asset lifecycle, compliance automation, user onboarding,
disaster recovery, and security response operations.

Available Enterprise Workflows:
==============================

1. Incident Management (incident_management.py):
   - ITSM incident handling and escalation
   - Automated diagnosis and resolution
   - SLA monitoring and compliance
   - Post-incident analysis and reporting

2. Asset Management (asset_management.py):
   - Network asset discovery and inventory
   - Asset lifecycle provisioning
   - Compliance auditing and tracking
   - Equipment and software management

3. Compliance Management (compliance_tasks.py):
   - Multi-framework compliance assessment
   - Audit workflow orchestration
   - Compliance reporting and analytics
   - Regulatory requirement tracking

4. User Onboarding (user_onboarding.py):
   - Employee onboarding workflow orchestration
   - Account provisioning and access setup
   - Training and orientation scheduling
   - Equipment assignment and tracking

5. Backup & Recovery (backup_recovery.py):
   - Automated backup orchestration
   - Disaster recovery procedures
   - Data validation and integrity checking
   - Recovery testing and verification

6. Security Workflows (security_workflows.py):
   - Continuous security monitoring
   - Threat detection and analysis
   - Automated incident response
   - Forensic evidence collection

Usage Examples:
==============

# Incident Management
from app.tasks.enterprise.incident_management import create_incident, initiate_critical_incident_response

# Create new incident
incident_result = create_incident.delay({
    "title": "Database Performance Degradation",
    "description": "Users reporting slow response times",
    "severity": 2,  # High severity
    "affected_services": ["database", "api"],
    "customer_impact": "moderate",
    "assigned_to": "dba_team"
})

# Asset Discovery
from app.tasks.enterprise.asset_management import discover_network_assets

# Discover network assets
discovery_result = discover_network_assets.delay({
    "network_ranges": ["192.168.1.0/24", "10.0.0.0/16"],
    "methods": ["ping", "snmp", "wmi"],
    "enable_vulnerability_scanning": True,
    "enable_compliance_check": True
})

# Compliance Assessment
from app.tasks.enterprise.compliance_tasks import run_comprehensive_assessment

# Run compliance assessment
compliance_result = run_comprehensive_assessment.delay({
    "frameworks": ["gdpr", "sox", "pci_dss"],
    "scope": "full",
    "generate_report": True,
    "notify_stakeholders": True
})

# User Onboarding
from app.tasks.enterprise.user_onboarding import initiate_employee_onboarding

# Onboard new employee
onboarding_result = initiate_employee_onboarding.delay({
    "first_name": "John",
    "last_name": "Doe",
    "email": "john.doe@company.com",
    "department": "engineering",
    "role": "Software Engineer",
    "manager_id": "MGR-001",
    "start_date": "2024-01-15T09:00:00",
    "employee_type": "full_time",
    "security_clearance_level": "standard"
})

# Backup Operations
from app.tasks.enterprise.backup_recovery import execute_scheduled_backups

# Execute backup cycle
backup_result = execute_scheduled_backups.delay({
    "systems": [
        {"name": "database_prod", "data_tier": "critical", "data_size_gb": 500},
        {"name": "api_server", "data_tier": "important", "data_size_gb": 100},
        {"name": "log_server", "data_tier": "standard", "data_size_gb": 1000}
    ],
    "window_hours": 6,
    "backup_config": {
        "storage_config": {
            "compression_enabled": True,
            "encryption_enabled": True,
            "base_path": "/backups"
        }
    }
})

# Security Monitoring
from app.tasks.enterprise.security_workflows import continuous_security_monitoring

# Start security monitoring
monitoring_result = continuous_security_monitoring.delay({
    "sources": ["network_traffic", "system_logs", "user_activity", "endpoint_detection"],
    "cycle_interval_seconds": 300,
    "source_configs": {
        "network_traffic": {"deep_packet_inspection": True},
        "endpoint_detection": {"real_time_scanning": True}
    },
    "response_config": {
        "auto_isolate_enabled": True,
        "notification_channels": ["email", "slack", "sms"]
    }
})

# Disaster Recovery
from app.tasks.enterprise.backup_recovery import initiate_disaster_recovery

# Initiate disaster recovery
dr_result = initiate_disaster_recovery.delay({
    "scenario": "datacenter_outage",
    "disaster_type": "infrastructure_failure",
    "affected_systems": [
        {"name": "primary_db", "criticality": "critical", "rto_minutes": 60},
        {"name": "api_cluster", "criticality": "critical", "rto_minutes": 30},
        {"name": "web_frontend", "criticality": "important", "rto_minutes": 120}
    ]
})

Available Tasks:
===============

Incident Management Tasks:
- incident.create_incident
- incident.initiate_critical_incident_response
- incident.escalate_incident
- incident.initiate_automated_diagnosis
- incident.check_system_health
- incident.analyze_logs
- incident.check_dependencies
- incident.run_connectivity_tests
- incident.check_resource_utilization
- incident.aggregate_diagnostic_results
- incident.monitor_incident_sla
- incident.handle_sla_breach

Asset Management Tasks:
- asset.discover_network_assets
- asset.scan_network_range
- asset.aggregate_discovery_results
- asset.provision_new_asset
- asset.create_asset_record
- asset.configure_asset
- asset.install_software
- asset.apply_security_policies
- asset.assign_asset_to_user
- asset.update_asset_status
- asset.run_compliance_audit
- asset.check_asset_compliance

Compliance Tasks:
- compliance.run_comprehensive_assessment
- compliance.assess_framework_compliance
- compliance.check_compliance_requirement
- compliance.analyze_cross_framework_compliance
- compliance.initiate_audit
- compliance.collect_audit_evidence
- compliance.generate_compliance_report
- compliance.distribute_compliance_report

User Onboarding Tasks:
- onboarding.initiate_employee_onboarding
- onboarding.execute_pre_start_onboarding
- onboarding.execute_onboarding_workflow
- onboarding.execute_onboarding_stage
- onboarding.create_user_accounts
- onboarding.setup_email_account
- onboarding.order_equipment
- onboarding.configure_access_permissions
- onboarding.schedule_orientation
- onboarding.verify_onboarding_completion

Backup & Recovery Tasks:
- backup.execute_scheduled_backups
- backup.execute_system_backup
- backup.validate_system_before_backup
- backup.create_backup_snapshot
- backup.transfer_backup_data
- backup.verify_backup_integrity
- backup.update_backup_catalog
- backup.initiate_disaster_recovery
- backup.assess_disaster_scope
- backup.create_disaster_recovery_plan
- backup.execute_system_recovery
- backup.find_latest_backup
- backup.validate_backup_for_recovery
- backup.restore_system_data
- backup.verify_system_recovery

Security Workflow Tasks:
- security.continuous_security_monitoring
- security.monitor_security_source
- security.analyze_security_events
- security.execute_immediate_response
- security.execute_response_action
- security.create_security_incident
- security.notify_security_team

Configuration Classes:
=====================

- IncidentContext: Incident information and metadata
- IncidentSeverity: ITIL-standard incident severity levels
- AssetInfo: Asset lifecycle information
- AssetType: IT asset classifications
- ComplianceFramework: Supported compliance frameworks
- ComplianceRequirement: Compliance requirement definitions
- EmployeeProfile: Employee onboarding information
- OnboardingStage: Employee onboarding lifecycle stages
- BackupPolicy: Backup policy configurations
- SecurityEvent: Security event data structures
- ThreatLevel: Security threat classifications

Integration Patterns:
====================

These enterprise workflows are designed to integrate with:

1. **ITSM Systems**: ServiceNow, Remedy, Jira Service Management
2. **Asset Management**: Lansweeper, ManageEngine AssetExplorer
3. **Compliance Platforms**: ServiceNow GRC, MetricStream, LogicGate
4. **HR Systems**: Workday, BambooHR, ADP
5. **Backup Solutions**: Veeam, Commvault, NetBackup
6. **Security Tools**: Splunk, QRadar, CrowdStrike, SentinelOne
7. **Infrastructure**: VMware, AWS, Azure, Kubernetes
8. **Monitoring**: Datadog, New Relic, Prometheus, Grafana

Best Practices:
==============

1. **Error Handling**: All workflows include comprehensive error handling with retry logic
2. **Audit Trail**: Complete audit trails for compliance and forensic analysis
3. **Notifications**: Multi-channel notifications (email, Slack, SMS, dashboard)
4. **Progress Tracking**: Real-time progress tracking and status updates
5. **Resource Management**: Efficient resource utilization and cleanup
6. **Security**: Secure handling of sensitive data and credentials
7. **Scalability**: Designed for high-volume enterprise environments
8. **Integration**: RESTful APIs and webhook support for external systems
"""

# Import all enterprise modules to register tasks
from . import incident_management
from . import asset_management
from . import compliance_tasks
from . import user_onboarding
from . import backup_recovery
from . import security_workflows

# Export key classes and enums for external use
from .incident_management import IncidentContext, IncidentSeverity, IncidentStatus, EscalationLevel
from .asset_management import AssetInfo, AssetType, AssetStatus, ComplianceStatus
from .compliance_tasks import ComplianceFramework, ComplianceRequirement, ComplianceStatus, AuditType
from .user_onboarding import EmployeeProfile, OnboardingStage, EmployeeType, Department
from .backup_recovery import BackupPolicy, BackupType, BackupStatus, RecoveryType, DataTier
from .security_workflows import SecurityEvent, ThreatLevel, SecurityEventType, ResponseAction

__all__ = [
    # Modules
    'incident_management',
    'asset_management',
    'compliance_tasks', 
    'user_onboarding',
    'backup_recovery',
    'security_workflows',
    
    # Incident Management Classes
    'IncidentContext',
    'IncidentSeverity',
    'IncidentStatus',
    'EscalationLevel',
    
    # Asset Management Classes
    'AssetInfo',
    'AssetType', 
    'AssetStatus',
    'ComplianceStatus',
    
    # Compliance Classes
    'ComplianceFramework',
    'ComplianceRequirement',
    'AuditType',
    
    # User Onboarding Classes
    'EmployeeProfile',
    'OnboardingStage',
    'EmployeeType',
    'Department',
    
    # Backup & Recovery Classes
    'BackupPolicy',
    'BackupType',
    'BackupStatus',
    'RecoveryType',
    'DataTier',
    
    # Security Classes
    'SecurityEvent',
    'ThreatLevel',
    'SecurityEventType', 
    'ResponseAction'
]
