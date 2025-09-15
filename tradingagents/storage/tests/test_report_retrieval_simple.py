"""
Simplified unit tests for ReportRetrievalService.

Tests core functionality with proper mocking.
"""

import unittest
from unittest.mock import Mock, patch
from datetime import datetime

from tradingagents.storage.report_retrieval import (
    ReportRetrievalService,
    ReportRetrievalError,
    ReportNotFoundError,
    SessionNotFoundError,
    ErrorResponseFormatter
)
from tradingagents.storage.agent_validation import AgentValidationError
from tradingagents.storage.neon_config import NeonConfig


class TestReportRetrievalServiceSimple(unittest.TestCase):
    """Simplified test cases for ReportRetrievalService class."""
    
    def setUp(self):
        """Set up test environment."""
        self.mock_config = Mock(spec=NeonConfig)
        self.mock_config.connection_pool = Mock()
        self.service = ReportRetrievalService(self.mock_config)
    
    def test_init_with_config(self):
        """Test initialization with provided config."""
        service = ReportRetrievalService(self.mock_config)
        self.assertEqual(service.config, self.mock_config)
    
    def test_init_without_config(self):
        """Test initialization without provided config creates new one."""
        with patch('tradingagents.storage.report_retrieval.NeonConfig') as mock_config_class:
            mock_config_instance = Mock()
            mock_config_instance.connection_pool = Mock()
            mock_config_class.return_value = mock_config_instance
            
            service = ReportRetrievalService()
            
            mock_config_class.assert_called_once()
            self.assertEqual(service.config, mock_config_instance)
    
    @patch('tradingagents.storage.report_retrieval.validate_session_id')
    def test_session_exists_true(self, mock_validate):
        """Test session existence check returns True."""
        mock_validate.return_value = True
        
        # Mock database connection and cursor
        mock_connection = Mock()
        mock_cursor = Mock()
        mock_cursor.fetchone.return_value = [1]
        mock_connection.cursor.return_value = mock_cursor
        self.mock_config.get_connection.return_value = mock_connection
        
        result = self.service.session_exists("AAPL_2025-09-13_1694612345")
        
        self.assertTrue(result)
        mock_validate.assert_called_once_with("AAPL_2025-09-13_1694612345")
    
    @patch('tradingagents.storage.report_retrieval.validate_session_id')
    def test_session_exists_false(self, mock_validate):
        """Test session existence check returns False."""
        mock_validate.return_value = True
        
        # Mock database connection and cursor
        mock_connection = Mock()
        mock_cursor = Mock()
        mock_cursor.fetchone.return_value = None
        mock_connection.cursor.return_value = mock_cursor
        self.mock_config.get_connection.return_value = mock_connection
        
        result = self.service.session_exists("AAPL_2025-09-13_1694612345")
        
        self.assertFalse(result)
    
    @patch('tradingagents.storage.report_retrieval.validate_session_id')
    def test_session_exists_invalid_session_id(self, mock_validate):
        """Test session existence check with invalid session ID."""
        mock_validate.return_value = False
        
        result = self.service.session_exists("invalid_session")
        
        self.assertFalse(result)
    
    @patch('tradingagents.storage.report_retrieval.validate_session_id')
    @patch('tradingagents.storage.report_retrieval.AgentReportSchema')
    def test_get_agent_report_success(self, mock_schema, mock_validate):
        """Test successful agent report retrieval."""
        mock_validate.return_value = True
        mock_schema.is_valid_agent_type.return_value = True
        mock_schema.get_agent_column.return_value = 'market_analyst_report'
        
        # Mock database connection and cursor
        mock_connection = Mock()
        mock_cursor = Mock()
        # First call checks session exists, second call gets report
        mock_cursor.fetchone.side_effect = [
            [1],  # Session exists
            {'market_analyst_report': 'Test report content'}  # Report content
        ]
        mock_connection.cursor.return_value = mock_cursor
        self.mock_config.get_connection.return_value = mock_connection
        
        result = self.service.get_agent_report("AAPL_2025-09-13_1694612345", "Market Analyst")
        
        self.assertEqual(result, "Test report content")
        mock_validate.assert_called_once_with("AAPL_2025-09-13_1694612345")
        mock_schema.is_valid_agent_type.assert_called_once_with("Market Analyst")
        mock_schema.get_agent_column.assert_called_once_with("Market Analyst")
    
    @patch('tradingagents.storage.report_retrieval.validate_session_id')
    def test_get_agent_report_invalid_session_id(self, mock_validate):
        """Test agent report retrieval with invalid session ID."""
        mock_validate.return_value = False
        
        with self.assertRaises(ReportRetrievalError) as context:
            self.service.get_agent_report("invalid_session", "Market Analyst")
        
        self.assertIn("Invalid session ID format", str(context.exception))
    
    @patch('tradingagents.storage.report_retrieval.validate_session_id')
    @patch('tradingagents.storage.report_retrieval.AgentReportSchema')
    def test_get_agent_report_invalid_agent_type(self, mock_schema, mock_validate):
        """Test agent report retrieval with invalid agent type."""
        mock_validate.return_value = True
        mock_schema.is_valid_agent_type.return_value = False
        
        with self.assertRaises(AgentValidationError) as context:
            self.service.get_agent_report("AAPL_2025-09-13_1694612345", "Invalid Agent")
        
        self.assertIn("Invalid agent type", str(context.exception))
    
    def test_get_agent_report_safe_success(self):
        """Test safe agent report retrieval with success response."""
        with patch.object(self.service, 'get_agent_report') as mock_get:
            mock_get.return_value = "Test report content"
            
            result = self.service.get_agent_report_safe("AAPL_2025-09-13_1694612345", "Market Analyst")
            
            self.assertTrue(result['success'])
            self.assertEqual(result['data']['content'], "Test report content")
            self.assertEqual(result['data']['agent_type'], "Market Analyst")
    
    def test_get_agent_report_safe_not_found(self):
        """Test safe agent report retrieval with not found response."""
        with patch.object(self.service, 'get_agent_report') as mock_get:
            mock_get.return_value = None
            
            result = self.service.get_agent_report_safe("AAPL_2025-09-13_1694612345", "Market Analyst")
            
            self.assertFalse(result['success'])
            self.assertEqual(result['error']['type'], 'NotFoundError')
            self.assertIn('Report not found', result['error']['message'])
    
    def test_health_check_healthy(self):
        """Test health check when service is healthy."""
        self.mock_config.health_check.return_value = {'healthy': True}
        
        # Mock database connection and cursor
        mock_connection = Mock()
        mock_cursor = Mock()
        mock_cursor.fetchone.return_value = [5]
        mock_connection.cursor.return_value = mock_cursor
        self.mock_config.get_connection.return_value = mock_connection
        
        result = self.service.health_check()
        
        self.assertTrue(result['healthy'])
        self.assertTrue(result['database_connection'])
        self.assertIsNone(result['error'])
    
    def test_health_check_unhealthy(self):
        """Test health check when service is unhealthy."""
        self.mock_config.health_check.return_value = {'healthy': False, 'error': 'Connection failed'}
        
        result = self.service.health_check()
        
        self.assertFalse(result['healthy'])
        self.assertFalse(result['database_connection'])
        self.assertEqual(result['error'], 'Connection failed')


class TestErrorResponseFormatterSimple(unittest.TestCase):
    """Simplified test cases for ErrorResponseFormatter class."""
    
    def test_format_error_response(self):
        """Test error response formatting."""
        error = ValueError("Test error message")
        context = {'session_id': 'test_session'}
        
        result = ErrorResponseFormatter.format_error_response(error, context)
        
        self.assertFalse(result['success'])
        self.assertEqual(result['error']['type'], 'ValueError')
        self.assertEqual(result['error']['message'], 'Test error message')
        self.assertEqual(result['error']['context'], context)
        self.assertIsNone(result['data'])
    
    def test_format_success_response(self):
        """Test success response formatting."""
        data = {'key': 'value'}
        message = "Operation successful"
        
        result = ErrorResponseFormatter.format_success_response(data, message)
        
        self.assertTrue(result['success'])
        self.assertEqual(result['message'], message)
        self.assertEqual(result['data'], data)
        self.assertIsNotNone(result['timestamp'])
    
    def test_format_not_found_response(self):
        """Test not found response formatting."""
        resource_type = "report"
        identifier = "test_id"
        details = {'reason': 'Not available'}
        
        result = ErrorResponseFormatter.format_not_found_response(resource_type, identifier, details)
        
        self.assertFalse(result['success'])
        self.assertEqual(result['error']['type'], 'NotFoundError')
        self.assertEqual(result['error']['code'], 'REPORT_NOT_FOUND')
        self.assertIn('Report not found: test_id', result['error']['message'])
        self.assertEqual(result['error']['details'], details)


if __name__ == '__main__':
    unittest.main()