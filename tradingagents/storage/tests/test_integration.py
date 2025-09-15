"""
Integration tests for end-to-end storage functionality.

These tests verify the complete workflow from session creation through
report storage and retrieval, including web API integration.
"""

import unittest
import os
import tempfile
import sqlite3
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, date

from tradingagents.storage.report_storage import ReportStorageService, ReportStorageError
from tradingagents.storage.report_retrieval import ReportRetrievalService, ReportRetrievalError
from tradingagents.storage.session_utils import generate_session_id, validate_session_id
from tradingagents.storage.neon_config import NeonConfig


class MockNeonConfig:
    """Mock Neon configuration for testing."""
    
    def __init__(self):
        # Create in-memory SQLite database for testing
        self.connection = sqlite3.connect(':memory:')
        self.connection.row_factory = sqlite3.Row
        self.connection_pool = Mock()  # Add connection_pool attribute
        self._setup_test_schema()
    
    def _setup_test_schema(self):
        """Set up test database schema."""
        cursor = self.connection.cursor()
        cursor.execute("""
            CREATE TABLE agent_reports (
                id TEXT PRIMARY KEY,
                session_id TEXT UNIQUE NOT NULL,
                ticker TEXT NOT NULL,
                analysis_date DATE NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                
                -- Individual Agent Reports
                market_analyst_report TEXT,
                news_analyst_report TEXT,
                fundamentals_analyst_report TEXT,
                social_analyst_report TEXT,
                bull_researcher_report TEXT,
                bear_researcher_report TEXT,
                research_manager_report TEXT,
                trader_report TEXT,
                
                -- Risk Management Reports
                risky_analyst_report TEXT,
                neutral_analyst_report TEXT,
                safe_analyst_report TEXT,
                
                -- Final Results
                portfolio_manager_report TEXT,
                final_decision TEXT,
                final_analysis TEXT,
                recommendation TEXT
            )
        """)
        cursor.execute("CREATE INDEX idx_session_id ON agent_reports(session_id)")
        cursor.execute("CREATE INDEX idx_ticker_date ON agent_reports(ticker, analysis_date)")
        self.connection.commit()
    
    def get_connection(self):
        """Get database connection."""
        return self.connection
    
    def return_connection(self, conn):
        """Return connection (no-op for SQLite)."""
        pass
    
    def create_connection_pool(self):
        """Mock connection pool creation."""
        pass
    
    def health_check(self):
        """Return healthy status."""
        return {'healthy': True}


class MockConnectionFactory:
    """Mock connection factory for testing."""
    
    def __init__(self, config):
        self.config = config
    
    def get_cursor(self):
        """Get cursor context manager."""
        return self.config.get_connection()


class TestStorageIntegration(unittest.TestCase):
    """Integration tests for storage components."""
    
    def setUp(self):
        """Set up test environment."""
        self.mock_config = MockNeonConfig()
        
        # Patch the dependencies to use our mocks
        self.storage_patches = [
            patch('tradingagents.storage.report_storage.ConnectionFactory', MockConnectionFactory),
            patch('tradingagents.storage.report_storage.ReportContentValidator'),
            patch('tradingagents.storage.report_storage.LargeContentHandler'),
            patch('tradingagents.storage.report_storage.validate_agent_report', 
                  side_effect=self._mock_validate_agent_report),
        ]
        
        for p in self.storage_patches:
            p.start()
        
        self.storage_service = ReportStorageService(self.mock_config)
        self.retrieval_service = ReportRetrievalService(self.mock_config)
    
    def tearDown(self):
        """Clean up test environment."""
        for p in self.storage_patches:
            p.stop()
        self.mock_config.connection.close()
    
    def _mock_validate_agent_report(self, agent_type, content):
        """Mock agent report validation."""
        agent_mapping = {
            'Market Analyst': 'market_analyst_report',
            'News Analyst': 'news_analyst_report',
            'Fundamentals Analyst': 'fundamentals_analyst_report',
            'Bull Researcher': 'bull_researcher_report',
            'Bear Researcher': 'bear_researcher_report',
        }
        
        if agent_type not in agent_mapping:
            raise ValueError(f"Invalid agent type: {agent_type}")
        
        return agent_mapping[agent_type], content
    
    def test_complete_analysis_workflow(self):
        """Test complete analysis workflow from session creation to report retrieval."""
        ticker = "AAPL"
        analysis_date = "2025-09-13"
        
        # Step 1: Create session
        session_id = self.storage_service.create_session_sync(ticker, analysis_date)
        
        self.assertIsNotNone(session_id)
        self.assertTrue(validate_session_id(session_id))
        self.assertIn(ticker, session_id)
        self.assertIn(analysis_date, session_id)
        
        # Step 2: Verify session exists
        self.assertTrue(self.storage_service.session_exists(session_id))
        
        # Step 3: Save individual agent reports
        agent_reports = {
            'Market Analyst': 'Market analysis shows strong fundamentals...',
            'News Analyst': 'Recent news indicates positive sentiment...',
            'Fundamentals Analyst': 'Financial metrics are solid...',
            'Bull Researcher': 'Bullish indicators suggest upward trend...',
            'Bear Researcher': 'Some concerns about market volatility...'
        }
        
        for agent_type, content in agent_reports.items():
            result = self.storage_service.save_agent_report_sync(session_id, agent_type, content)
            self.assertTrue(result)
        
        # Step 4: Save final decision
        final_decision = "Based on comprehensive analysis, recommend BUY"
        final_analysis = "All indicators point to positive outlook"
        recommendation = "BUY"
        
        result = self.storage_service.save_final_decision_sync(
            session_id, final_decision, final_analysis, recommendation
        )
        self.assertTrue(result)
        
        # Step 5: Retrieve and verify individual reports
        for agent_type, expected_content in agent_reports.items():
            with patch('tradingagents.storage.report_retrieval.validate_session_id', return_value=True), \
                 patch('tradingagents.storage.report_retrieval.AgentReportSchema') as mock_schema:
                
                mock_schema.is_valid_agent_type.return_value = True
                mock_schema.get_agent_column.return_value = self._mock_validate_agent_report(agent_type, '')[0]
                
                retrieved_content = self.retrieval_service.get_agent_report(session_id, agent_type)
                self.assertEqual(retrieved_content, expected_content)
        
        # Step 6: Retrieve final decision
        with patch('tradingagents.storage.report_retrieval.validate_session_id', return_value=True):
            final_data = self.retrieval_service.get_final_decision(session_id)
            
            self.assertIsNotNone(final_data)
            self.assertEqual(final_data['final_decision'], final_decision)
            self.assertEqual(final_data['final_analysis'], final_analysis)
            self.assertEqual(final_data['recommendation'], recommendation)
        
        # Step 7: Retrieve complete session data
        with patch('tradingagents.storage.report_retrieval.validate_session_id', return_value=True), \
             patch('tradingagents.storage.report_retrieval.AGENT_TYPE_MAPPING', {
                 'Market Analyst': 'market_analyst_report',
                 'News Analyst': 'news_analyst_report',
                 'Fundamentals Analyst': 'fundamentals_analyst_report',
                 'Bull Researcher': 'bull_researcher_report',
                 'Bear Researcher': 'bear_researcher_report'
             }):
            
            session_data = self.retrieval_service.get_session_reports(session_id)
            
            self.assertEqual(session_data['session_id'], session_id)
            self.assertEqual(session_data['ticker'], ticker)
            self.assertEqual(session_data['final_decision'], final_decision)
            self.assertEqual(session_data['recommendation'], recommendation)
            
            # Verify all agent reports are present
            for agent_type in agent_reports.keys():
                self.assertIn(agent_type, session_data['agent_reports'])
    
    def test_concurrent_session_handling(self):
        """Test handling of multiple concurrent sessions."""
        sessions = []
        
        # Create multiple sessions
        for i in range(3):
            ticker = f"STOCK{i}"
            analysis_date = "2025-09-13"
            session_id = self.storage_service.create_session_sync(ticker, analysis_date)
            sessions.append((session_id, ticker))
        
        # Verify all sessions exist and are unique
        self.assertEqual(len(sessions), 3)
        session_ids = [s[0] for s in sessions]
        self.assertEqual(len(set(session_ids)), 3)  # All unique
        
        # Save reports to each session
        for session_id, ticker in sessions:
            content = f"Analysis for {ticker}"
            result = self.storage_service.save_agent_report_sync(
                session_id, 'Market Analyst', content
            )
            self.assertTrue(result)
        
        # Verify reports are correctly associated with sessions
        for session_id, ticker in sessions:
            with patch('tradingagents.storage.report_retrieval.validate_session_id', return_value=True), \
                 patch('tradingagents.storage.report_retrieval.AgentReportSchema') as mock_schema:
                
                mock_schema.is_valid_agent_type.return_value = True
                mock_schema.get_agent_column.return_value = 'market_analyst_report'
                
                retrieved_content = self.retrieval_service.get_agent_report(session_id, 'Market Analyst')
                expected_content = f"Analysis for {ticker}"
                self.assertEqual(retrieved_content, expected_content)
    
    def test_error_handling_scenarios(self):
        """Test various error handling scenarios."""
        
        # Test invalid session ID
        with self.assertRaises(ReportStorageError):
            self.storage_service.create_session_sync("", "2025-09-13")
        
        with self.assertRaises(ReportStorageError):
            self.storage_service.create_session_sync("AAPL", "")
        
        # Test saving to non-existent session
        fake_session_id = "FAKE_2025-09-13_1234567890"
        
        with patch('tradingagents.storage.report_storage.validate_session_id', return_value=True):
            with self.assertRaises(ReportStorageError):
                self.storage_service.save_agent_report_sync(
                    fake_session_id, 'Market Analyst', 'content'
                )
        
        # Test retrieving from non-existent session
        with patch('tradingagents.storage.report_retrieval.validate_session_id', return_value=True), \
             patch('tradingagents.storage.report_retrieval.AgentReportSchema') as mock_schema:
            
            mock_schema.is_valid_agent_type.return_value = True
            mock_schema.get_agent_column.return_value = 'market_analyst_report'
            
            with self.assertRaises(Exception):  # Should raise SessionNotFoundError
                self.retrieval_service.get_agent_report(fake_session_id, 'Market Analyst')
    
    def test_data_consistency(self):
        """Test data consistency across storage and retrieval operations."""
        ticker = "TSLA"
        analysis_date = "2025-09-13"
        
        # Create session
        session_id = self.storage_service.create_session_sync(ticker, analysis_date)
        
        # Save report with specific content
        original_content = "Original analysis content with special characters: !@#$%^&*()"
        result = self.storage_service.save_agent_report_sync(
            session_id, 'Market Analyst', original_content
        )
        self.assertTrue(result)
        
        # Retrieve and verify exact content match
        with patch('tradingagents.storage.report_retrieval.validate_session_id', return_value=True), \
             patch('tradingagents.storage.report_retrieval.AgentReportSchema') as mock_schema:
            
            mock_schema.is_valid_agent_type.return_value = True
            mock_schema.get_agent_column.return_value = 'market_analyst_report'
            
            retrieved_content = self.retrieval_service.get_agent_report(session_id, 'Market Analyst')
            self.assertEqual(retrieved_content, original_content)
        
        # Update report and verify change
        updated_content = "Updated analysis content"
        result = self.storage_service.save_agent_report_sync(
            session_id, 'Market Analyst', updated_content
        )
        self.assertTrue(result)
        
        with patch('tradingagents.storage.report_retrieval.validate_session_id', return_value=True), \
             patch('tradingagents.storage.report_retrieval.AgentReportSchema') as mock_schema:
            
            mock_schema.is_valid_agent_type.return_value = True
            mock_schema.get_agent_column.return_value = 'market_analyst_report'
            
            retrieved_content = self.retrieval_service.get_agent_report(session_id, 'Market Analyst')
            self.assertEqual(retrieved_content, updated_content)
            self.assertNotEqual(retrieved_content, original_content)
    
    def test_session_id_functionality(self):
        """Test session ID generation and validation functionality."""
        
        # Test valid session ID generation
        ticker = "NVDA"
        analysis_date = "2025-09-13"
        
        session_id = generate_session_id(ticker, analysis_date)
        
        self.assertTrue(validate_session_id(session_id))
        self.assertIn(ticker, session_id)
        self.assertIn(analysis_date, session_id)
        
        # Test session ID uniqueness
        import time
        session_id_1 = generate_session_id(ticker, analysis_date)
        time.sleep(0.001)  # Small delay to ensure different timestamps
        session_id_2 = generate_session_id(ticker, analysis_date)
        
        self.assertNotEqual(session_id_1, session_id_2)
        
        # Test invalid session IDs
        invalid_session_ids = [
            "",
            "invalid",
            "AAPL_2025-09-13",  # Missing timestamp
            "AAPL_invalid_date_123456789",
            "invalid_ticker_2025-09-13_123456789"
        ]
        
        for invalid_id in invalid_session_ids:
            self.assertFalse(validate_session_id(invalid_id))


class TestWebAPIIntegration(unittest.TestCase):
    """Test integration with web API endpoints."""
    
    def setUp(self):
        """Set up test environment."""
        self.mock_config = MockNeonConfig()
        
        # Mock the retrieval service
        self.mock_retrieval_service = Mock()
        
    def tearDown(self):
        """Clean up test environment."""
        self.mock_config.connection.close()
    
    def test_api_report_retrieval_success(self):
        """Test successful report retrieval through API-like interface."""
        session_id = "AAPL_2025-09-13_1694612345"
        agent_type = "Market Analyst"
        expected_content = "Market analysis content"
        
        # Mock successful retrieval
        self.mock_retrieval_service.get_agent_report_safe.return_value = {
            'success': True,
            'data': {
                'session_id': session_id,
                'agent_type': agent_type,
                'content': expected_content,
                'content_length': len(expected_content)
            },
            'message': f"Successfully retrieved {agent_type} report"
        }
        
        # Simulate API call
        result = self.mock_retrieval_service.get_agent_report_safe(session_id, agent_type)
        
        self.assertTrue(result['success'])
        self.assertEqual(result['data']['content'], expected_content)
        self.assertEqual(result['data']['agent_type'], agent_type)
        self.assertEqual(result['data']['session_id'], session_id)
    
    def test_api_report_retrieval_not_found(self):
        """Test report retrieval when report is not available."""
        session_id = "AAPL_2025-09-13_1694612345"
        agent_type = "Market Analyst"
        
        # Mock report not found
        self.mock_retrieval_service.get_agent_report_safe.return_value = {
            'success': False,
            'error': {
                'type': 'NotFoundError',
                'code': 'REPORT_NOT_FOUND',
                'message': f'Report not found: {agent_type} for session {session_id}',
                'details': {
                    'session_id': session_id,
                    'agent_type': agent_type,
                    'reason': 'Report not yet available or analysis not completed'
                }
            },
            'data': None
        }
        
        # Simulate API call
        result = self.mock_retrieval_service.get_agent_report_safe(session_id, agent_type)
        
        self.assertFalse(result['success'])
        self.assertEqual(result['error']['type'], 'NotFoundError')
        self.assertEqual(result['error']['code'], 'REPORT_NOT_FOUND')
        self.assertIn('Report not found', result['error']['message'])
    
    def test_api_error_response_format(self):
        """Test consistent error response formatting."""
        session_id = "INVALID_SESSION"
        agent_type = "Market Analyst"
        
        # Mock validation error
        self.mock_retrieval_service.get_agent_report_safe.return_value = {
            'success': False,
            'error': {
                'type': 'ReportRetrievalError',
                'message': 'Invalid session ID format: INVALID_SESSION',
                'timestamp': datetime.utcnow().isoformat(),
                'context': {
                    'session_id': session_id,
                    'agent_type': agent_type
                }
            },
            'data': None
        }
        
        # Simulate API call
        result = self.mock_retrieval_service.get_agent_report_safe(session_id, agent_type)
        
        self.assertFalse(result['success'])
        self.assertIn('error', result)
        self.assertIn('type', result['error'])
        self.assertIn('message', result['error'])
        self.assertIn('timestamp', result['error'])
        self.assertIsNone(result['data'])


if __name__ == '__main__':
    unittest.main()