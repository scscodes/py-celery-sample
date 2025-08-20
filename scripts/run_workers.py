#!/usr/bin/env python3
"""
Celery worker management script for Celery Showcase project.

This script provides an easy way to start Celery workers with
different configurations and queue assignments.
"""

import sys
import os
import subprocess
import signal
from pathlib import Path
from typing import List, Dict

# Add the app directory to the Python path
app_dir = Path(__file__).parent.parent
sys.path.insert(0, str(app_dir))

from app.config.settings import settings


class WorkerManager:
    """Manage Celery workers and related services."""
    
    def __init__(self):
        self.processes: List[subprocess.Popen] = []
        
    def cleanup(self):
        """Clean up all running processes."""
        print("🧹 Cleaning up worker processes...")
        for process in self.processes:
            try:
                process.terminate()
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()
        
    def start_redis_check(self) -> bool:
        """Check if Redis is available."""
        try:
            import redis
            r = redis.from_url(settings.redis_url)
            r.ping()
            print("✅ Redis connection successful")
            return True
        except Exception as e:
            print(f"❌ Redis connection failed: {e}")
            print("💡 Make sure Redis is running: redis-server")
            return False
    
    def start_worker(self, 
                    worker_name: str = "default",
                    queues: List[str] = None, 
                    concurrency: int = 4,
                    loglevel: str = "info") -> subprocess.Popen:
        """Start a Celery worker process."""
        
        if queues is None:
            queues = ["default"]
        
        cmd = [
            "celery", 
            "-A", "app.tasks.celery_app",
            "worker",
            "--hostname", f"{worker_name}@%h",
            "--queues", ",".join(queues),
            "--concurrency", str(concurrency),
            "--loglevel", loglevel,
            "--prefetch-multiplier", "1"
        ]
        
        print(f"🚀 Starting worker '{worker_name}' for queues: {', '.join(queues)}")
        print(f"   Command: {' '.join(cmd)}")
        
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            universal_newlines=True,
            bufsize=1
        )
        
        self.processes.append(process)
        return process
    
    def start_beat(self) -> subprocess.Popen:
        """Start Celery beat scheduler."""
        cmd = [
            "celery",
            "-A", "app.tasks.celery_app", 
            "beat",
            "--loglevel", "info"
        ]
        
        print("⏰ Starting Celery beat scheduler...")
        print(f"   Command: {' '.join(cmd)}")
        
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            universal_newlines=True,
            bufsize=1
        )
        
        self.processes.append(process)
        return process
    
    def start_flower(self, port: int = 5555) -> subprocess.Popen:
        """Start Flower monitoring interface."""
        cmd = [
            "celery",
            "-A", "app.tasks.celery_app",
            "flower",
            "--port", str(port),
            "--broker", settings.celery_broker_url
        ]
        
        print(f"🌸 Starting Flower monitoring on port {port}...")
        print(f"   Command: {' '.join(cmd)}")
        print(f"   Access at: http://localhost:{port}")
        
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            universal_newlines=True,
            bufsize=1
        )
        
        self.processes.append(process)
        return process
    
    def run_development_setup(self):
        """Run complete development environment."""
        print("🔧 Starting development environment...")
        print("=" * 50)
        
        # Check Redis connection
        if not self.start_redis_check():
            return False
        
        try:
            # Start multiple workers for different queues
            self.start_worker("default_worker", ["default"], concurrency=2)
            self.start_worker("orchestration_worker", ["orchestration"], concurrency=2)
            self.start_worker("enterprise_worker", ["enterprise"], concurrency=2)
            
            # Start beat scheduler
            self.start_beat()
            
            # Start flower monitoring
            self.start_flower()
            
            print()
            print("✅ All services started successfully!")
            print("=" * 50)
            print("🖥️  Services running:")
            print("   - Default Worker (queue: default)")
            print("   - Orchestration Worker (queue: orchestration)")  
            print("   - Enterprise Worker (queue: enterprise)")
            print("   - Beat Scheduler (periodic tasks)")
            print("   - Flower Monitoring (http://localhost:5555)")
            print()
            print("💡 Useful commands:")
            print("   - Check worker status: celery -A app.tasks.celery_app inspect active")
            print("   - Send test task: python -c \"from app.tasks.basic.cache_tasks import cache_health_check; cache_health_check.delay()\"")
            print("   - Stop all: Ctrl+C")
            print()
            print("⌨️  Press Ctrl+C to stop all services...")
            
            # Wait for interrupt
            signal.signal(signal.SIGINT, lambda s, f: self.cleanup())
            signal.signal(signal.SIGTERM, lambda s, f: self.cleanup())
            
            # Keep main process alive
            while True:
                for process in self.processes[:]:  # Copy list to avoid modification during iteration
                    if process.poll() is not None:
                        print(f"⚠️  Process {process.pid} has exited")
                        self.processes.remove(process)
                
                if not self.processes:
                    print("❌ All processes have exited")
                    break
                    
                try:
                    # Read output from processes
                    for process in self.processes:
                        if process.stdout and process.stdout.readable():
                            line = process.stdout.readline()
                            if line:
                                print(f"[{process.pid}] {line.strip()}")
                except:
                    pass
                
        except KeyboardInterrupt:
            print("\\n🛑 Received interrupt signal")
            self.cleanup()
            return True
        
        except Exception as e:
            print(f"❌ Error running development setup: {e}")
            self.cleanup()
            return False
    
    def run_single_worker(self, queues: List[str] = None, concurrency: int = 4):
        """Run a single worker for testing."""
        print("🔧 Starting single worker for testing...")
        
        if not self.start_redis_check():
            return False
        
        if queues is None:
            queues = ["default", "orchestration", "enterprise"]
        
        try:
            worker_process = self.start_worker(
                "test_worker", 
                queues, 
                concurrency=concurrency,
                loglevel="debug"
            )
            
            print(f"✅ Worker started for queues: {', '.join(queues)}")
            print("⌨️  Press Ctrl+C to stop...")
            
            # Handle output and wait for completion
            signal.signal(signal.SIGINT, lambda s, f: self.cleanup())
            
            # Stream output
            for line in worker_process.stdout:
                print(line.strip())
                
        except KeyboardInterrupt:
            print("\\n🛑 Stopping worker...")
            self.cleanup()
            return True
        
        except Exception as e:
            print(f"❌ Error running worker: {e}")
            self.cleanup()
            return False


def print_usage():
    """Print script usage information."""
    print("🔧 Celery Worker Management Script")
    print("=" * 40)
    print("Usage: python scripts/run_workers.py [command]")
    print()
    print("Commands:")
    print("  dev       - Start full development environment (default)")
    print("  worker    - Start single worker for testing")
    print("  flower    - Start only Flower monitoring")
    print("  beat      - Start only beat scheduler")
    print("  check     - Check Redis connection")
    print()
    print("Examples:")
    print("  python scripts/run_workers.py dev")
    print("  python scripts/run_workers.py worker")
    print("  python scripts/run_workers.py flower")


def main():
    """Main worker management function."""
    manager = WorkerManager()
    
    command = sys.argv[1] if len(sys.argv) > 1 else "dev"
    
    try:
        if command == "dev":
            manager.run_development_setup()
            
        elif command == "worker":
            manager.run_single_worker()
            
        elif command == "flower":
            if manager.start_redis_check():
                manager.start_flower()
                print("⌨️  Press Ctrl+C to stop Flower...")
                signal.signal(signal.SIGINT, lambda s, f: manager.cleanup())
                manager.processes[0].wait()
            
        elif command == "beat":
            if manager.start_redis_check():
                manager.start_beat()
                print("⌨️  Press Ctrl+C to stop Beat...")
                signal.signal(signal.SIGINT, lambda s, f: manager.cleanup())
                manager.processes[0].wait()
            
        elif command == "check":
            manager.start_redis_check()
            
        elif command in ["help", "-h", "--help"]:
            print_usage()
            
        else:
            print(f"❌ Unknown command: {command}")
            print_usage()
            sys.exit(1)
            
    except Exception as e:
        print(f"❌ Script error: {e}")
        manager.cleanup()
        sys.exit(1)
    
    finally:
        manager.cleanup()


if __name__ == "__main__":
    main()
