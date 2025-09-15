"""
Unit tests for session ID generation and validation functions.

Tests cover session ID generation, parsing, validation, and utility functions
for extracting components from session IDs.
"""

import unittest
import time
from datetime import datetime
from unittest.mock import patch

from tradingagents.storage.session_utils import (
    generate_session_id,
    parse_session_id,
    validate_session_id,
    get_session_date,
    get_session_ticker,
    get_session_timestamp
)


class TestSessionUtils(unittest.TestCase):
    """Test cases for session utility functions."""
    
    def test_generate_session_id_valid_inputs(self):
        """Test session ID generation with valid inputs."""
        ticker = "AAPL"
        analysis_date = "2025-09-13"
        
        with patch('time.time', return_value=1694612345):
            session_id = generate_session_id(ticker, analysis_date)
        
        expected = "AAPL_2025-09-13_1694612345"
        self.assertEqual(session_id, expected)
    
    def test_generate_session_id_lowercase_ticker(self):
        """Test session ID generation converts ticker to uppercase."""
        ticker = "aapl"
        analysis_date = "2025-09-13"
        
        with patch('time.time', return_value=1694612345):
            session_id = generate_session_id(ticker, analysis_date)
        
        expected = "AAPL_2025-09-13_1694612345"
        self.assertEqual(session_id, expected)
    
    def test_generate_session_id_ticker_with_special_chars(self):
        """Test session ID generation cleans special characters from ticker."""
        ticker = "BRK.B"
        analysis_date = "2025-09-13"
        
        with patch('time.time', return_value=1694612345):
            session_id = generate_session_id(ticker, analysis_date)
        
        expected = "BRKB_2025-09-13_1694612345"
        self.assertEqual(session_id, expected)
    
    def test_generate_session_id_empty_ticker(self):
        """Test session ID generation fails with empty ticker."""
        with self.assertRaises(ValueError) as context:
            generate_session_id("", "2025-09-13")
        
        self.assertIn("Ticker must be a non-empty string", str(context.exception))
    
    def test_generate_session_id_none_ticker(self):
        """Test session ID generation fails with None ticker."""
        with self.assertRaises(ValueError) as context:
            generate_session_id(None, "2025-09-13")
        
        self.assertIn("Ticker must be a non-empty string", str(context.exception))
    
    def test_generate_session_id_invalid_ticker_type(self):
        """Test session ID generation fails with invalid ticker type."""
        with self.assertRaises(ValueError) as context:
            generate_session_id(123, "2025-09-13")
        
        self.assertIn("Ticker must be a non-empty string", str(context.exception))
    
    def test_generate_session_id_empty_date(self):
        """Test session ID generation fails with empty date."""
        with self.assertRaises(ValueError) as context:
            generate_session_id("AAPL", "")
        
        self.assertIn("Analysis date must be a non-empty string", str(context.exception))
    
    def test_generate_session_id_none_date(self):
        """Test session ID generation fails with None date."""
        with self.assertRaises(ValueError) as context:
            generate_session_id("AAPL", None)
        
        self.assertIn("Analysis date must be a non-empty string", str(context.exception))
    
    def test_generate_session_id_invalid_date_format(self):
        """Test session ID generation fails with invalid date format."""
        with self.assertRaises(ValueError) as context:
            generate_session_id("AAPL", "2025/09/13")
        
        self.assertIn("Analysis date must be in YYYY-MM-DD format", str(context.exception))
    
    def test_generate_session_id_ticker_only_special_chars(self):
        """Test session ID generation fails when ticker has no alphanumeric chars."""
        with self.assertRaises(ValueError) as context:
            generate_session_id("...", "2025-09-13")
        
        self.assertIn("Ticker must contain alphanumeric characters", str(context.exception))
    
    def test_parse_session_id_valid(self):
        """Test parsing valid session ID."""
        session_id = "AAPL_2025-09-13_1694612345"
        
        ticker, date, timestamp = parse_session_id(session_id)
        
        self.assertEqual(ticker, "AAPL")
        self.assertEqual(date, "2025-09-13")
        self.assertEqual(timestamp, 1694612345)
    
    def test_parse_session_id_empty(self):
        """Test parsing empty session ID fails."""
        with self.assertRaises(ValueError) as context:
            parse_session_id("")
        
        self.assertIn("Session ID must be a non-empty string", str(context.exception))
    
    def test_parse_session_id_none(self):
        """Test parsing None session ID fails."""
        with self.assertRaises(ValueError) as context:
            parse_session_id(None)
        
        self.assertIn("Session ID must be a non-empty string", str(context.exception))
    
    def test_parse_session_id_wrong_format(self):
        """Test parsing session ID with wrong format fails."""
        with self.assertRaises(ValueError) as context:
            parse_session_id("AAPL_2025-09-13")
        
        self.assertIn("Session ID must have format: ticker_date_timestamp", str(context.exception))
    
    def test_parse_session_id_invalid_ticker(self):
        """Test parsing session ID with invalid ticker fails."""
        with self.assertRaises(ValueError) as context:
            parse_session_id("aa.pl_2025-09-13_1694612345")
        
        self.assertIn("Invalid ticker format in session ID", str(context.exception))
    
    def test_parse_session_id_invalid_date(self):
        """Test parsing session ID with invalid date fails."""
        with self.assertRaises(ValueError) as context:
            parse_session_id("AAPL_2025/09/13_1694612345")
        
        self.assertIn("Invalid date format in session ID", str(context.exception))
    
    def test_parse_session_id_invalid_timestamp(self):
        """Test parsing session ID with invalid timestamp fails."""
        with self.assertRaises(ValueError) as context:
            parse_session_id("AAPL_2025-09-13_invalid")
        
        self.assertIn("Invalid timestamp format in session ID", str(context.exception))
    
    def test_validate_session_id_valid(self):
        """Test validation of valid session ID."""
        session_id = "AAPL_2025-09-13_1694612345"
        
        result = validate_session_id(session_id)
        
        self.assertTrue(result)
    
    def test_validate_session_id_invalid(self):
        """Test validation of invalid session ID."""
        session_id = "invalid_session_id"
        
        result = validate_session_id(session_id)
        
        self.assertFalse(result)
    
    def test_validate_session_id_empty(self):
        """Test validation of empty session ID."""
        result = validate_session_id("")
        
        self.assertFalse(result)
    
    def test_get_session_date_valid(self):
        """Test extracting date from valid session ID."""
        session_id = "AAPL_2025-09-13_1694612345"
        
        date = get_session_date(session_id)
        
        self.assertEqual(date, "2025-09-13")
    
    def test_get_session_date_invalid(self):
        """Test extracting date from invalid session ID."""
        session_id = "invalid_session_id"
        
        date = get_session_date(session_id)
        
        self.assertIsNone(date)
    
    def test_get_session_ticker_valid(self):
        """Test extracting ticker from valid session ID."""
        session_id = "AAPL_2025-09-13_1694612345"
        
        ticker = get_session_ticker(session_id)
        
        self.assertEqual(ticker, "AAPL")
    
    def test_get_session_ticker_invalid(self):
        """Test extracting ticker from invalid session ID."""
        session_id = "invalid_session_id"
        
        ticker = get_session_ticker(session_id)
        
        self.assertIsNone(ticker)
    
    def test_get_session_timestamp_valid(self):
        """Test extracting timestamp from valid session ID."""
        session_id = "AAPL_2025-09-13_1694612345"
        
        timestamp = get_session_timestamp(session_id)
        
        expected_datetime = datetime.fromtimestamp(1694612345)
        self.assertEqual(timestamp, expected_datetime)
    
    def test_get_session_timestamp_invalid(self):
        """Test extracting timestamp from invalid session ID."""
        session_id = "invalid_session_id"
        
        timestamp = get_session_timestamp(session_id)
        
        self.assertIsNone(timestamp)
    
    def test_get_session_timestamp_invalid_timestamp_value(self):
        """Test extracting invalid timestamp value."""
        session_id = "AAPL_2025-09-13_999999999999999"  # Invalid timestamp
        
        timestamp = get_session_timestamp(session_id)
        
        self.assertIsNone(timestamp)
    
    def test_session_id_uniqueness(self):
        """Test that session IDs are unique across time."""
        ticker = "AAPL"
        analysis_date = "2025-09-13"
        
        # Generate multiple session IDs with small time differences
        session_ids = []
        for i in range(5):
            # Mock different timestamps to ensure uniqueness
            with patch('time.time', return_value=1694612345 + i):
                session_id = generate_session_id(ticker, analysis_date)
                session_ids.append(session_id)
        
        # All session IDs should be unique
        self.assertEqual(len(session_ids), len(set(session_ids)))
    
    def test_session_id_components_roundtrip(self):
        """Test that session ID components can be round-tripped."""
        original_ticker = "TSLA"
        original_date = "2025-12-25"
        
        with patch('time.time', return_value=1703520000):
            session_id = generate_session_id(original_ticker, original_date)
        
        parsed_ticker, parsed_date, parsed_timestamp = parse_session_id(session_id)
        
        self.assertEqual(parsed_ticker, original_ticker)
        self.assertEqual(parsed_date, original_date)
        self.assertEqual(parsed_timestamp, 1703520000)


if __name__ == '__main__':
    unittest.main()