"""
Unit tests for ReportRetrievalService with various scenarios.

Tests cover individual report retrieval, session data retrieval, final decision retrieval,
error handling, and API-friendly response formatting.
"""

import unittest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime
from psycopg2 import OperationalError, DatabaseError

from tradingagents.storage.report_retrieval import (
    ReportRetrievalService,
    ReportRetrievalError,
    ReportNotFoundError,
    SessionNotFoundError,
    DatabaseConnectionError,
    ErrorResponseFormatter
)
from tradingagents.storage.agent_validation import AgentValidationError
from tradingagents.storage.neon_config import NeonConfig


class TestReportRetrievalService(unittest.TestCase):
    """Test cases for ReportRetrievalService class."""
    
    def setUp(self):
        """Set up test environment."""
        # Mock the NeonConfig to avoid database connections
        self.mock_config = Mock(spec=NeonConfig)
        self.mock_config.connection_pool = Mock()
        
        # Create service with mocked config
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
        mock_connection.cursor.return_value.__enter__.return_value = mock_cursor
        self.mock_config.get_connection.return_value = mock_connection
        
        result = self.service.session_exists("AAPL_2025-09-13_1694612345")
        
        self.assertTrue(result)
        mock_validate.assert_called_once_with("AAPL_2025-09-13_1694612345")
        mock_cursor.execute.assert_called_once()
    
    @patch('tradingagents.storage.report_retrieval.validate_session_id')
    def test_session_exists_false(self, mock_validate):
        """Test session existence check returns False."""
        mock_validate.return_value = True
        
        # Mock database connection and cursor
        mock_connection = Mock()
        mock_cursor = Mock()
        mock_cursor.fetchone.return_value = None
        mock_connection.cursor.return_value.__enter__.return_value = mock_cursor
        self.mock_config.get_connection.return_value = mock_connection
        
        result = self.service.session_exists("AAPL_2025-09-13_1694612345")
        
        self.assertFalse(result)
    
    @patch('tradingagents.storage.report_retrieval.validate_session_id')
    def test_session_exists_invalid_session_id(self, mock_validate):
        """Test session existence check with invalid session ID."""
        mock_validate.return_value = False
        
        result = self.service.session_exists("invalid_session")
        
        self.assertFalse(result)
    
    def test_session_exists_database_error(self):
        """Test session existence check handles database errors."""
        self.mock_config.get_connection.side_effect = OperationalError("Connection failed")
        
        with self.assertRaises(ReportRetrievalError):
            self.service.session_exists("AAPL_2025-09-13_1694612345")
    
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
        mock_connection.cursor.return_value.__enter__.return_value = mock_cursor
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
    
    @patch('tradingagents.storage.report_retrieval.validate_session_id')
    @patch('tradingagents.storage.report_retrieval.AgentReportSchema')
    def test_get_agent_report_session_not_found(self, mock_schema, mock_validate):
        """Test agent report retrieval when session doesn't exist."""
        mock_validate.return_value = True
        mock_schema.is_valid_agent_type.return_value = True
        mock_schema.get_agent_column.return_value = 'market_analyst_report'
        
        # Mock database connection and cursor
        mock_connection = Mock()
        mock_cursor = Mock()
        mock_cursor.fetchone.return_value = None  # Session doesn't exist
        mock_connection.cursor.return_value.__enter__.return_value = mock_cursor
        self.mock_config.get_connection.return_value = mock_connection
        
        with self.assertRaises(SessionNotFoundError) as context:
            self.service.get_agent_report("AAPL_2025-09-13_1694612345", "Market Analyst")
        
        self.assertIn("Session not found", str(context.exception))
    
    @patch('tradingagents.storage.report_retrieval.validate_session_id')
    @patch('tradingagents.storage.report_retrieval.AgentReportSchema')
    def test_get_agent_report_not_available(self, mock_schema, mock_validate):
        """Test agent report retrieval when report is not available."""
        mock_validate.return_value = True
        mock_schema.is_valid_agent_type.return_value = True
        mock_schema.get_agent_column.return_value = 'market_analyst_report'
        
        # Mock database connection and cursor
        mock_connection = Mock()
        mock_cursor = Mock()
        # First call checks session exists, second call gets empty report
        mock_cursor.fetchone.side_effect = [
            [1],  # Session exists
            {'market_analyst_report': None}  # No report content
        ]
        mock_connection.cursor.return_value.__enter__.return_value = mock_cursor
        self.mock_config.get_connection.return_value = mock_connection
        
        result = self.service.get_agent_report("AAPL_2025-09-13_1694612345", "Market Analyst")
        
        self.assertIsNone(result)
    
    @patch('tradingagents.storage.report_retrieval.validate_session_id')
    @patch('tradingagents.storage.report_retrieval.AGENT_TYPE_MAPPING')
    def test_get_session_reports_success(self, mock_mapping, mock_validate):
        """Test successful complete session data retrieval."""
        mock_validate.return_value = True
        mock_mapping = {
            'Market Analyst': 'market_analyst_report',
            'News Analyst': 'news_analyst_report'
        }
        
        # Mock database connection and cursor
        mock_connection = Mock()
        mock_cursor = Mock()
        mock_result = {
            'session_id': 'AAPL_2025-09-13_1694612345',
            'ticker': 'AAPL',
            'analysis_date': datetime(2025, 9, 13).date(),
            'created_at': datetime(2025, 9, 13, 10, 0, 0),
            'updated_at': datetime(2025, 9, 13, 11, 0, 0),
            'market_analyst_report': 'Market analysis content',
            'news_analyst_report': 'News analysis content',
            'final_decision': 'Final decision content',
            'final_analysis': 'Final analysis content',
            'recommendation': 'BUY'
        }
        mock_cursor.fetchone.return_value = mock_result
        mock_connection.cursor.return_value.__enter__.return_value = mock_cursor
        self.mock_config.get_connection.return_value = mock_connection
        
        with patch('tradingagents.storage.report_retrieval.AGENT_TYPE_MAPPING', mock_mapping):
            result = self.service.get_session_reports("AAPL_2025-09-13_1694612345")
        
        self.assertEqual(result['session_id'], 'AAPL_2025-09-13_1694612345')
        self.assertEqual(result['ticker'], 'AAPL')
        self.assertIn('Market Analyst', result['agent_reports'])
        self.assertIn('News Analyst', result['agent_reports'])
        self.assertEqual(result['final_decision'], 'Final decision content')
        self.assertEqual(result['recommendation'], 'BUY')
    
    @patch('tradingagents.storage.report_retrieval.validate_session_id')
    def test_get_session_reports_not_found(self, mock_validate):
        """Test session reports retrieval when session doesn't exist."""
        mock_validate.return_value = True
        
        # Mock database connection and cursor
        mock_connection = Mock()
        mock_cursor = Mock()
        mock_cursor.fetchone.return_value = None
        mock_connection.cursor.return_value.__enter__.return_value = mock_cursor
        self.mock_config.get_connection.return_value = mock_connection
        
        with self.assertRaises(SessionNotFoundError) as context:
            self.service.get_session_reports("AAPL_2025-09-13_1694612345")
        
        self.assertIn("Session not found", str(context.exception))
    
    @patch('tradingagents.storage.report_retrieval.validate_session_id')
    def test_get_final_decision_success(self, mock_validate):
        """Test successful final decision retrieval."""
        mock_validate.return_value = True
        
        # Mock database connection and cursor
        mock_connection = Mock()
        mock_cursor = Mock()
        mock_result = {
            'final_decision': 'Final decision content',
            'final_analysis': 'Final analysis content',
            'recommendation': 'BUY'
        }
        mock_cursor.fetchone.return_value = mock_result
        mock_connection.cursor.return_value.__enter__.return_value = mock_cursor
        self.mock_config.get_connection.return_value = mock_connection
        
        result = self.service.get_final_decision("AAPL_2025-09-13_1694612345")
        
        self.assertEqual(result['final_decision'], 'Final decision content')
        self.assertEqual(result['final_analysis'], 'Final analysis content')
        self.assertEqual(result['recommendation'], 'BUY')
    
    @patch('tradingagents.storage.report_retrieval.validate_session_id')
    def test_get_final_decision_not_available(self, mock_validate):
        """Test final decision retrieval when not available."""
        mock_validate.return_value = True
        
        # Mock database connection and cursor
        mock_connection = Mock()
        mock_cursor = Mock()
        mock_result = {
            'final_decision': None,
            'final_analysis': None,
            'recommendation': None
        }
        mock_cursor.fetchone.return_value = mock_result
        mock_connection.cursor.return_value.__enter__.return_value = mock_cursor
        self.mock_config.get_connection.return_value = mock_connection
        
        result = self.service.get_final_decision("AAPL_2025-09-13_1694612345")
        
        self.assertIsNone(result)
    
    @patch('tradingagents.storage.report_retrieval.validate_session_id')
    def test_get_final_decision_session_not_found(self, mock_validate):
        """Test final decision retrieval when session doesn't exist."""
        mock_validate.return_value = True
        
        # Mock database connection and cursor
        mock_connection = Mock()
        mock_cursor = Mock()
        mock_cursor.fetchone.return_value = None
        mock_connection.cursor.return_value.__enter__.return_value = mock_cursor
        self.mock_config.get_connection.return_value = mock_connection
        
        with self.assertRaises(SessionNotFoundError) as context:
            self.service.get_final_decision("AAPL_2025-09-13_1694612345")
        
        self.assertIn("Session not found", str(context.exception))
    
    def test_get_sessions_by_ticker_success(self):
        """Test successful sessions retrieval by ticker."""
        # Mock database connection and cursor
        mock_connection = Mock()
        mock_cursor = Mock()
        mock_results = [
            {
                'session_id': 'AAPL_2025-09-13_1694612345',
                'ticker': 'AAPL',
                'analysis_date': datetime(2025, 9, 13).date(),
                'created_at': datetime(2025, 9, 13, 10, 0, 0),
                'updated_at': datetime(2025, 9, 13, 11, 0, 0),
                'recommendation': 'BUY',
                'has_final_decision': True
            },
            {
                'session_id': 'AAPL_2025-09-12_1694526000',
                'ticker': 'AAPL',
                'analysis_date': datetime(2025, 9, 12).date(),
                'created_at': datetime(2025, 9, 12, 10, 0, 0),
                'updated_at': datetime(2025, 9, 12, 11, 0, 0),
                'recommendation': 'HOLD',
                'has_final_decision': False
            }
        ]
        mock_cursor.fetchall.return_value = mock_results
        mock_connection.cursor.return_value.__enter__.return_value = mock_cursor
        self.mock_config.get_connection.return_value = mock_connection
        
        result = self.service.get_sessions_by_ticker("AAPL", 10)
        
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]['ticker'], 'AAPL')
        self.assertEqual(result[0]['recommendation'], 'BUY')
        self.assertTrue(result[0]['has_final_decision'])
        self.assertFalse(result[1]['has_final_decision'])
    
    def test_get_sessions_by_ticker_invalid_ticker(self):
        """Test sessions retrieval with invalid ticker."""
        with self.assertRaises(ReportRetrievalError) as context:
            self.service.get_sessions_by_ticker("", 10)
        
        self.assertIn("Ticker must be a non-empty string", str(context.exception))
    
    @patch('tradingagents.storage.report_retrieval.validate_session_id')
    @patch('tradingagents.storage.report_retrieval.AGENT_TYPE_MAPPING')
    def test_get_available_reports_success(self, mock_mapping, mock_validate):
        """Test successful available reports retrieval."""
        mock_validate.return_value = True
        mock_mapping = {
            'Market Analyst': 'market_analyst_report',
            'News Analyst': 'news_analyst_report',
            'Bull Researcher': 'bull_researcher_report'
        }
        
        # Mock database connection and cursor
        mock_connection = Mock()
        mock_cursor = Mock()
        mock_result = {
            'market_analyst_report': 'Market analysis content',
            'news_analyst_report': None,  # Not available
            'bull_researcher_report': 'Bull research content'
        }
        mock_cursor.fetchone.return_value = mock_result
        mock_connection.cursor.return_value.__enter__.return_value = mock_cursor
        self.mock_config.get_connection.return_value = mock_connection
        
        with patch('tradingagents.storage.report_retrieval.AGENT_TYPE_MAPPING', mock_mapping):
            result = self.service.get_available_reports("AAPL_2025-09-13_1694612345")
        
        self.assertIn('Market Analyst', result)
        self.assertNotIn('News Analyst', result)
        self.assertIn('Bull Researcher', result)
        self.assertEqual(len(result), 2)
    
    def test_health_check_healthy(self):
        """Test health check when service is healthy."""
        self.mock_config.health_check.return_value = {'healthy': True}
        
        # Mock database connection and cursor
        mock_connection = Mock()
        mock_cursor = Mock()
        mock_cursor.fetchone.return_value = [5]
        mock_connection.cursor.return_value.__enter__.return_value = mock_cursor
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
    
    def test_get_agent_report_safe_session_not_found(self):
        """Test safe agent report retrieval with session not found error."""
        with patch.object(self.service, 'get_agent_report') as mock_get:
            mock_get.side_effect = SessionNotFoundError("Session not found", "AAPL_2025-09-13_1694612345")
            
            result = self.service.get_agent_report_safe("AAPL_2025-09-13_1694612345", "Market Analyst")
            
            self.assertFalse(result['success'])
            self.assertEqual(result['error']['type'], 'SessionNotFoundError')
    
    def test_get_session_reports_safe_success(self):
        """Test safe session reports retrieval with success response."""
        mock_session_data = {
            'session_id': 'AAPL_2025-09-13_1694612345',
            'agent_reports': {'Market Analyst': 'content', 'News Analyst': 'content'},
            'final_decision': 'Final decision'
        }
        
        with patch.object(self.service, 'get_session_reports') as mock_get:
            mock_get.return_value = mock_session_data
            
            result = self.service.get_session_reports_safe("AAPL_2025-09-13_1694612345")
            
            self.assertTrue(result['success'])
            self.assertEqual(result['data']['summary']['total_reports'], 2)
            self.assertTrue(result['data']['summary']['has_final_decision'])
            self.assertEqual(result['data']['summary']['completion_status'], 'complete')
    
    def test_get_final_decision_safe_success(self):
        """Test safe final decision retrieval with success response."""
        mock_final_decision = {
            'final_decision': 'Final decision content',
            'final_analysis': 'Final analysis content',
            'recommendation': 'BUY'
        }
        
        with patch.object(self.service, 'get_final_decision') as mock_get:
            mock_get.return_value = mock_final_decision
            
            result = self.service.get_final_decision_safe("AAPL_2025-09-13_1694612345")
            
            self.assertTrue(result['success'])
            self.assertEqual(result['data']['recommendation'], 'BUY')


class TestErrorResponseFormatter(unittest.TestCase):
    """Test cases for ErrorResponseFormatter class."""
    
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