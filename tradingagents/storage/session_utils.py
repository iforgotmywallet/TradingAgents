"""
Session management utilities for trading agent reports.

This module provides utilities for generating, parsing, and validating session IDs
used to uniquely identify trading analysis sessions in the database.
"""

import time
import re
from typing import Tuple, Optional
from datetime import datetime


def generate_session_id(ticker: str, analysis_date: str) -> str:
    """
    Generate unique session ID using ticker, date, and timestamp.
    
    Format: {ticker}_{date}_{timestamp}
    Example: AAPL_2025-09-13_1694612345
    
    Args:
        ticker: Stock ticker symbol (e.g., 'AAPL')
        analysis_date: Analysis date in YYYY-MM-DD format
        
    Returns:
        Unique session ID string
        
    Raises:
        ValueError: If ticker or date format is invalid
    """
    if not ticker or not isinstance(ticker, str):
        raise ValueError("Ticker must be a non-empty string")
    
    if not analysis_date or not isinstance(analysis_date, str):
        raise ValueError("Analysis date must be a non-empty string")
    
    # Validate date format
    if not re.match(r'^\d{4}-\d{2}-\d{2}$', analysis_date):
        raise ValueError("Analysis date must be in YYYY-MM-DD format")
    
    # Clean ticker (uppercase, alphanumeric only)
    clean_ticker = re.sub(r'[^A-Z0-9]', '', ticker.upper())
    if not clean_ticker:
        raise ValueError("Ticker must contain alphanumeric characters")
    
    timestamp = int(time.time())
    return f"{clean_ticker}_{analysis_date}_{timestamp}"


def parse_session_id(session_id: str) -> Tuple[str, str, int]:
    """
    Parse session ID back to its components.
    
    Args:
        session_id: Session ID in format {ticker}_{date}_{timestamp}
        
    Returns:
        Tuple of (ticker, analysis_date, timestamp)
        
    Raises:
        ValueError: If session ID format is invalid
    """
    if not session_id or not isinstance(session_id, str):
        raise ValueError("Session ID must be a non-empty string")
    
    parts = session_id.split('_')
    if len(parts) != 3:
        raise ValueError("Session ID must have format: ticker_date_timestamp")
    
    ticker, analysis_date, timestamp_str = parts
    
    # Validate ticker
    if not re.match(r'^[A-Z0-9]+$', ticker):
        raise ValueError("Invalid ticker format in session ID")
    
    # Validate date
    if not re.match(r'^\d{4}-\d{2}-\d{2}$', analysis_date):
        raise ValueError("Invalid date format in session ID")
    
    # Validate timestamp
    try:
        timestamp = int(timestamp_str)
    except ValueError:
        raise ValueError("Invalid timestamp format in session ID")
    
    return ticker, analysis_date, timestamp


def validate_session_id(session_id: str) -> bool:
    """
    Validate session ID format without raising exceptions.
    
    Args:
        session_id: Session ID to validate
        
    Returns:
        True if valid, False otherwise
    """
    try:
        parse_session_id(session_id)
        return True
    except ValueError:
        return False


def get_session_date(session_id: str) -> Optional[str]:
    """
    Extract analysis date from session ID.
    
    Args:
        session_id: Session ID to parse
        
    Returns:
        Analysis date string or None if invalid
    """
    try:
        _, analysis_date, _ = parse_session_id(session_id)
        return analysis_date
    except ValueError:
        return None


def get_session_ticker(session_id: str) -> Optional[str]:
    """
    Extract ticker from session ID.
    
    Args:
        session_id: Session ID to parse
        
    Returns:
        Ticker string or None if invalid
    """
    try:
        ticker, _, _ = parse_session_id(session_id)
        return ticker
    except ValueError:
        return None


def get_session_timestamp(session_id: str) -> Optional[datetime]:
    """
    Extract timestamp from session ID as datetime object.
    
    Args:
        session_id: Session ID to parse
        
    Returns:
        Datetime object or None if invalid
    """
    try:
        _, _, timestamp = parse_session_id(session_id)
        return datetime.fromtimestamp(timestamp)
    except (ValueError, OSError):
        return None