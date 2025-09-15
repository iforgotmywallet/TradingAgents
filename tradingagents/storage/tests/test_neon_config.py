"""
Unit tests for NeonConfig class and connection management.

Tests cover configuration validation, connection pooling, health checks,
and error handling scenarios.
"""

import os
import pytest
import unittest
from unittest.mock import Mock, patch, MagicMock
from psycopg2 import OperationalError, DatabaseError
from psycopg2.pool import ThreadedConnectionPool

from tradingagents.storage.neon_config import NeonConfig


class TestNeonConfig(unittest.TestCase):
    """Test cases for NeonConfig class."""
    
    def setUp(self):
        """Set up test environment."""
        # Store original environment variables
        self.original_env = {
            'NEON_DATABASE_URL': os.getenv('NEON_DATABASE_URL'),
            'DB_POOL_SIZE': os.getenv('DB_POOL_SIZE'),
            'DB_SSL_MODE': os.getenv('DB_SSL_MODE')
        }
        
        # Set test environment variables
        os.environ['NEON_DATABASE_URL'] = 'postgresql://testuser:testpass@testhost:5432/testdb'
        os.environ['DB_POOL_SIZE'] = '5'
        os.environ['DB_SSL_MODE'] = 'require'
    
    def tearDown(self):
        """Clean up test environment."""
        # Restore original environment variables
        for key, value in self.original_env.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value
    
    def test_init_with_valid_config(self):
        """Test initialization with valid configuration."""
        config = NeonConfig()
        
        self.assertEqual(config.connection_string, 'postgresql://testuser:testpass@testhost:5432/testdb')
        self.assertEqual(config.pool_size, 5)
        self.assertEqual(config.ssl_mode, 'require')
        self.assertIsNone(config.connection_pool)
    
    def test_init_missing_database_url(self):
        """Test initialization fails with missing database URL."""
        os.environ.pop('NEON_DATABASE_URL', None)
        
        with self.assertRaises(ValueError) as context:
            NeonConfig()
        
        self.assertIn("NEON_DATABASE_URL environment variable is required", str(context.exception))
    
    def test_init_invalid_database_url(self):
        """Test initialization fails with invalid database URL."""
        os.environ['NEON_DATABASE_URL'] = 'invalid-url'
        
        with self.assertRaises(ValueError) as context:
            NeonConfig()
        
        self.assertIn("Invalid NEON_DATABASE_URL", str(context.exception))
    
    def test_init_invalid_pool_size(self):
        """Test initialization fails with invalid pool size."""
        os.environ['DB_POOL_SIZE'] = '0'
        
        with self.assertRaises(ValueError) as context:
            NeonConfig()
        
        self.assertIn("DB_POOL_SIZE must be between 1 and 50", str(context.exception))
        
        os.environ['DB_POOL_SIZE'] = '100'
        
        with self.assertRaises(ValueError) as context:
            NeonConfig()
        
        self.assertIn("DB_POOL_SIZE must be between 1 and 50", str(context.exception))
    
    def test_get_connection_params(self):
        """Test connection parameters extraction."""
        config = NeonConfig()
        params = config.get_connection_params()
        
        expected_params = {
            'host': 'testhost',
            'port': 5432,
            'database': 'testdb',
            'user': 'testuser',
            'password': 'testpass',
            'sslmode': 'require',
            'connect_timeout': 30
        }
        
        for key, value in expected_params.items():
            self.assertEqual(params[key], value)
    
    def test_get_connection_params_with_channel_binding(self):
        """Test connection parameters with channel binding."""
        os.environ['NEON_DATABASE_URL'] = 'postgresql://testuser:testpass@testhost:5432/testdb?channel_binding=require'
        config = NeonConfig()
        params = config.get_connection_params()
        
        self.assertEqual(params['channel_binding'], 'require')
    
    @patch('tradingagents.storage.neon_config.pool.ThreadedConnectionPool')
    def test_create_connection_pool_success(self, mock_pool_class):
        """Test successful connection pool creation."""
        mock_pool = Mock()
        mock_pool_class.return_value = mock_pool
        
        config = NeonConfig()
        result = config.create_connection_pool()
        
        self.assertEqual(result, mock_pool)
        self.assertEqual(config.connection_pool, mock_pool)
        mock_pool_class.assert_called_once()
    
    @patch('tradingagents.storage.neon_config.pool.ThreadedConnectionPool')
    def test_create_connection_pool_failure(self, mock_pool_class):
        """Test connection pool creation failure."""
        mock_pool_class.side_effect = OperationalError("Connection failed")
        
        config = NeonConfig()
        
        with self.assertRaises(OperationalError):
            config.create_connection_pool()
    
    def test_get_connection_no_pool(self):
        """Test getting connection when pool doesn't exist."""
        config = NeonConfig()
        config.connection_pool = None  # Ensure pool is None
        
        with patch.object(config, 'create_connection_pool') as mock_create:
            mock_pool = Mock()
            mock_connection = Mock()
            mock_pool.getconn.return_value = mock_connection
            mock_create.return_value = mock_pool
            
            result = config.get_connection()
            
            mock_create.assert_called_once()
            self.assertEqual(result, mock_connection)
    
    def test_get_connection_pool_returns_none(self):
        """Test getting connection when pool returns None."""
        config = NeonConfig()
        mock_pool = Mock()
        mock_pool.getconn.return_value = None
        config.connection_pool = mock_pool
        
        with self.assertRaises(OperationalError) as context:
            config.get_connection()
        
        self.assertIn("Failed to get connection from pool", str(context.exception))
    
    def test_return_connection_success(self):
        """Test successful connection return."""
        config = NeonConfig()
        mock_pool = Mock()
        mock_connection = Mock()
        config.connection_pool = mock_pool
        
        config.return_connection(mock_connection)
        
        mock_pool.putconn.assert_called_once_with(mock_connection)
    
    def test_return_connection_no_pool(self):
        """Test returning connection when no pool exists."""
        config = NeonConfig()
        mock_connection = Mock()
        
        # Should not raise exception
        config.return_connection(mock_connection)
    
    def test_close_connection_pool_success(self):
        """Test successful connection pool closure."""
        config = NeonConfig()
        mock_pool = Mock()
        config.connection_pool = mock_pool
        
        config.close_connection_pool()
        
        mock_pool.closeall.assert_called_once()
        self.assertIsNone(config.connection_pool)
    
    def test_close_connection_pool_no_pool(self):
        """Test closing connection pool when none exists."""
        config = NeonConfig()
        
        # Should not raise exception
        config.close_connection_pool()
    
    @patch.object(NeonConfig, 'get_connection')
    @patch.object(NeonConfig, 'return_connection')
    def test_validate_connection_success(self, mock_return, mock_get):
        """Test successful connection validation."""
        config = NeonConfig()
        mock_connection = Mock()
        mock_cursor = Mock()
        mock_cursor.fetchone.return_value = [1]
        mock_connection.cursor.return_value = mock_cursor
        mock_get.return_value = mock_connection
        
        result = config.validate_connection()
        
        self.assertTrue(result)
        mock_get.assert_called_once()
        mock_return.assert_called_once_with(mock_connection)
        mock_cursor.execute.assert_called_once_with("SELECT 1")
    
    @patch.object(NeonConfig, 'get_connection')
    def test_validate_connection_failure(self, mock_get):
        """Test connection validation failure."""
        config = NeonConfig()
        mock_get.side_effect = OperationalError("Connection failed")
        
        result = config.validate_connection()
        
        self.assertFalse(result)
    
    @patch.object(NeonConfig, 'validate_connection')
    def test_health_check_healthy(self, mock_validate):
        """Test health check when connection is healthy."""
        config = NeonConfig()
        mock_validate.return_value = True
        
        result = config.health_check()
        
        self.assertTrue(result['healthy'])
        self.assertIsNone(result['error'])
        self.assertIsNotNone(result['response_time_ms'])
        self.assertEqual(result['pool_size'], 5)
        self.assertEqual(result['ssl_mode'], 'require')
    
    @patch.object(NeonConfig, 'validate_connection')
    def test_health_check_unhealthy(self, mock_validate):
        """Test health check when connection is unhealthy."""
        config = NeonConfig()
        mock_validate.return_value = False
        
        result = config.health_check()
        
        self.assertFalse(result['healthy'])
        self.assertEqual(result['error'], "Connection validation failed")
    
    @patch.object(NeonConfig, 'get_connection')
    @patch.object(NeonConfig, 'return_connection')
    def test_get_database_info_success(self, mock_return, mock_get):
        """Test successful database info retrieval."""
        config = NeonConfig()
        mock_connection = Mock()
        mock_cursor = Mock()
        
        # Mock cursor responses
        mock_cursor.fetchone.side_effect = [
            ["PostgreSQL 15.0"],  # version
            ["testdb"],           # database name
            [5]                   # active connections
        ]
        
        mock_connection.cursor.return_value = mock_cursor
        mock_get.return_value = mock_connection
        
        result = config.get_database_info()
        
        self.assertEqual(result['version'], "PostgreSQL 15.0")
        self.assertEqual(result['database_name'], "testdb")
        self.assertEqual(result['active_connections'], 5)
        self.assertEqual(result['pool_size'], 5)
        self.assertEqual(result['ssl_mode'], 'require')
    
    @patch.object(NeonConfig, 'get_connection')
    def test_get_database_info_failure(self, mock_get):
        """Test database info retrieval failure."""
        config = NeonConfig()
        mock_get.side_effect = OperationalError("Connection failed")
        
        result = config.get_database_info()
        
        self.assertIn('error', result)
        self.assertIn("Connection failed", result['error'])


if __name__ == '__main__':
    unittest.main()