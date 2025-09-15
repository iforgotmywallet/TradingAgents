"""
Simplified unit tests for ReportStorageService.

Tests core functionality with proper mocking.
"""

import unittest
from unittest.mock import Mock, patch
from datetime import datetime

from tradingagents.storage.report_storage import (
    ReportStorageService,
    ReportStorageError
)
from tradingagents.storage.agent_validation import AgentValidationError
from tradingagents.storage.neon_config import NeonConfig


class TestReportStorageServiceSimple(unittest.TestCase):
    """Simplified test cases for ReportStorageService class."""
    
    def setUp(self):
        """Set up test environment."""
        self.mock_config = Mock(spec=NeonConfig)
        
        # Mock all dependencies
        with patch('tradingagents.storage.report_storage.ConnectionFactory'), \
             patch('tradingagents.storage.report_storage.ReportContentValidator'), \
             patch('tradingagents.storage.report_storage.LargeContentHandler'):
            self.service = ReportStorageService(self.mock_config)
    
    def test_init_with_config(self):
        """Test initialization with provided config."""
        with patch('tradingagents.storage.report_storage.ConnectionFactory'), \
             patch('tradingagents.storage.report_storage.ReportContentValidator'), \
             patch('tradingagents.storage.report_storage.LargeContentHandler'):
            service = ReportStorageService(self.mock_config)
            self.assertEqual(service.config, self.mock_config)
    
    def test_init_without_config(self):
        """Test initialization without provided config creates new one."""
        with patch('tradingagents.storage.report_storage.NeonConfig') as mock_config_class, \
             patch('tradingagents.storage.report_storage.ConnectionFactory'), \
             patch('tradingagents.storage.report_storage.ReportContentValidator'), \
             patch('tradingagents.storage.report_storage.LargeContentHandler'):
            
            mock_config_instance = Mock()
            mock_config_class.return_value = mock_config_instance
            
            service = ReportStorageService()
            
            mock_config_class.assert_called_once()
            self.assertEqual(service.config, mock_config_instance)
    
    @patch('tradingagents.storage.report_storage.generate_session_id')
    def test_create_session_sync_success(self, mock_generate_id):
        """Test successful synchronous session creation."""
        mock_generate_id.return_value = "AAPL_2025-09-13_1694612345"
        
        # Mock the connection factory and cursor
        mock_cursor = Mock()
        mock_cursor.fetchone.return_value = {'id': 'uuid-123', 'session_id': 'AAPL_2025-09-13_1694612345'}
        
        # Mock context manager
        mock_context = Mock()
        mock_context.__enter__.return_value = mock_cursor
        mock_context.__exit__.return_value = None
        
        self.service.connection_factory.get_cursor.return_value = mock_context
        
        result = self.service.create_session_sync("AAPL", "2025-09-13")
        
        self.assertEqual(result, "AAPL_2025-09-13_1694612345")
        mock_generate_id.assert_called_once_with("AAPL", "2025-09-13")
    
    def test_create_session_sync_invalid_ticker(self):
        """Test session creation fails with invalid ticker."""
        with self.assertRaises(ReportStorageError) as context:
            self.service.create_session_sync("", "2025-09-13")
        
        self.assertIn("Ticker must be a non-empty string", str(context.exception))
    
    def test_create_session_sync_invalid_date(self):
        """Test session creation fails with invalid date."""
        with self.assertRaises(ReportStorageError) as context:
            self.service.create_session_sync("AAPL", "")
        
        self.assertIn("Analysis date must be a non-empty string", str(context.exception))
    
    @patch('tradingagents.storage.report_storage.validate_session_id')
    @patch('tradingagents.storage.report_storage.validate_agent_report')
    def test_save_agent_report_sync_success(self, mock_validate_report, mock_validate_session):
        """Test successful agent report saving."""
        mock_validate_session.return_value = True
        mock_validate_report.return_value = ('market_analyst_report', 'sanitized content')
        
        # Mock the connection factory and cursor
        mock_cursor = Mock()
        mock_cursor.fetchone.return_value = {'id': 'uuid-123'}
        
        # Mock context manager
        mock_context = Mock()
        mock_context.__enter__.return_value = mock_cursor
        mock_context.__exit__.return_value = None
        
        self.service.connection_factory.get_cursor.return_value = mock_context
        
        result = self.service.save_agent_report_sync(
            "AAPL_2025-09-13_1694612345",
            "Market Analyst",
            "Test report content"
        )
        
        self.assertTrue(result)
        mock_validate_session.assert_called_once_with("AAPL_2025-09-13_1694612345")
        mock_validate_report.assert_called_once_with("Market Analyst", "Test report content")
    
    @patch('tradingagents.storage.report_storage.validate_session_id')
    def test_save_agent_report_sync_invalid_session(self, mock_validate_session):
        """Test agent report saving fails with invalid session ID."""
        mock_validate_session.return_value = False
        
        with self.assertRaises(AgentValidationError) as context:
            self.service.save_agent_report_sync(
                "invalid_session",
                "Market Analyst",
                "Test report content"
            )
        
        self.assertIn("Invalid session ID format", str(context.exception))
    
    @patch('tradingagents.storage.report_storage.validate_session_id')
    def test_session_exists_true(self, mock_validate_session):
        """Test session existence check returns True."""
        mock_validate_session.return_value = True
        
        # Mock the connection factory and cursor
        mock_cursor = Mock()
        mock_cursor.fetchone.return_value = [1]
        
        # Mock context manager
        mock_context = Mock()
        mock_context.__enter__.return_value = mock_cursor
        mock_context.__exit__.return_value = None
        
        self.service.connection_factory.get_cursor.return_value = mock_context
        
        result = self.service.session_exists("AAPL_2025-09-13_1694612345")
        
        self.assertTrue(result)
    
    @patch('tradingagents.storage.report_storage.validate_session_id')
    def test_session_exists_false(self, mock_validate_session):
        """Test session existence check returns False."""
        mock_validate_session.return_value = True
        
        # Mock the connection factory and cursor
        mock_cursor = Mock()
        mock_cursor.fetchone.return_value = None
        
        # Mock context manager
        mock_context = Mock()
        mock_context.__enter__.return_value = mock_cursor
        mock_context.__exit__.return_value = None
        
        self.service.connection_factory.get_cursor.return_value = mock_context
        
        result = self.service.session_exists("AAPL_2025-09-13_1694612345")
        
        self.assertFalse(result)
    
    def test_session_exists_invalid_session_id(self):
        """Test session existence check with invalid session ID."""
        result = self.service.session_exists("invalid_session")
        
        self.assertFalse(result)


if __name__ == '__main__':
    unittest.main()