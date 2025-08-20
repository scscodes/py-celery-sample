"""
Database Mock

Mock implementation of database operations for testing and development.
Simulates various database systems with configurable behavior.
"""

import logging
import asyncio
import random
import time
from typing import Dict, List, Optional, Any, Union
from datetime import datetime
import json
import copy

logger = logging.getLogger(__name__)


class DatabaseMock:
    """Mock database implementation with realistic behavior simulation."""
    
    def __init__(self, db_type: str = "postgresql", failure_rate: float = 0.02):
        self.db_type = db_type
        self.failure_rate = failure_rate
        self.response_delay = (0.01, 0.1)  # Min/max response time in seconds
        self.connection_pool_size = 20
        self.active_connections = 0
        
        # In-memory storage for mock data
        self._tables = {}
        self._sequences = {}
        self._indexes = {}
        
        # Performance metrics
        self._query_count = 0
        self._error_count = 0
        self._total_response_time = 0.0
        
        logger.info(f"DatabaseMock initialized: {db_type}")
    
    async def connect(self) -> bool:
        """Simulate database connection."""
        await self._simulate_delay()
        
        if self._should_fail():
            raise Exception(f"Database connection failed: {self.db_type} unreachable")
        
        if self.active_connections >= self.connection_pool_size:
            raise Exception("Connection pool exhausted")
        
        self.active_connections += 1
        logger.debug(f"Database connected (active: {self.active_connections})")
        return True
    
    async def disconnect(self) -> bool:
        """Simulate database disconnection."""
        await self._simulate_delay(factor=0.1)
        
        if self.active_connections > 0:
            self.active_connections -= 1
        
        logger.debug(f"Database disconnected (active: {self.active_connections})")
        return True
    
    async def execute_query(self, query: str, params: List[Any] = None) -> Dict[str, Any]:
        """Execute a SQL query with realistic simulation."""
        start_time = time.time()
        self._query_count += 1
        
        try:
            await self._simulate_delay()
            
            if self._should_fail():
                self._error_count += 1
                raise Exception(f"Query failed: {self._generate_db_error()}")
            
            # Parse basic query type
            query_type = self._parse_query_type(query)
            
            # Simulate query execution
            if query_type == "SELECT":
                result = await self._mock_select(query, params or [])
            elif query_type == "INSERT":
                result = await self._mock_insert(query, params or [])
            elif query_type == "UPDATE":
                result = await self._mock_update(query, params or [])
            elif query_type == "DELETE":
                result = await self._mock_delete(query, params or [])
            else:
                result = {"affected_rows": 0, "message": f"Unknown query type: {query_type}"}
            
            # Add execution metadata
            execution_time = time.time() - start_time
            self._total_response_time += execution_time
            
            result.update({
                "execution_time_ms": execution_time * 1000,
                "query_type": query_type,
                "connection_id": f"conn_{self.active_connections}"
            })
            
            logger.debug(f"Query executed: {query_type} in {execution_time*1000:.2f}ms")
            return result
            
        except Exception as e:
            execution_time = time.time() - start_time
            self._total_response_time += execution_time
            logger.error(f"Query failed: {e}")
            raise
    
    async def begin_transaction(self) -> str:
        """Begin database transaction."""
        await self._simulate_delay(factor=0.2)
        
        if self._should_fail(rate=0.01):  # Lower failure rate for transactions
            raise Exception("Failed to begin transaction")
        
        transaction_id = f"txn_{random.randint(100000, 999999)}"
        logger.debug(f"Transaction started: {transaction_id}")
        return transaction_id
    
    async def commit_transaction(self, transaction_id: str) -> bool:
        """Commit database transaction."""
        await self._simulate_delay(factor=0.3)
        
        if self._should_fail(rate=0.005):  # Very low failure rate for commits
            raise Exception(f"Transaction commit failed: {transaction_id}")
        
        logger.debug(f"Transaction committed: {transaction_id}")
        return True
    
    async def rollback_transaction(self, transaction_id: str) -> bool:
        """Rollback database transaction."""
        await self._simulate_delay(factor=0.2)
        
        logger.debug(f"Transaction rolled back: {transaction_id}")
        return True
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get database performance metrics."""
        avg_response_time = (self._total_response_time / self._query_count) if self._query_count > 0 else 0
        
        return {
            "db_type": self.db_type,
            "total_queries": self._query_count,
            "total_errors": self._error_count,
            "error_rate": (self._error_count / self._query_count) if self._query_count > 0 else 0,
            "avg_response_time_ms": avg_response_time * 1000,
            "active_connections": self.active_connections,
            "connection_pool_size": self.connection_pool_size,
            "pool_utilization": (self.active_connections / self.connection_pool_size) * 100
        }
    
    def set_failure_rate(self, rate: float) -> None:
        """Set the failure rate for operations."""
        self.failure_rate = max(0.0, min(1.0, rate))
        logger.info(f"Database failure rate set to {self.failure_rate:.1%}")
    
    def set_response_delay(self, min_delay: float, max_delay: float) -> None:
        """Set response delay range."""
        self.response_delay = (min_delay, max_delay)
        logger.info(f"Database response delay set to {min_delay}-{max_delay}s")
    
    def add_table_data(self, table_name: str, data: List[Dict[str, Any]]) -> None:
        """Add mock data to a table."""
        if table_name not in self._tables:
            self._tables[table_name] = []
        
        self._tables[table_name].extend(data)
        logger.info(f"Added {len(data)} records to table {table_name}")
    
    def clear_table(self, table_name: str) -> None:
        """Clear all data from a table."""
        if table_name in self._tables:
            del self._tables[table_name]
        logger.info(f"Cleared table {table_name}")
    
    def clear_all_tables(self) -> None:
        """Clear all mock data."""
        self._tables.clear()
        self._sequences.clear()
        self._indexes.clear()
        logger.info("Cleared all mock database data")
    
    # Private methods
    
    async def _simulate_delay(self, factor: float = 1.0) -> None:
        """Simulate realistic database response delay."""
        min_delay, max_delay = self.response_delay
        delay = random.uniform(min_delay, max_delay) * factor
        await asyncio.sleep(delay)
    
    def _should_fail(self, rate: float = None) -> bool:
        """Determine if operation should fail based on configured rate."""
        return random.random() < (rate or self.failure_rate)
    
    def _parse_query_type(self, query: str) -> str:
        """Extract query type from SQL."""
        query_upper = query.strip().upper()
        
        if query_upper.startswith('SELECT'):
            return 'SELECT'
        elif query_upper.startswith('INSERT'):
            return 'INSERT'
        elif query_upper.startswith('UPDATE'):
            return 'UPDATE'
        elif query_upper.startswith('DELETE'):
            return 'DELETE'
        elif query_upper.startswith('CREATE'):
            return 'CREATE'
        elif query_upper.startswith('DROP'):
            return 'DROP'
        elif query_upper.startswith('ALTER'):
            return 'ALTER'
        else:
            return 'OTHER'
    
    def _generate_db_error(self) -> str:
        """Generate realistic database error messages."""
        errors = [
            "Connection timeout",
            "Deadlock detected",
            "Constraint violation",
            "Table not found",
            "Column not found",
            "Invalid syntax",
            "Permission denied",
            "Disk full",
            "Lock timeout",
            "Connection lost"
        ]
        return random.choice(errors)
    
    async def _mock_select(self, query: str, params: List[Any]) -> Dict[str, Any]:
        """Mock SELECT query execution."""
        # Extract table name (simplified parsing)
        table_name = self._extract_table_name(query)
        
        if table_name and table_name in self._tables:
            rows = self._tables[table_name]
            
            # Simulate filtering (very basic)
            if "WHERE" in query.upper():
                # Random filtering simulation
                filtered_rows = random.sample(rows, min(len(rows), random.randint(0, len(rows))))
            else:
                filtered_rows = rows
            
            # Simulate LIMIT
            if "LIMIT" in query.upper():
                limit = random.randint(1, min(100, len(filtered_rows)))
                filtered_rows = filtered_rows[:limit]
            
            return {
                "rows": copy.deepcopy(filtered_rows),
                "row_count": len(filtered_rows),
                "columns": list(filtered_rows[0].keys()) if filtered_rows else []
            }
        else:
            # Return empty result for unknown tables
            return {
                "rows": [],
                "row_count": 0,
                "columns": []
            }
    
    async def _mock_insert(self, query: str, params: List[Any]) -> Dict[str, Any]:
        """Mock INSERT query execution."""
        table_name = self._extract_table_name(query)
        
        if table_name:
            # Generate mock inserted ID
            if table_name not in self._sequences:
                self._sequences[table_name] = 1000
            
            inserted_id = self._sequences[table_name]
            self._sequences[table_name] += 1
            
            # Simulate inserting data
            if table_name not in self._tables:
                self._tables[table_name] = []
            
            # Create mock record from params
            mock_record = {
                "id": inserted_id,
                "created_at": datetime.utcnow().isoformat(),
                **{f"field_{i}": param for i, param in enumerate(params)}
            }
            
            self._tables[table_name].append(mock_record)
            
            return {
                "inserted_id": inserted_id,
                "affected_rows": 1,
                "table": table_name
            }
        
        return {"affected_rows": 0}
    
    async def _mock_update(self, query: str, params: List[Any]) -> Dict[str, Any]:
        """Mock UPDATE query execution."""
        table_name = self._extract_table_name(query)
        
        if table_name and table_name in self._tables:
            # Simulate updating random number of rows
            total_rows = len(self._tables[table_name])
            affected_rows = random.randint(0, min(total_rows, 10))
            
            return {
                "affected_rows": affected_rows,
                "table": table_name
            }
        
        return {"affected_rows": 0}
    
    async def _mock_delete(self, query: str, params: List[Any]) -> Dict[str, Any]:
        """Mock DELETE query execution."""
        table_name = self._extract_table_name(query)
        
        if table_name and table_name in self._tables:
            # Simulate deleting random number of rows
            total_rows = len(self._tables[table_name])
            affected_rows = random.randint(0, min(total_rows, 5))
            
            # Actually remove some items for realism
            if affected_rows > 0:
                self._tables[table_name] = self._tables[table_name][:-affected_rows]
            
            return {
                "affected_rows": affected_rows,
                "table": table_name
            }
        
        return {"affected_rows": 0}
    
    def _extract_table_name(self, query: str) -> Optional[str]:
        """Extract table name from SQL query (simplified)."""
        query_upper = query.upper()
        
        # Very basic table name extraction
        if "FROM" in query_upper:
            from_index = query_upper.find("FROM")
            after_from = query[from_index + 4:].strip()
            table_name = after_from.split()[0].strip(";")
            return table_name.lower()
        
        if "INTO" in query_upper:
            into_index = query_upper.find("INTO")
            after_into = query[into_index + 4:].strip()
            table_name = after_into.split()[0].strip()
            return table_name.lower()
        
        if "UPDATE" in query_upper:
            update_index = query_upper.find("UPDATE")
            after_update = query[update_index + 6:].strip()
            table_name = after_update.split()[0].strip()
            return table_name.lower()
        
        return None


# Convenience functions for common operations
async def create_mock_database() -> DatabaseMock:
    """Create and initialize a mock database with sample data."""
    db = DatabaseMock()
    
    # Add sample data
    sample_users = [
        {"id": 1, "username": "john_doe", "email": "john@example.com", "status": "active"},
        {"id": 2, "username": "jane_smith", "email": "jane@example.com", "status": "active"},
        {"id": 3, "username": "bob_wilson", "email": "bob@example.com", "status": "inactive"}
    ]
    
    sample_groups = [
        {"id": 1, "name": "Administrators", "description": "System administrators"},
        {"id": 2, "name": "Users", "description": "Regular users"},
        {"id": 3, "name": "Engineering", "description": "Engineering team"}
    ]
    
    sample_computers = [
        {"id": 1, "hostname": "WS001", "ip_address": "192.168.1.10", "status": "online"},
        {"id": 2, "hostname": "WS002", "ip_address": "192.168.1.11", "status": "online"},
        {"id": 3, "hostname": "SRV001", "ip_address": "192.168.1.100", "status": "maintenance"}
    ]
    
    db.add_table_data("users", sample_users)
    db.add_table_data("groups", sample_groups)
    db.add_table_data("computers", sample_computers)
    
    logger.info("Mock database initialized with sample data")
    return db
