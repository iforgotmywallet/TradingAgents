"""
Unit tests for ReportStorageService save and retrieve methods.

Tests cover session creation, agent report saving, final decision storage,
error handling, and validation scenarios.
"""

import unittest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

from tradingagents.storage.report_storage import (
    ReportStorageService,
    ReportStorageError
)
from tradingagents.storage.agent_validation import AgentValidationError
from tradingagents.storage.neon_config import NeonConfig


class TestReportStorageService(unittest.TestCase):
    """Test cases for ReportStorageService class."""
    
    def setUp(self):
        """Set up test environment."""
        # Mock the NeonConfig to avoid database connections
        self.mock_config = Mock(spec=NeonConfig)
        self.mock_connection_factory = Mock()
        self.mock_validator = Mock()
        self.mock_content_handler = Mock()
        
        # Create service with mocked dependencies
        with patch('tradingagents.storage.report_storage.ConnectionFactory') as mock_cf, \
             patch('tradingagents.storage.report_storage.ReportContentValidator') as mock_validator, \
             patch('tradingagents.storage.report_storage.LargeContentHandler') as mock_handler:
            
            mock_cf.return_value = self.mock_connection_factory
            mock_validator.return_value = self.mock_validator
            mock_handler.return_value = self.mock_content_handler
            
            self.service = ReportStorageService(self.mock_config)
    
    def _setup_cursor_mock(self, return_value=None):
        """Helper method to set up cursor mock with context manager."""
        mock_cursor = Mock()
        if return_value is not None:
            mock_cursor.fetchone.return_value = return_value
        mock_context_manager = Mock()
        mock_context_manager.__enter__.return_value = mock_cursor
        mock_context_manager.__exit__.return_value = None
        self.mock_connection_factory.get_cursor.return_value = mock_context_manager
        return mock_cursor
    
    def test_init_with_config(self):
        """Test initialization with provided config."""
        with patch('tradingagents.storage.report_storage.ConnectionFactory') as mock_cf, \
             patch('tradingagents.storage.report_storage.ReportContentValidator') as mock_validator, \
             patch('tradingagents.storage.report_storage.LargeContentHandler') as mock_handler:
            
            service = ReportStorageService(self.mock_config)
            
            self.assertEqual(service.config, self.mock_config)
            mock_cf.assert_called_once_with(self.mock_config)
    
    def test_init_without_config(self):
        """Test initialization without provided config creates new one."""
        with patch('tradingagents.storage.report_storage.NeonConfig') as mock_config_class, \
             patch('tradingagents.storage.report_storage.ConnectionFactory') as mock_cf, \
             patch('tradingagents.storage.report_storage.ReportContentValidator') as mock_validator, \
             patch('tradingagents.storage.report_storage.LargeContentHandler') as mock_handler:
            
            mock_config_instance = Mock()
            mock_config_class.return_value = mock_config_instance
            
            service = ReportStorageService()
            
            mock_config_class.assert_called_once()
            self.assertEqual(service.config, mock_config_instance)
    
    @patch('tradingagents.storage.report_storage.generate_session_id')
    def test_create_session_sync_success(self, mock_generate_id):
        """Test successful synchronous session creation."""
        mock_generate_id.return_value = "AAPL_2025-09-13_1694612345"
        
        # Mock cursor and database interaction
        mock_cursor = self._setup_cursor_mock({'id': 'uuid-123', 'session_id': 'AAPL_2025-09-13_1694612345'})
        
        result = self.service.create_session_sync("AAPL", "2025-09-13")
        
        self.assertEqual(result, "AAPL_2025-09-13_1694612345")
        mock_generate_id.assert_called_once_with("AAPL", "2025-09-13")
        mock_cursor.execute.assert_called_once()
    
    @patch('tradingagents.storage.report_storage.generate_session_id')
    def test_create_session_sync_existing_session(self, mock_generate_id):
        """Test session creation when session already exists."""
        mock_generate_id.return_value = "AAPL_2025-09-13_1694612345"
        
        # Mock cursor returning None (session already exists)
        mock_cursor = self._setup_cursor_mock(None)
        
        result = self.service.create_session_sync("AAPL", "2025-09-13")
        
        self.assertEqual(result, "AAPL_2025-09-13_1694612345")
    
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
    
    def test_create_session_sync_database_error(self):
        """Test session creation handles database errors."""
        self.mock_connection_factory.get_cursor.side_effect = Exception("Database error")
        
        with self.assertRaises(ReportStorageError) as context:
            self.service.create_session_sync("AAPL", "2025-09-13")
        
        self.assertIn("Session creation failed", str(context.exception))
    
    @patch('tradingagents.storage.report_storage.validate_session_id')
    @patch('tradingagents.storage.report_storage.validate_agent_report')
    def test_save_agent_report_sync_success(self, mock_validate_report, mock_validate_session):
        """Test successful agent report saving."""
        mock_validate_session.return_value = True
        mock_validate_report.return_value = ('market_analyst_report', 'sanitized content')
        
        # Mock cursor and database interaction
        mock_cursor = Mock()
        mock_cursor.fetchone.return_value = {'id': 'uuid-123'}
        self.mock_connection_factory.get_cursor.return_value.__enter__.return_value = mock_cursor
        
        result = self.service.save_agent_report_sync(
            "AAPL_2025-09-13_1694612345",
            "Market Analyst",
            "Test report content"
        )
        
        self.assertTrue(result)
        mock_validate_session.assert_called_once_with("AAPL_2025-09-13_1694612345")
        mock_validate_report.assert_called_once_with("Market Analyst", "Test report content")
        mock_cursor.execute.assert_called_once()
    
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
    @patch('tradingagents.storage.report_storage.validate_agent_report')
    def test_save_agent_report_sync_large_content(self, mock_validate_report, mock_validate_session):
        """Test agent report saving with large content compression."""
        mock_validate_session.return_value = True
        large_content = "x" * (1024 * 1024 + 1)  # > 1MB
        mock_validate_report.return_value = ('market_analyst_report', large_content)
        self.mock_content_handler.compress_content.return_value = "compressed content"
        
        # Mock cursor and database interaction
        mock_cursor = Mock()
        mock_cursor.fetchone.return_value = {'id': 'uuid-123'}
        self.mock_connection_factory.get_cursor.return_value.__enter__.return_value = mock_cursor
        
        result = self.service.save_agent_report_sync(
            "AAPL_2025-09-13_1694612345",
            "Market Analyst",
            large_content
        )
        
        self.assertTrue(result)
        self.mock_content_handler.compress_content.assert_called_once_with(large_content)
    
    @patch('tradingagents.storage.report_storage.validate_session_id')
    @patch('tradingagents.storage.report_storage.validate_agent_report')
    def test_save_agent_report_sync_session_not_found(self, mock_validate_report, mock_validate_session):
        """Test agent report saving fails when session not found."""
        mock_validate_session.return_value = True
        mock_validate_report.return_value = ('market_analyst_report', 'sanitized content')
        
        # Mock cursor returning None (session not found)
        mock_cursor = Mock()
        mock_cursor.fetchone.return_value = None
        self.mock_connection_factory.get_cursor.return_value.__enter__.return_value = mock_cursor
        
        with self.assertRaises(ReportStorageError) as context:
            self.service.save_agent_report_sync(
                "AAPL_2025-09-13_1694612345",
                "Market Analyst",
                "Test report content"
            )
        
        self.assertIn("Session AAPL_2025-09-13_1694612345 not found", str(context.exception))
    
    @patch('tradingagents.storage.report_storage.validate_session_id')
    def test_save_final_decision_sync_success(self, mock_validate_session):
        """Test successful final decision saving."""
        mock_validate_session.return_value = True
        self.mock_validator.validate_report_content.side_effect = lambda x, y: f"sanitized {x}"
        self.mock_validator.validate_recommendation.return_value = "BUY"
        
        # Mock cursor and database interaction
        mock_cursor = Mock()
        mock_cursor.fetchone.return_value = {'id': 'uuid-123'}
        self.mock_connection_factory.get_cursor.return_value.__enter__.return_value = mock_cursor
        
        result = self.service.save_final_decision_sync(
            "AAPL_2025-09-13_1694612345",
            "Final decision content",
            "Final analysis content",
            "BUY"
        )
        
        self.assertTrue(result)
        mock_validate_session.assert_called_once_with("AAPL_2025-09-13_1694612345")
        self.assertEqual(self.mock_validator.validate_report_content.call_count, 2)
        self.mock_validator.validate_recommendation.assert_called_once_with("BUY")
    
    @patch('tradingagents.storage.report_storage.validate_session_id')
    def test_save_final_decision_sync_invalid_session(self, mock_validate_session):
        """Test final decision saving fails with invalid session ID."""
        mock_validate_session.return_value = False
        
        with self.assertRaises(AgentValidationError) as context:
            self.service.save_final_decision_sync(
                "invalid_session",
                "Final decision",
                "Final analysis",
                "BUY"
            )
        
        self.assertIn("Invalid session ID format", str(context.exception))
    
    @patch('tradingagents.storage.report_storage.validate_session_id')
    def test_update_session_timestamp_success(self, mock_validate_session):
        """Test successful session timestamp update."""
        mock_validate_session.return_value = True
        
        # Mock cursor and database interaction
        mock_cursor = Mock()
        mock_cursor.fetchone.return_value = {'id': 'uuid-123'}
        self.mock_connection_factory.get_cursor.return_value.__enter__.return_value = mock_cursor
        
        result = self.service.update_session_timestamp("AAPL_2025-09-13_1694612345")
        
        self.assertTrue(result)
        mock_validate_session.assert_called_once_with("AAPL_2025-09-13_1694612345")
        mock_cursor.execute.assert_called_once()
    
    @patch('tradingagents.storage.report_storage.validate_session_id')
    def test_update_session_timestamp_invalid_session(self, mock_validate_session):
        """Test timestamp update fails with invalid session ID."""
        mock_validate_session.return_value = False
        
        with self.assertRaises(AgentValidationError) as context:
            self.service.update_session_timestamp("invalid_session")
        
        self.assertIn("Invalid session ID format", str(context.exception))
    
    @patch('tradingagents.storage.report_storage.validate_session_id')
    def test_session_exists_true(self, mock_validate_session):
        """Test session existence check returns True."""
        mock_validate_session.return_value = True
        
        # Mock cursor and database interaction
        mock_cursor = Mock()
        mock_cursor.fetchone.return_value = [1]
        self.mock_connection_factory.get_cursor.return_value.__enter__.return_value = mock_cursor
        
        result = self.service.session_exists("AAPL_2025-09-13_1694612345")
        
        self.assertTrue(result)
    
    @patch('tradingagents.storage.report_storage.validate_session_id')
    def test_session_exists_false(self, mock_validate_session):
        """Test session existence check returns False."""
        mock_validate_session.return_value = True
        
        # Mock cursor and database interaction
        mock_cursor = Mock()
        mock_cursor.fetchone.return_value = None
        self.mock_connection_factory.get_cursor.return_value.__enter__.return_value = mock_cursor
        
        result = self.service.session_exists("AAPL_2025-09-13_1694612345")
        
        self.assertFalse(result)
    
    def test_session_exists_invalid_session_id(self):
        """Test session existence check with invalid session ID."""
        result = self.service.session_exists("invalid_session")
        
        self.assertFalse(result)
    
    @patch('tradingagents.storage.report_storage.validate_session_id')
    def test_get_session_info_success(self, mock_validate_session):
        """Test successful session info retrieval."""
        mock_validate_session.return_value = True
        
        # Mock cursor and database interaction
        mock_cursor = Mock()
        mock_result = {
            'session_id': 'AAPL_2025-09-13_1694612345',
            'ticker': 'AAPL',
            'analysis_date': '2025-09-13',
            'created_at': datetime.now(),
            'updated_at': datetime.now()
        }
        mock_cursor.fetchone.return_value = mock_result
        self.mock_connection_factory.get_cursor.return_value.__enter__.return_value = mock_cursor
        
        result = self.service.get_session_info("AAPL_2025-09-13_1694612345")
        
        self.assertEqual(result, mock_result)
    
    @patch('tradingagents.storage.report_storage.validate_session_id')
    def test_get_session_info_not_found(self, mock_validate_session):
        """Test session info retrieval when session not found."""
        mock_validate_session.return_value = True
        
        # Mock cursor and database interaction
        mock_cursor = Mock()
        mock_cursor.fetchone.return_value = None
        self.mock_connection_factory.get_cursor.return_value.__enter__.return_value = mock_cursor
        
        result = self.service.get_session_info("AAPL_2025-09-13_1694612345")
        
        self.assertIsNone(result)
    
    def test_cleanup_old_sessions_success(self):
        """Test successful cleanup of old sessions."""
        # Mock cursor and database interaction
        mock_cursor = Mock()
        mock_cursor.fetchall.return_value = [
            {'session_id': 'OLD1_2025-08-01_1234567890'},
            {'session_id': 'OLD2_2025-08-02_1234567891'}
        ]
        self.mock_connection_factory.get_cursor.return_value.__enter__.return_value = mock_cursor
        
        result = self.service.cleanup_old_sessions(30)
        
        self.assertEqual(result, 2)
        mock_cursor.execute.assert_called_once()
    
    def test_cleanup_old_sessions_none_found(self):
        """Test cleanup when no old sessions found."""
        # Mock cursor and database interaction
        mock_cursor = Mock()
        mock_cursor.fetchall.return_value = []
        self.mock_connection_factory.get_cursor.return_value.__enter__.return_value = mock_cursor
        
        result = self.service.cleanup_old_sessions(30)
        
        self.assertEqual(result, 0)
    
    def test_cleanup_old_sessions_database_error(self):
        """Test cleanup handles database errors gracefully."""
        self.mock_connection_factory.get_cursor.side_effect = Exception("Database error")
        
        result = self.service.cleanup_old_sessions(30)
        
        self.assertEqual(result, 0)


if __name__ == '__main__':
    unittest.main()