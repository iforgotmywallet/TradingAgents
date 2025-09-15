"""
Database connection utilities for Neon PostgreSQL.

This module provides connection factory, retry logic, and comprehensive
error handling for database operations with SSL requirements.
"""

import logging
import time
import random
from typing import Optional, Callable, Any, Dict
from contextlib import contextmanager
from functools import wraps
import psycopg2
from psycopg2 import OperationalError, DatabaseError, InterfaceError
from psycopg2.extras import RealDictCursor

from .neon_config import NeonConfig

logger = logging.getLogger(__name__)


class ConnectionError(Exception):
    """Custom exception for connection-related errors."""
    pass


class RetryableError(Exception):
    """Exception for errors that should trigger a retry."""
    pass


class ConnectionFactory:
    """Factory for creating and managing database connections with retry logic."""
    
    def __init__(self, config: NeonConfig):
        """Initialize connection factory with configuration."""
        self.config = config
        self.max_retries = 3
        self.base_delay = 1.0  # Base delay for exponential backoff
        self.max_delay = 30.0  # Maximum delay between retries
        
    def create_connection(self, use_pool: bool = True):
        """
        Create a database connection with SSL requirements.
        
        Args:
            use_pool: Whether to use connection pool or create direct connection
            
        Returns:
            Database connection object
            
        Raises:
            ConnectionError: If connection cannot be established after retries
        """
        if use_pool:
            return self._create_pooled_connection()
        else:
            return self._create_direct_connection()
    
    def _create_pooled_connection(self):
        """Create connection from pool with retry logic."""
        return self._retry_operation(
            operation=self.config.get_connection,
            operation_name="get_pooled_connection"
        )
    
    def _create_direct_connection(self):
        """Create direct connection with retry logic."""
        def _connect():
            connection_params = self.config.get_connection_params()
            return psycopg2.connect(**connection_params)
            
        return self._retry_operation(
            operation=_connect,
            operation_name="create_direct_connection"
        )
    
    def _retry_operation(self, operation: Callable, operation_name: str) -> Any:
        """
        Execute operation with exponential backoff retry logic.
        
        Args:
            operation: Function to execute
            operation_name: Name for logging purposes
            
        Returns:
            Result of the operation
            
        Raises:
            ConnectionError: If all retries are exhausted
        """
        last_exception = None
        
        for attempt in range(self.max_retries + 1):
            try:
                result = operation()
                if attempt > 0:
                    logger.info(f"{operation_name} succeeded on attempt {attempt + 1}")
                return result
                
            except (OperationalError, DatabaseError, InterfaceError) as e:
                last_exception = e
                
                if attempt == self.max_retries:
                    logger.error(f"{operation_name} failed after {self.max_retries + 1} attempts: {e}")
                    break
                
                # Calculate delay with exponential backoff and jitter
                delay = min(
                    self.base_delay * (2 ** attempt) + random.uniform(0, 1),
                    self.max_delay
                )
                
                logger.warning(
                    f"{operation_name} failed on attempt {attempt + 1}/{self.max_retries + 1}: {e}. "
                    f"Retrying in {delay:.2f} seconds..."
                )
                
                time.sleep(delay)
                
            except Exception as e:
                # Non-retryable errors
                logger.error(f"{operation_name} failed with non-retryable error: {e}")
                raise ConnectionError(f"Non-retryable error in {operation_name}: {e}")
        
        # All retries exhausted
        raise ConnectionError(f"Failed to {operation_name} after {self.max_retries + 1} attempts: {last_exception}")
    
    @contextmanager
    def get_connection(self, use_pool: bool = True):
        """
        Context manager for database connections with automatic cleanup.
        
        Args:
            use_pool: Whether to use connection pool
            
        Yields:
            Database connection
        """
        conn = None
        try:
            conn = self.create_connection(use_pool=use_pool)
            yield conn
        except Exception as e:
            if conn:
                try:
                    conn.rollback()
                except Exception as rollback_error:
                    logger.error(f"Error during rollback: {rollback_error}")
            raise
        finally:
            if conn:
                if use_pool:
                    self.config.return_connection(conn)
                else:
                    try:
                        conn.close()
                    except Exception as close_error:
                        logger.error(f"Error closing connection: {close_error}")
    
    @contextmanager
    def get_cursor(self, use_pool: bool = True, cursor_factory=RealDictCursor):
        """
        Context manager for database cursors with automatic cleanup.
        
        Args:
            use_pool: Whether to use connection pool
            cursor_factory: Cursor factory to use
            
        Yields:
            Database cursor
        """
        with self.get_connection(use_pool=use_pool) as conn:
            cursor = None
            try:
                cursor = conn.cursor(cursor_factory=cursor_factory)
                yield cursor
                conn.commit()
            except Exception as e:
                conn.rollback()
                logger.error(f"Database operation failed, rolled back: {e}")
                raise
            finally:
                if cursor:
                    try:
                        cursor.close()
                    except Exception as close_error:
                        logger.error(f"Error closing cursor: {close_error}")


def with_db_retry(max_retries: int = 3, base_delay: float = 1.0):
    """
    Decorator for database operations with retry logic.
    
    Args:
        max_retries: Maximum number of retry attempts
        base_delay: Base delay for exponential backoff
        
    Returns:
        Decorated function with retry logic
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None
            
            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                    
                except (OperationalError, DatabaseError, InterfaceError) as e:
                    last_exception = e
                    
                    if attempt == max_retries:
                        logger.error(f"{func.__name__} failed after {max_retries + 1} attempts: {e}")
                        break
                    
                    # Calculate delay with exponential backoff and jitter
                    delay = min(
                        base_delay * (2 ** attempt) + random.uniform(0, 1),
                        30.0  # Max delay
                    )
                    
                    logger.warning(
                        f"{func.__name__} failed on attempt {attempt + 1}/{max_retries + 1}: {e}. "
                        f"Retrying in {delay:.2f} seconds..."
                    )
                    
                    time.sleep(delay)
                    
                except Exception as e:
                    # Non-retryable errors
                    logger.error(f"{func.__name__} failed with non-retryable error: {e}")
                    raise
            
            # All retries exhausted
            raise ConnectionError(f"Failed to execute {func.__name__} after {max_retries + 1} attempts: {last_exception}")
        
        return wrapper
    return decorator


class DatabaseHealthChecker:
    """Utility class for comprehensive database health monitoring."""
    
    def __init__(self, connection_factory: ConnectionFactory):
        """Initialize health checker with connection factory."""
        self.connection_factory = connection_factory
    
    def check_connectivity(self) -> Dict[str, Any]:
        """Check basic database connectivity."""
        start_time = time.time()
        
        try:
            with self.connection_factory.get_cursor() as cursor:
                cursor.execute("SELECT 1 as test")
                result = cursor.fetchone()
                
                response_time = round((time.time() - start_time) * 1000, 2)
                
                return {
                    'status': 'healthy',
                    'response_time_ms': response_time,
                    'test_query_result': result['test'] if result else None
                }
                
        except Exception as e:
            return {
                'status': 'unhealthy',
                'error': str(e),
                'response_time_ms': round((time.time() - start_time) * 1000, 2)
            }
    
    def check_ssl_connection(self) -> Dict[str, Any]:
        """Verify SSL connection is properly established."""
        try:
            with self.connection_factory.get_cursor() as cursor:
                cursor.execute("SHOW ssl")
                ssl_status = cursor.fetchone()
                
                cursor.execute("SELECT pg_is_in_recovery()")
                is_replica = cursor.fetchone()
                
                return {
                    'ssl_enabled': ssl_status['ssl'] == 'on' if ssl_status else False,
                    'is_replica': is_replica[0] if is_replica else False,
                    'status': 'healthy'
                }
                
        except Exception as e:
            return {
                'status': 'unhealthy',
                'error': str(e)
            }
    
    def check_database_stats(self) -> Dict[str, Any]:
        """Get database performance statistics."""
        try:
            with self.connection_factory.get_cursor() as cursor:
                # Get connection stats
                cursor.execute("""
                    SELECT 
                        count(*) as total_connections,
                        count(*) FILTER (WHERE state = 'active') as active_connections,
                        count(*) FILTER (WHERE state = 'idle') as idle_connections
                    FROM pg_stat_activity 
                    WHERE datname = current_database()
                """)
                connection_stats = cursor.fetchone()
                
                # Get database size
                cursor.execute("""
                    SELECT pg_size_pretty(pg_database_size(current_database())) as database_size
                """)
                size_info = cursor.fetchone()
                
                return {
                    'status': 'healthy',
                    'connection_stats': dict(connection_stats) if connection_stats else {},
                    'database_size': size_info['database_size'] if size_info else 'unknown'
                }
                
        except Exception as e:
            return {
                'status': 'unhealthy',
                'error': str(e)
            }
    
    def comprehensive_health_check(self) -> Dict[str, Any]:
        """Perform comprehensive health check."""
        health_report = {
            'overall_status': 'healthy',
            'timestamp': time.time(),
            'checks': {}
        }
        
        # Run all health checks
        checks = [
            ('connectivity', self.check_connectivity),
            ('ssl_connection', self.check_ssl_connection),
            ('database_stats', self.check_database_stats)
        ]
        
        for check_name, check_func in checks:
            try:
                result = check_func()
                health_report['checks'][check_name] = result
                
                if result.get('status') != 'healthy':
                    health_report['overall_status'] = 'unhealthy'
                    
            except Exception as e:
                health_report['checks'][check_name] = {
                    'status': 'error',
                    'error': str(e)
                }
                health_report['overall_status'] = 'unhealthy'
        
        return health_report


# Utility functions for common database operations
def execute_query_with_retry(connection_factory: ConnectionFactory, 
                           query: str, 
                           params: Optional[tuple] = None,
                           fetch_one: bool = False,
                           fetch_all: bool = True) -> Any:
    """
    Execute a query with automatic retry logic.
    
    Args:
        connection_factory: Connection factory instance
        query: SQL query to execute
        params: Query parameters
        fetch_one: Whether to fetch only one result
        fetch_all: Whether to fetch all results
        
    Returns:
        Query results or None
    """
    @with_db_retry()
    def _execute():
        with connection_factory.get_cursor() as cursor:
            cursor.execute(query, params)
            
            if fetch_one:
                return cursor.fetchone()
            elif fetch_all:
                return cursor.fetchall()
            else:
                return cursor.rowcount
    
    return _execute()