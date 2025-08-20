#!/usr/bin/env python3
"""
Database seed data script for Celery Showcase project.

This script populates the database with realistic mock data
for testing and demonstration purposes using Faker.
"""

import sys
import os
import random
from pathlib import Path
from datetime import datetime, timedelta
from typing import List

# Add the app directory to the Python path
app_dir = Path(__file__).parent.parent
sys.path.insert(0, str(app_dir))

from faker import Faker
from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.models import (
    User, Group, Computer, Event, Incident,
    EventType, EventSeverity, IncidentStatus, IncidentPriority,
    user_group_association
)

# Initialize Faker
fake = Faker()
Faker.seed(42)  # For reproducible data


class DataSeeder:
    """Class to handle database seeding operations."""
    
    def __init__(self):
        self.db: Session = SessionLocal()
        self.users: List[User] = []
        self.groups: List[Group] = []
        self.computers: List[Computer] = []
        
    def close(self):
        """Close database session."""
        self.db.close()
    
    def clear_existing_data(self):
        """Clear all existing data from tables."""
        print("🧹 Clearing existing data...")
        
        # Delete in reverse order of dependencies
        self.db.query(Incident).delete()
        self.db.query(Event).delete()
        self.db.query(Computer).delete()
        self.db.execute(user_group_association.delete())
        self.db.query(Group).delete()
        self.db.query(User).delete()
        
        self.db.commit()
        print("✅ Existing data cleared")
    
    def create_groups(self, count: int = 15):
        """Create groups with realistic enterprise structure."""
        print(f"👥 Creating {count} groups...")
        
        # Define realistic group types and names
        group_templates = [
            # IT Groups
            {"name": "IT Administrators", "type": "security", "description": "System administrators with full access"},
            {"name": "Help Desk", "type": "security", "description": "IT support staff"},
            {"name": "Network Administrators", "type": "security", "description": "Network infrastructure management"},
            {"name": "Database Administrators", "type": "security", "description": "Database management team"},
            {"name": "Security Team", "type": "security", "description": "Information security specialists"},
            
            # Department Groups
            {"name": "Engineering", "type": "organizational", "description": "Software development team"},
            {"name": "Human Resources", "type": "organizational", "description": "HR department staff"},
            {"name": "Finance", "type": "organizational", "description": "Financial operations team"},
            {"name": "Sales", "type": "organizational", "description": "Sales and business development"},
            {"name": "Marketing", "type": "organizational", "description": "Marketing and communications"},
            
            # Access Groups
            {"name": "VPN Users", "type": "security", "description": "Remote access permissions"},
            {"name": "File Server Access", "type": "security", "description": "Shared file system access"},
            {"name": "Executive Team", "type": "security", "description": "Senior leadership access"},
            {"name": "Contractors", "type": "security", "description": "External contractor access"},
            {"name": "Interns", "type": "security", "description": "Intern user permissions"}
        ]
        
        for i, template in enumerate(group_templates[:count]):
            group = Group(
                name=template["name"],
                description=template["description"],
                group_type=template["type"],
                scope=random.choice(["global", "domain", "universal"]),
                managed_by=fake.user_name(),
                is_active=True,
                distinguished_name=f"CN={template['name']},OU=Groups,DC=company,DC=com"
            )
            
            self.db.add(group)
            self.groups.append(group)
        
        self.db.commit()
        print(f"✅ Created {len(self.groups)} groups")
    
    def create_users(self, count: int = 50):
        """Create users with realistic enterprise attributes."""
        print(f"👤 Creating {count} users...")
        
        departments = ["Engineering", "IT", "Human Resources", "Finance", "Sales", "Marketing", "Operations"]
        titles = [
            "Software Engineer", "Senior Developer", "DevOps Engineer", "Product Manager",
            "System Administrator", "Network Engineer", "Security Analyst", "Database Administrator",
            "HR Manager", "Recruiter", "Financial Analyst", "Accountant",
            "Sales Manager", "Account Executive", "Marketing Specialist", "Content Manager"
        ]
        
        # Create a few managers first
        managers = []
        for i in range(7):  # One manager per department
            manager = User(
                username=fake.user_name(),
                email=fake.email(),
                first_name=fake.first_name(),
                last_name=fake.last_name(),
                department=departments[i],
                title=f"{departments[i]} Manager",
                employee_id=f"EMP{1000 + i}",
                phone=fake.phone_number(),
                office_location=fake.city(),
                is_active=True,
                last_login=fake.date_time_between(start_date="-30d", end_date="now")
            )
            manager.display_name = f"{manager.first_name} {manager.last_name}"
            
            self.db.add(manager)
            managers.append(manager)
            self.users.append(manager)
        
        self.db.commit()  # Commit managers first to get IDs
        
        # Create regular employees
        for i in range(len(managers), count):
            department = random.choice(departments)
            manager = random.choice([m for m in managers if m.department == department])
            
            user = User(
                username=fake.user_name(),
                email=fake.email(),
                first_name=fake.first_name(),
                last_name=fake.last_name(),
                department=department,
                title=random.choice(titles),
                manager_id=manager.id,
                employee_id=f"EMP{1000 + i}",
                phone=fake.phone_number() if random.random() > 0.3 else None,
                office_location=fake.city() if random.random() > 0.2 else None,
                is_active=random.random() > 0.05,  # 95% active users
                is_locked=random.random() < 0.02,  # 2% locked accounts
                password_last_changed=fake.date_time_between(start_date="-90d", end_date="-1d"),
                last_login=fake.date_time_between(start_date="-7d", end_date="now") if random.random() > 0.1 else None,
                failed_login_attempts=random.randint(0, 2) if random.random() > 0.8 else 0
            )
            user.display_name = f"{user.first_name} {user.last_name}"
            
            self.db.add(user)
            self.users.append(user)
        
        self.db.commit()
        print(f"✅ Created {len(self.users)} users")
    
    def assign_users_to_groups(self):
        """Assign users to groups based on department and role."""
        print("🔗 Assigning users to groups...")
        
        assignments = 0
        
        for user in self.users:
            # Assign to department group
            dept_groups = [g for g in self.groups if g.name == user.department]
            if dept_groups:
                user.groups.append(dept_groups[0])
                assignments += 1
            
            # Assign IT users to IT groups
            if user.department == "IT":
                it_groups = [g for g in self.groups if "IT" in g.name or "Network" in g.name or "Database" in g.name]
                for group in random.sample(it_groups, min(2, len(it_groups))):
                    if group not in user.groups:
                        user.groups.append(group)
                        assignments += 1
            
            # Assign managers to executive group
            if "Manager" in user.title:
                exec_groups = [g for g in self.groups if g.name == "Executive Team"]
                if exec_groups and exec_groups[0] not in user.groups:
                    user.groups.append(exec_groups[0])
                    assignments += 1
            
            # Random additional group assignments
            if random.random() > 0.5:
                available_groups = [g for g in self.groups if g not in user.groups and g.group_type == "security"]
                if available_groups:
                    additional_group = random.choice(available_groups)
                    user.groups.append(additional_group)
                    assignments += 1
        
        self.db.commit()
        print(f"✅ Created {assignments} group memberships")
    
    def create_computers(self, count: int = 75):
        """Create computers with realistic enterprise configurations."""
        print(f"💻 Creating {count} computers...")
        
        manufacturers = ["Dell", "HP", "Lenovo", "Apple", "Microsoft"]
        os_options = [
            "Windows 11 Pro", "Windows 10 Pro", "Windows Server 2022",
            "macOS Ventura", "macOS Monterey", "Ubuntu 22.04 LTS", "CentOS 8"
        ]
        
        for i in range(count):
            manufacturer = random.choice(manufacturers)
            os = random.choice(os_options)
            
            # Generate realistic hostname
            dept_prefix = random.choice(["ENG", "IT", "HR", "FIN", "SAL", "MKT"])
            hostname = f"{dept_prefix}-{manufacturer[:3].upper()}-{1000 + i}"
            
            computer = Computer(
                hostname=hostname.lower(),
                asset_tag=f"AST{10000 + i}",
                serial_number=fake.bothify(text="??######"),
                ip_address=fake.ipv4_private(),
                mac_address=fake.mac_address(),
                domain="company.local",
                manufacturer=manufacturer,
                model=f"{manufacturer} Model {random.randint(1, 9)}",
                cpu=f"Intel Core i{random.choice([5, 7, 9])}-{random.randint(8000, 13000)}",
                ram_gb=random.choice([8, 16, 32, 64]),
                storage_gb=random.choice([256, 512, 1024, 2048]),
                operating_system=os,
                os_version=f"{os.split()[0]} {random.randint(1, 5)}.{random.randint(0, 9)}",
                owner_id=random.choice(self.users).id if random.random() > 0.1 else None,
                department=random.choice(["Engineering", "IT", "HR", "Finance", "Sales", "Marketing"]),
                location=fake.city(),
                status=random.choices(
                    ["active", "inactive", "maintenance", "retired"],
                    weights=[85, 10, 3, 2]
                )[0],
                health_status=random.choices(
                    ["healthy", "warning", "critical", "unknown"],
                    weights=[70, 20, 5, 5]
                )[0],
                is_online=random.random() > 0.15,  # 85% online
                last_seen=fake.date_time_between(start_date="-7d", end_date="now"),
                is_compliant=random.random() > 0.1,  # 90% compliant
                encryption_status=random.choice(["encrypted", "unencrypted", "partial"]),
                cpu_usage_percent=random.uniform(10, 90),
                memory_usage_percent=random.uniform(20, 85),
                disk_usage_percent=random.uniform(30, 95),
                uptime_hours=random.randint(1, 720),  # Up to 30 days
                purchase_date=fake.date_between(start_date="-3y", end_date="-1m"),
                warranty_expiry=fake.date_between(start_date="now", end_date="+2y"),
                cost=random.uniform(800, 5000),
                last_patch_date=fake.date_time_between(start_date="-30d", end_date="now")
            )
            
            # Set compliance issues for non-compliant computers
            if not computer.is_compliant:
                issues = random.sample([
                    "Missing security patches",
                    "Outdated antivirus definitions", 
                    "Unauthorized software installed",
                    "Weak password policy",
                    "Missing encryption"
                ], random.randint(1, 3))
                computer.compliance_issues = "; ".join(issues)
            
            self.db.add(computer)
            self.computers.append(computer)
        
        self.db.commit()
        print(f"✅ Created {len(self.computers)} computers")
    
    def create_events(self, count: int = 200):
        """Create system events with realistic patterns."""
        print(f"📝 Creating {count} events...")
        
        event_templates = [
            # System events
            {"type": EventType.SYSTEM, "severity": EventSeverity.INFO, "title": "System startup completed", "source": "Windows"},
            {"type": EventType.SYSTEM, "severity": EventSeverity.WARNING, "title": "High CPU usage detected", "source": "Performance Monitor"},
            {"type": EventType.SYSTEM, "severity": EventSeverity.ERROR, "title": "Service failed to start", "source": "Service Control Manager"},
            {"type": EventType.SYSTEM, "severity": EventSeverity.CRITICAL, "title": "System crash detected", "source": "Kernel"},
            
            # Security events
            {"type": EventType.SECURITY, "severity": EventSeverity.INFO, "title": "User logged in successfully", "source": "Active Directory"},
            {"type": EventType.SECURITY, "severity": EventSeverity.WARNING, "title": "Failed login attempt", "source": "Active Directory"},
            {"type": EventType.SECURITY, "severity": EventSeverity.ERROR, "title": "Account locked due to failed attempts", "source": "Security"},
            {"type": EventType.SECURITY, "severity": EventSeverity.CRITICAL, "title": "Potential security breach detected", "source": "Antivirus"},
            
            # Network events
            {"type": EventType.NETWORK, "severity": EventSeverity.INFO, "title": "Network connection established", "source": "Network"},
            {"type": EventType.NETWORK, "severity": EventSeverity.WARNING, "title": "High network latency", "source": "Network Monitor"},
            {"type": EventType.NETWORK, "severity": EventSeverity.ERROR, "title": "Network connection lost", "source": "Network"},
            
            # Hardware events
            {"type": EventType.HARDWARE, "severity": EventSeverity.WARNING, "title": "Hard drive temperature high", "source": "Hardware Monitor"},
            {"type": EventType.HARDWARE, "severity": EventSeverity.CRITICAL, "title": "Hard drive failure predicted", "source": "SMART"},
            
            # Application events
            {"type": EventType.APPLICATION, "severity": EventSeverity.INFO, "title": "Application started successfully", "source": "Application"},
            {"type": EventType.APPLICATION, "severity": EventSeverity.ERROR, "title": "Application crashed", "source": "Application"}
        ]
        
        for i in range(count):
            template = random.choice(event_templates)
            
            event = Event(
                event_id=f"EVT-{datetime.now().strftime('%Y%m%d')}-{10000 + i}",
                event_type=template["type"],
                severity=template["severity"],
                source=template["source"],
                title=template["title"],
                description=fake.text(max_nb_chars=200),
                raw_data='{"additional": "event data"}',
                occurred_at=fake.date_time_between(start_date="-30d", end_date="now"),
                computer_id=random.choice(self.computers).id if random.random() > 0.2 else None,
                user_id=random.choice(self.users).id if random.random() > 0.6 else None,
                is_processed=random.random() > 0.3,  # 70% processed
                correlation_id=f"CORR-{random.randint(1000, 9999)}" if random.random() > 0.7 else None
            )
            
            if event.is_processed:
                event.processed_at = event.occurred_at + timedelta(minutes=random.randint(5, 120))
            
            self.db.add(event)
        
        self.db.commit()
        print(f"✅ Created {count} events")
    
    def create_incidents(self, count: int = 30):
        """Create incidents with realistic IT service management patterns."""
        print(f"🎫 Creating {count} incidents...")
        
        incident_templates = [
            {"title": "Computer not starting", "category": "Hardware", "priority": IncidentPriority.HIGH},
            {"title": "Cannot access network shares", "category": "Network", "priority": IncidentPriority.MEDIUM},
            {"title": "Email not working", "category": "Software", "priority": IncidentPriority.MEDIUM},
            {"title": "Printer not responding", "category": "Hardware", "priority": IncidentPriority.LOW},
            {"title": "Application keeps crashing", "category": "Software", "priority": IncidentPriority.HIGH},
            {"title": "Internet connection slow", "category": "Network", "priority": IncidentPriority.LOW},
            {"title": "Cannot log into system", "category": "Access", "priority": IncidentPriority.URGENT},
            {"title": "Server is down", "category": "Infrastructure", "priority": IncidentPriority.CRITICAL},
        ]
        
        for i in range(count):
            template = random.choice(incident_templates)
            created_date = fake.date_time_between(start_date="-60d", end_date="now")
            
            # Determine status based on age
            age_days = (datetime.now() - created_date).days
            if age_days > 30:
                status = random.choice([IncidentStatus.RESOLVED, IncidentStatus.CLOSED])
            elif age_days > 7:
                status = random.choice([IncidentStatus.IN_PROGRESS, IncidentStatus.PENDING, IncidentStatus.RESOLVED])
            else:
                status = random.choice([IncidentStatus.NEW, IncidentStatus.ASSIGNED, IncidentStatus.IN_PROGRESS])
            
            incident = Incident(
                ticket_id=f"INC-{created_date.strftime('%Y%m%d')}-{1000 + i}",
                title=template["title"],
                description=fake.text(max_nb_chars=300),
                category=template["category"],
                subcategory=fake.word(),
                priority=template["priority"],
                impact=random.choice(["High", "Medium", "Low"]),
                urgency=random.choice(["High", "Medium", "Low"]),
                status=status,
                reporter_id=random.choice(self.users).id,
                assignee_id=random.choice(self.users).id if status != IncidentStatus.NEW else None,
                assigned_group=random.choice(["Help Desk", "IT Administrators", "Network Team"]),
                affected_computer_id=random.choice(self.computers).id if random.random() > 0.4 else None,
                affected_users_count=random.randint(1, 10),
                sla_due_date=created_date + timedelta(hours=random.choice([4, 8, 24, 72])),
                requires_change=random.random() > 0.8,
                escalated=random.random() > 0.9,
                public_notes=fake.text(max_nb_chars=150) if random.random() > 0.5 else None,
                private_notes=fake.text(max_nb_chars=150) if random.random() > 0.3 else None,
                created_at=created_date
            )
            
            # Set resolution details for closed incidents
            if status in [IncidentStatus.RESOLVED, IncidentStatus.CLOSED]:
                incident.resolved_at = created_date + timedelta(hours=random.randint(1, 48))
                incident.resolution = fake.text(max_nb_chars=200)
                incident.calculate_resolution_time()
                
                if status == IncidentStatus.CLOSED:
                    incident.closed_at = incident.resolved_at + timedelta(hours=random.randint(1, 24))
            
            # Check SLA breach
            if incident.sla_due_date and datetime.now() > incident.sla_due_date and incident.is_open:
                incident.sla_breached = True
            
            self.db.add(incident)
        
        self.db.commit()
        print(f"✅ Created {count} incidents")
    
    def run_full_seed(self, 
                     users_count: int = 50,
                     groups_count: int = 15, 
                     computers_count: int = 75,
                     events_count: int = 200,
                     incidents_count: int = 30):
        """Run complete database seeding process."""
        print("🌱 Starting database seeding process...")
        print("=" * 50)
        
        try:
            # Clear existing data
            self.clear_existing_data()
            
            # Create data in dependency order
            self.create_groups(groups_count)
            self.create_users(users_count)
            self.assign_users_to_groups()
            self.create_computers(computers_count)
            self.create_events(events_count)
            self.create_incidents(incidents_count)
            
            print()
            print("✅ Database seeding completed successfully!")
            print("=" * 50)
            print(f"📊 Summary:")
            print(f"   Users: {len(self.users)}")
            print(f"   Groups: {len(self.groups)}")
            print(f"   Computers: {len(self.computers)}")
            print(f"   Events: {events_count}")
            print(f"   Incidents: {incidents_count}")
            
        except Exception as e:
            print(f"❌ Seeding failed: {e}")
            self.db.rollback()
            raise


def main():
    """Main seeding function."""
    seeder = DataSeeder()
    
    try:
        if len(sys.argv) > 1 and sys.argv[1] == "small":
            # Smaller dataset for quick testing
            seeder.run_full_seed(
                users_count=20,
                groups_count=10,
                computers_count=30,
                events_count=100,
                incidents_count=15
            )
        else:
            # Full dataset
            seeder.run_full_seed()
            
    finally:
        seeder.close()


if __name__ == "__main__":
    main()
