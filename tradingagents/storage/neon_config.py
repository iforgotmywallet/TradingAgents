"""
Neon PostgreSQL database configuration and connection management.

This module provides configuration management for connecting to Neon PostgreSQL
database with proper SSL settings, connection pooling, and health checks.
"""

import os
import logging
import time
from typing import Optional, Dict, Any
from urllib.parse import urlparse
import psycopg2
from psycopg2 import pool, OperationalError, DatabaseError
from psycopg2.extras import RealDictCursor

logger = logging.getLogger(__name__)


class NeonConfig:
    """Configuration and connection management for Neon PostgreSQL database."""
    
    def __init__(self):
        """Initialize Neon configuration from environment variables."""
        self.connection_string = os.getenv('NEON_DATABASE_URL')
        self.pool_size = int(os.getenv('DB_POOL_SIZE', '10'))
        self.ssl_mode = os.getenv('DB_SSL_MODE', 'require')
        self.connection_pool: Optional[pool.ThreadedConnectionPool] = None
        
        # Validate configuration on initialization
        self._validate_config()
        
    def _validate_config(self) -> None:
        """Validate the database configuration."""
        if not self.connection_string:
            raise ValueError("NEON_DATABASE_URL environment variable is required")
            
        # Parse and validate connection string
        try:
            parsed = urlparse(self.connection_string)
            if not all([parsed.scheme, parsed.hostname, parsed.username, parsed.password]):
                raise ValueError("Invalid database connection string format")
                
            if parsed.scheme != 'postgresql':
                raise ValueError("Connection string must use postgresql:// scheme")
                
        except Exception as e:
            raise ValueError(f"Invalid NEON_DATABASE_URL: {e}")
            
        if self.pool_size < 1 or self.pool_size > 50:
            raise ValueError("DB_POOL_SIZE must be between 1 and 50")
            
        logger.info(f"Neon config validated - Pool size: {self.pool_size}, SSL: {self.ssl_mode}")
    
    def get_connection_params(self) -> Dict[str, Any]:
        """Get connection parameters dictionary from connection string."""
        parsed = urlparse(self.connection_string)
        
        params = {
            'host': parsed.hostname,
            'port': parsed.port or 5432,
            'database': parsed.path.lstrip('/') or 'neondb',
            'user': parsed.username,
            'password': parsed.password,
            'sslmode': self.ssl_mode,
            'cursor_factory': RealDictCursor,
            'connect_timeout': 30,
        }
        
        # Add SSL channel binding if specified in connection string
        if 'channel_binding=require' in self.connection_string:
            params['channel_binding'] = 'require'
            
        return params
    
    def create_connection_pool(self) -> pool.ThreadedConnectionPool:
        """Create and return a threaded connection pool."""
        if self.connection_pool is not None:
            return self.connection_pool
            
        try:
            connection_params = self.get_connection_params()
            
            self.connection_pool = pool.ThreadedConnectionPool(
                minconn=1,
                maxconn=self.pool_size,
                **connection_params
            )
            
            logger.info(f"Created connection pool with {self.pool_size} max connections")
            return self.connection_pool
            
        except Exception as e:
            logger.error(f"Failed to create connection pool: {e}")
            raise
    
    def get_connection(self):
        """Get a connection from the pool."""
        if self.connection_pool is None:
            self.create_connection_pool()
            
        try:
            conn = self.connection_pool.getconn()
            if conn is None:
                raise OperationalError("Failed to get connection from pool")
            return conn
        except Exception as e:
            logger.error(f"Failed to get connection: {e}")
            raise
    
    def return_connection(self, conn) -> None:
        """Return a connection to the pool."""
        if self.connection_pool and conn:
            try:
                self.connection_pool.putconn(conn)
            except Exception as e:
                logger.error(f"Failed to return connection to pool: {e}")
    
    def close_connection_pool(self) -> None:
        """Close all connections in the pool."""
        if self.connection_pool:
            try:
                self.connection_pool.closeall()
                self.connection_pool = None
                logger.info("Connection pool closed")
            except Exception as e:
                logger.error(f"Error closing connection pool: {e}")
    
    def validate_connection(self) -> bool:
        """Test database connectivity and return True if successful."""
        try:
            conn = self.get_connection()
            try:
                with conn.cursor() as cursor:
                    cursor.execute("SELECT 1")
                    result = cursor.fetchone()
                    # Handle RealDictCursor result
                    if result:
                        if hasattr(result, '__getitem__'):
                            # RealDictCursor returns RealDictRow
                            test_value = result[0] if isinstance(result, (list, tuple)) else result.get('?column?', result.get(list(result.keys())[0]))
                        else:
                            test_value = result
                        
                        if test_value == 1:
                            logger.info("Database connection validated successfully")
                            return True
                    return False
            finally:
                self.return_connection(conn)
                
        except Exception as e:
            logger.error(f"Database connection validation failed: {e}")
            return False
    
    def health_check(self) -> Dict[str, Any]:
        """Perform comprehensive health check and return status information."""
        health_status = {
            'healthy': False,
            'connection_pool_created': self.connection_pool is not None,
            'pool_size': self.pool_size,
            'ssl_mode': self.ssl_mode,
            'error': None,
            'response_time_ms': None
        }
        
        start_time = time.time()
        
        try:
            # Test basic connectivity
            if self.validate_connection():
                health_status['healthy'] = True
                health_status['response_time_ms'] = round((time.time() - start_time) * 1000, 2)
            else:
                health_status['error'] = "Connection validation failed"
                
        except Exception as e:
            health_status['error'] = str(e)
            
        return health_status
    
    def get_database_info(self) -> Dict[str, Any]:
        """Get database information for monitoring and debugging."""
        try:
            conn = self.get_connection()
            try:
                with conn.cursor() as cursor:
                    # Get PostgreSQL version
                    cursor.execute("SELECT version()")
                    version = cursor.fetchone()[0]
                    
                    # Get current database name
                    cursor.execute("SELECT current_database()")
                    database_name = cursor.fetchone()[0]
                    
                    # Get connection count
                    cursor.execute("""
                        SELECT count(*) 
                        FROM pg_stat_activity 
                        WHERE datname = current_database()
                    """)
                    active_connections = cursor.fetchone()[0]
                    
                    return {
                        'version': version,
                        'database_name': database_name,
                        'active_connections': active_connections,
                        'pool_size': self.pool_size,
                        'ssl_mode': self.ssl_mode
                    }
                    
            finally:
                self.return_connection(conn)
                
        except Exception as e:
            logger.error(f"Failed to get database info: {e}")
            return {'error': str(e)}