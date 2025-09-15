"""
Simplified integration tests for end-to-end storage functionality.

These tests verify the core workflow and demonstrate that the storage
components work together correctly.
"""

import unittest
import sqlite3
from unittest.mock import Mock, patch

from tradingagents.storage.report_storage import ReportStorageService
from tradingagents.storage.session_utils import generate_session_id, validate_session_id


class MockNeonConfig:
    """Mock Neon configuration for testing."""
    
    def __init__(self):
        self.connection = sqlite3.connect(':memory:')
        self.connection.row_factory = sqlite3.Row
        self.connection_pool = Mock()
        self._setup_test_schema()
    
    def _setup_test_schema(self):
        """Set up test database schema."""
        cursor = self.connection.cursor()
        cursor.execute("""
            CREATE TABLE agent_reports (
                id TEXT PRIMARY KEY DEFAULT (hex(randomblob(16))),
                session_id TEXT UNIQUE NOT NULL,
                ticker TEXT NOT NULL,
                analysis_date DATE NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                market_analyst_report TEXT,
                news_analyst_report TEXT,
                fundamentals_analyst_report TEXT,
                final_decision TEXT,
                final_analysis TEXT,
                recommendation TEXT
            )
        """)
        self.connection.commit()
    
    def get_connection(self):
        return self.connection
    
    def return_connection(self, conn):
        pass
    
    def create_connection_pool(self):
        pass
    
    def health_check(self):
        return {'healthy': True}


class MockConnectionFactory:
    """Mock connection factory for testing."""
    
    def __init__(self, config):
        self.config = config
    
    def get_cursor(self):
        return self.config.get_connection()


class TestStorageIntegrationSimple(unittest.TestCase):
    """Simplified integration tests for storage components."""
    
    def setUp(self):
        """Set up test environment."""
        self.mock_config = MockNeonConfig()
        
        # Patch dependencies
        self.patches = [
            patch('tradingagents.storage.report_storage.ConnectionFactory', MockConnectionFactory),
            patch('tradingagents.storage.report_storage.ReportContentValidator'),
            patch('tradingagents.storage.report_storage.LargeContentHandler'),
            patch('tradingagents.storage.report_storage.validate_agent_report', 
                  side_effect=self._mock_validate_agent_report),
        ]
        
        for p in self.patches:
            p.start()
        
        self.storage_service = ReportStorageService(self.mock_config)
    
    def tearDown(self):
        """Clean up test environment."""
        for p in self.patches:
            p.stop()
        self.mock_config.connection.close()
    
    def _mock_validate_agent_report(self, agent_type, content):
        """Mock agent report validation."""
        agent_mapping = {
            'Market Analyst': 'market_analyst_report',
            'News Analyst': 'news_analyst_report',
            'Fundamentals Analyst': 'fundamentals_analyst_report',
        }
        
        if agent_type not in agent_mapping:
            raise ValueError(f"Invalid agent type: {agent_type}")
        
        return agent_mapping[agent_type], content
    
    def test_session_creation_and_storage(self):
        """Test basic session creation and report storage."""
        ticker = "AAPL"
        analysis_date = "2025-09-13"
        
        # Create session
        session_id = self.storage_service.create_session_sync(ticker, analysis_date)
        
        # Verify session ID format
        self.assertIsNotNone(session_id)
        self.assertTrue(validate_session_id(session_id))
        self.assertIn(ticker, session_id)
        self.assertIn(analysis_date, session_id)
        
        # Verify session exists
        self.assertTrue(self.storage_service.session_exists(session_id))
        
        # Save a report
        report_content = "Market analysis shows positive trends"
        result = self.storage_service.save_agent_report_sync(
            session_id, 'Market Analyst', report_content
        )
        self.assertTrue(result)
        
        # Verify report was saved by checking database directly
        cursor = self.mock_config.connection.cursor()
        cursor.execute(
            "SELECT market_analyst_report FROM agent_reports WHERE session_id = ?",
            (session_id,)
        )
        row = cursor.fetchone()
        self.assertIsNotNone(row)
        self.assertEqual(row['market_analyst_report'], report_content)
    
    def test_multiple_reports_same_session(self):
        """Test saving multiple reports to the same session."""
        ticker = "TSLA"
        analysis_date = "2025-09-13"
        
        # Create session
        session_id = self.storage_service.create_session_sync(ticker, analysis_date)
        
        # Save multiple reports
        reports = {
            'Market Analyst': 'Market analysis content',
            'News Analyst': 'News analysis content',
            'Fundamentals Analyst': 'Fundamentals analysis content'
        }
        
        for agent_type, content in reports.items():
            result = self.storage_service.save_agent_report_sync(
                session_id, agent_type, content
            )
            self.assertTrue(result)
        
        # Verify all reports were saved
        cursor = self.mock_config.connection.cursor()
        cursor.execute(
            """SELECT market_analyst_report, news_analyst_report, fundamentals_analyst_report 
               FROM agent_reports WHERE session_id = ?""",
            (session_id,)
        )
        row = cursor.fetchone()
        
        self.assertEqual(row['market_analyst_report'], reports['Market Analyst'])
        self.assertEqual(row['news_analyst_report'], reports['News Analyst'])
        self.assertEqual(row['fundamentals_analyst_report'], reports['Fundamentals Analyst'])
    
    def test_final_decision_storage(self):
        """Test storing final decision and analysis."""
        ticker = "NVDA"
        analysis_date = "2025-09-13"
        
        # Create session
        session_id = self.storage_service.create_session_sync(ticker, analysis_date)
        
        # Save final decision
        final_decision = "Recommend BUY based on analysis"
        final_analysis = "Comprehensive analysis shows strong potential"
        recommendation = "BUY"
        
        # Mock the validator methods
        self.storage_service.validator.validate_report_content.side_effect = lambda x, y: x
        self.storage_service.validator.validate_recommendation.return_value = recommendation
        
        result = self.storage_service.save_final_decision_sync(
            session_id, final_decision, final_analysis, recommendation
        )
        self.assertTrue(result)
        
        # Verify final decision was saved
        cursor = self.mock_config.connection.cursor()
        cursor.execute(
            "SELECT final_decision, final_analysis, recommendation FROM agent_reports WHERE session_id = ?",
            (session_id,)
        )
        row = cursor.fetchone()
        
        self.assertEqual(row['final_decision'], final_decision)
        self.assertEqual(row['final_analysis'], final_analysis)
        self.assertEqual(row['recommendation'], recommendation)
    
    def test_session_id_validation(self):
        """Test session ID generation and validation."""
        # Test valid session ID
        ticker = "AAPL"
        analysis_date = "2025-09-13"
        session_id = generate_session_id(ticker, analysis_date)
        
        self.assertTrue(validate_session_id(session_id))
        self.assertIn(ticker, session_id)
        self.assertIn(analysis_date, session_id)
        
        # Test invalid session IDs
        invalid_ids = [
            "",
            "invalid",
            "AAPL_2025-09-13",  # Missing timestamp
            "AAPL_invalid_date_123456789",
        ]
        
        for invalid_id in invalid_ids:
            self.assertFalse(validate_session_id(invalid_id))
    
    def test_error_handling(self):
        """Test error handling for invalid inputs."""
        # Test invalid ticker
        with self.assertRaises(Exception):
            self.storage_service.create_session_sync("", "2025-09-13")
        
        # Test invalid date
        with self.assertRaises(Exception):
            self.storage_service.create_session_sync("AAPL", "")
        
        # Test saving to non-existent session
        fake_session_id = "FAKE_2025-09-13_1234567890"
        
        with patch('tradingagents.storage.report_storage.validate_session_id', return_value=True):
            with self.assertRaises(Exception):
                self.storage_service.save_agent_report_sync(
                    fake_session_id, 'Market Analyst', 'content'
                )
    
    def test_concurrent_sessions(self):
        """Test handling multiple sessions concurrently."""
        sessions = []
        
        # Create multiple sessions
        for i in range(3):
            ticker = f"STOCK{i}"
            analysis_date = "2025-09-13"
            session_id = self.storage_service.create_session_sync(ticker, analysis_date)
            sessions.append((session_id, ticker))
        
        # Verify all sessions are unique and valid
        session_ids = [s[0] for s in sessions]
        self.assertEqual(len(set(session_ids)), 3)  # All unique
        
        for session_id, ticker in sessions:
            self.assertTrue(validate_session_id(session_id))
            self.assertIn(ticker, session_id)
        
        # Save reports to each session
        for session_id, ticker in sessions:
            content = f"Analysis for {ticker}"
            result = self.storage_service.save_agent_report_sync(
                session_id, 'Market Analyst', content
            )
            self.assertTrue(result)
        
        # Verify reports are correctly associated
        for session_id, ticker in sessions:
            cursor = self.mock_config.connection.cursor()
            cursor.execute(
                "SELECT market_analyst_report FROM agent_reports WHERE session_id = ?",
                (session_id,)
            )
            row = cursor.fetchone()
            expected_content = f"Analysis for {ticker}"
            self.assertEqual(row['market_analyst_report'], expected_content)


if __name__ == '__main__':
    unittest.main()