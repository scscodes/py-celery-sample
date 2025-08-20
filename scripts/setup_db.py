#!/usr/bin/env python3
"""
Database setup script for Celery Showcase project.

This script initializes the database, creates all tables,
and provides options for resetting the database if needed.
"""

import sys
import os
from pathlib import Path

# Add the app directory to the Python path
app_dir = Path(__file__).parent.parent
sys.path.insert(0, str(app_dir))

from sqlalchemy import text
from app.core.database import engine, create_tables, drop_tables, SessionLocal
from app.models import *  # Import all models to ensure they're registered
from app.config.settings import settings


def check_database_connection():
    """Check if database connection is working."""
    try:
        with engine.connect() as conn:
            result = conn.execute(text("SELECT 1"))
            print("✅ Database connection successful")
            return True
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        return False


def create_database_tables():
    """Create all database tables."""
    try:
        print("📝 Creating database tables...")
        create_tables()
        print("✅ Database tables created successfully")
        
        # List created tables
        inspector = engine.dialect.get_table_names(engine.connect())
        print(f"📋 Created tables: {', '.join(inspector)}")
        
        return True
    except Exception as e:
        print(f"❌ Failed to create tables: {e}")
        return False


def reset_database():
    """Drop and recreate all database tables."""
    try:
        print("⚠️  Dropping all existing tables...")
        drop_tables()
        print("✅ Tables dropped successfully")
        
        print("📝 Recreating database tables...")
        create_tables()
        print("✅ Database reset completed")
        
        return True
    except Exception as e:
        print(f"❌ Failed to reset database: {e}")
        return False


def verify_tables():
    """Verify that all expected tables exist."""
    try:
        db = SessionLocal()
        
        # Expected tables based on our models
        expected_tables = [
            'users', 'groups', 'user_group_membership',
            'computers', 'events', 'incidents'
        ]
        
        # Check each table
        for table_name in expected_tables:
            try:
                result = db.execute(text(f"SELECT COUNT(*) FROM {table_name}"))
                count = result.scalar()
                print(f"✅ Table '{table_name}': {count} records")
            except Exception as e:
                print(f"❌ Table '{table_name}': Error - {e}")
                return False
        
        db.close()
        return True
        
    except Exception as e:
        print(f"❌ Table verification failed: {e}")
        return False


def main():
    """Main setup function."""
    print("🚀 Celery Showcase Database Setup")
    print("=" * 40)
    print(f"Database URL: {settings.database_url}")
    print()
    
    # Check database connection
    if not check_database_connection():
        print("❌ Cannot proceed without database connection")
        sys.exit(1)
    
    # Handle command line arguments
    if len(sys.argv) > 1:
        command = sys.argv[1].lower()
        
        if command == "reset":
            print("⚠️  WARNING: This will delete all existing data!")
            response = input("Are you sure you want to reset the database? (yes/no): ")
            
            if response.lower() == "yes":
                if reset_database():
                    print("✅ Database reset completed successfully")
                else:
                    print("❌ Database reset failed")
                    sys.exit(1)
            else:
                print("❌ Database reset cancelled")
                sys.exit(0)
                
        elif command == "verify":
            print("🔍 Verifying database tables...")
            if verify_tables():
                print("✅ All tables verified successfully")
            else:
                print("❌ Table verification failed")
                sys.exit(1)
                
        else:
            print(f"❌ Unknown command: {command}")
            print("Available commands: reset, verify")
            sys.exit(1)
    
    else:
        # Default action: create tables if they don't exist
        print("📝 Setting up database tables...")
        
        if create_database_tables():
            print()
            print("🔍 Verifying created tables...")
            if verify_tables():
                print()
                print("✅ Database setup completed successfully!")
                print()
                print("Next steps:")
                print("1. Run seed data script: python scripts/seed_data.py")
                print("2. Start Redis server: redis-server")
                print("3. Start Celery worker: celery -A app.tasks.celery_app worker --loglevel=info")
                print("4. Start FastAPI server: uvicorn app.main:app --reload")
            else:
                print("❌ Database setup verification failed")
                sys.exit(1)
        else:
            print("❌ Database setup failed")
            sys.exit(1)


if __name__ == "__main__":
    main()
