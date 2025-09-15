"""
Report storage service for trading agent reports in Neon PostgreSQL.

This module provides the main service for storing agent reports, managing sessions,
and handling final decisions and analysis results.
"""

import logging
from typing import Optional, Dict, Any, List
from datetime import datetime, date
import uuid

from .neon_config import NeonConfig
from .connection_utils import ConnectionFactory, with_db_retry
from .session_utils import generate_session_id, validate_session_id
from .agent_validation import (
    ReportContentValidator, 
    AgentValidationError,
    validate_agent_report,
    LargeContentHandler
)
from .schema import AgentReportSchema

logger = logging.getLogger(__name__)


class ReportStorageError(Exception):
    """Custom exception for report storage errors."""
    pass


class ReportStorageService:
    """Service for storing trading agent reports in Neon PostgreSQL."""
    
    def __init__(self, config: Optional[NeonConfig] = None):
        """
        Initialize the report storage service.
        
        Args:
            config: Neon configuration instance. If None, creates a new one.
        """
        self.config = config or NeonConfig()
        self.connection_factory = ConnectionFactory(self.config)
        self.validator = ReportContentValidator()
        self.content_handler = LargeContentHandler()
        
    async def create_session(self, ticker: str, analysis_date: str) -> str:
        """
        Create a new analysis session in the database.
        
        Args:
            ticker: Stock ticker symbol
            analysis_date: Analysis date in YYYY-MM-DD format
            
        Returns:
            Unique session ID
            
        Raises:
            ReportStorageError: If session creation fails
            AgentValidationError: If input validation fails
        """
        try:
            # Generate unique session ID
            session_id = generate_session_id(ticker, analysis_date)
            
            # Validate inputs
            if not ticker or not isinstance(ticker, str):
                raise AgentValidationError("Ticker must be a non-empty string")
            
            if not analysis_date or not isinstance(analysis_date, str):
                raise AgentValidationError("Analysis date must be a non-empty string")
            
            # Clean and validate ticker
            clean_ticker = ticker.upper().strip()
            if not clean_ticker:
                raise AgentValidationError("Ticker cannot be empty after cleaning")
            
            # Insert new session record
            insert_query = """
                INSERT INTO agent_reports (session_id, ticker, analysis_date)
                VALUES (%s, %s, %s)
                ON CONFLICT (session_id) DO NOTHING
                RETURNING id, session_id
            """
            
            with self.connection_factory.get_cursor() as cursor:
                cursor.execute(insert_query, (session_id, clean_ticker, analysis_date))
                result = cursor.fetchone()
                
                if not result:
                    # Session already exists, return existing session_id
                    logger.info(f"Session {session_id} already exists")
                    return session_id
                
                logger.info(f"Created new session: {session_id} for {clean_ticker} on {analysis_date}")
                return session_id
                
        except AgentValidationError:
            raise
        except Exception as e:
            logger.error(f"Failed to create session for {ticker} on {analysis_date}: {e}")
            raise ReportStorageError(f"Session creation failed: {e}")
    
    def create_session_sync(self, ticker: str, analysis_date: str) -> str:
        """
        Synchronous version of create_session.
        
        Args:
            ticker: Stock ticker symbol
            analysis_date: Analysis date in YYYY-MM-DD format
            
        Returns:
            Unique session ID
        """
        try:
            # Generate unique session ID
            session_id = generate_session_id(ticker, analysis_date)
            
            # Validate inputs
            if not ticker or not isinstance(ticker, str):
                raise AgentValidationError("Ticker must be a non-empty string")
            
            if not analysis_date or not isinstance(analysis_date, str):
                raise AgentValidationError("Analysis date must be a non-empty string")
            
            # Clean and validate ticker
            clean_ticker = ticker.upper().strip()
            if not clean_ticker:
                raise AgentValidationError("Ticker cannot be empty after cleaning")
            
            # Insert new session record
            insert_query = """
                INSERT INTO agent_reports (session_id, ticker, analysis_date)
                VALUES (%s, %s, %s)
                ON CONFLICT (session_id) DO NOTHING
                RETURNING id, session_id
            """
            
            with self.connection_factory.get_cursor() as cursor:
                cursor.execute(insert_query, (session_id, clean_ticker, analysis_date))
                result = cursor.fetchone()
                
                if not result:
                    # Session already exists, return existing session_id
                    logger.info(f"Session {session_id} already exists")
                    return session_id
                
                logger.info(f"Created new session: {session_id} for {clean_ticker} on {analysis_date}")
                return session_id
                
        except AgentValidationError:
            raise
        except Exception as e:
            logger.error(f"Failed to create session for {ticker} on {analysis_date}: {e}")
            raise ReportStorageError(f"Session creation failed: {e}")
    
    @with_db_retry(max_retries=3)
    async def save_agent_report(self, session_id: str, agent_type: str, report_content: str) -> bool:
        """
        Save an individual agent report to the database.
        
        Args:
            session_id: Unique session identifier
            agent_type: Type of agent (e.g., 'Market Analyst')
            report_content: The report content to save
            
        Returns:
            True if successful, False otherwise
            
        Raises:
            ReportStorageError: If save operation fails
            AgentValidationError: If validation fails
        """
        try:
            # Validate session ID
            if not validate_session_id(session_id):
                raise AgentValidationError(f"Invalid session ID format: {session_id}")
            
            # Validate agent type and get column name
            column_name, sanitized_content = validate_agent_report(agent_type, report_content)
            
            # Handle large content
            if len(sanitized_content.encode('utf-8')) > 1024 * 1024:  # 1MB
                sanitized_content = self.content_handler.compress_content(sanitized_content)
                logger.warning(f"Compressed large report for {agent_type} in session {session_id}")
            
            # Update the specific agent report column
            update_query = f"""
                UPDATE agent_reports 
                SET {column_name} = %s, updated_at = CURRENT_TIMESTAMP
                WHERE session_id = %s
                RETURNING id
            """
            
            with self.connection_factory.get_cursor() as cursor:
                cursor.execute(update_query, (sanitized_content, session_id))
                result = cursor.fetchone()
                
                if not result:
                    raise ReportStorageError(f"Session {session_id} not found")
                
                logger.info(f"Saved {agent_type} report for session {session_id}")
                return True
                
        except (AgentValidationError, ReportStorageError):
            raise
        except Exception as e:
            logger.error(f"Failed to save {agent_type} report for session {session_id}: {e}")
            raise ReportStorageError(f"Failed to save agent report: {e}")
    
    def save_agent_report_sync(self, session_id: str, agent_type: str, report_content: str) -> bool:
        """
        Synchronous version of save_agent_report.
        
        Args:
            session_id: Unique session identifier
            agent_type: Type of agent (e.g., 'Market Analyst')
            report_content: The report content to save
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Validate session ID
            if not validate_session_id(session_id):
                raise AgentValidationError(f"Invalid session ID format: {session_id}")
            
            # Validate agent type and get column name
            column_name, sanitized_content = validate_agent_report(agent_type, report_content)
            
            # Handle large content
            if len(sanitized_content.encode('utf-8')) > 1024 * 1024:  # 1MB
                sanitized_content = self.content_handler.compress_content(sanitized_content)
                logger.warning(f"Compressed large report for {agent_type} in session {session_id}")
            
            # Update the specific agent report column
            update_query = f"""
                UPDATE agent_reports 
                SET {column_name} = %s, updated_at = CURRENT_TIMESTAMP
                WHERE session_id = %s
                RETURNING id
            """
            
            with self.connection_factory.get_cursor() as cursor:
                cursor.execute(update_query, (sanitized_content, session_id))
                result = cursor.fetchone()
                
                if not result:
                    raise ReportStorageError(f"Session {session_id} not found")
                
                logger.info(f"Saved {agent_type} report for session {session_id}")
                return True
                
        except (AgentValidationError, ReportStorageError):
            raise
        except Exception as e:
            logger.error(f"Failed to save {agent_type} report for session {session_id}: {e}")
            raise ReportStorageError(f"Failed to save agent report: {e}")
    
    @with_db_retry(max_retries=3)
    async def save_final_analysis(self, session_id: str, analysis: str, recommendation: str) -> bool:
        """
        Save final analysis and recommendation to the database.
        
        Args:
            session_id: Unique session identifier
            analysis: Final analysis content
            recommendation: Trading recommendation (BUY/SELL/HOLD)
            
        Returns:
            True if successful, False otherwise
            
        Raises:
            ReportStorageError: If save operation fails
            AgentValidationError: If validation fails
        """
        try:
            # Validate session ID
            if not validate_session_id(session_id):
                raise AgentValidationError(f"Invalid session ID format: {session_id}")
            
            # Validate and sanitize content
            sanitized_analysis = self.validator.validate_report_content(analysis, "Final Analysis")
            validated_recommendation = self.validator.validate_recommendation(recommendation)
            
            # Handle large content
            if len(sanitized_analysis.encode('utf-8')) > 1024 * 1024:  # 1MB
                sanitized_analysis = self.content_handler.compress_content(sanitized_analysis)
                logger.warning(f"Compressed large final analysis for session {session_id}")
            
            # Update final analysis and recommendation
            update_query = """
                UPDATE agent_reports 
                SET final_analysis = %s, 
                    recommendation = %s,
                    updated_at = CURRENT_TIMESTAMP
                WHERE session_id = %s
                RETURNING id
            """
            
            with self.connection_factory.get_cursor() as cursor:
                cursor.execute(update_query, (
                    sanitized_analysis, 
                    validated_recommendation, 
                    session_id
                ))
                result = cursor.fetchone()
                
                if not result:
                    raise ReportStorageError(f"Session {session_id} not found")
                
                logger.info(f"Saved final analysis and recommendation for session {session_id}")
                return True
                
        except (AgentValidationError, ReportStorageError):
            raise
        except Exception as e:
            logger.error(f"Failed to save final analysis for session {session_id}: {e}")
            raise ReportStorageError(f"Failed to save final analysis: {e}")
    
    def save_final_analysis_sync(self, session_id: str, analysis: str, recommendation: str) -> bool:
        """
        Synchronous version of save_final_analysis.
        
        Args:
            session_id: Unique session identifier
            analysis: Final analysis content
            recommendation: Trading recommendation (BUY/SELL/HOLD)
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Validate session ID
            if not validate_session_id(session_id):
                raise AgentValidationError(f"Invalid session ID format: {session_id}")
            
            # Validate and sanitize content
            sanitized_analysis = self.validator.validate_report_content(analysis, "Final Analysis")
            validated_recommendation = self.validator.validate_recommendation(recommendation)
            
            # Handle large content
            if len(sanitized_analysis.encode('utf-8')) > 1024 * 1024:  # 1MB
                sanitized_analysis = self.content_handler.compress_content(sanitized_analysis)
                logger.warning(f"Compressed large final analysis for session {session_id}")
            
            # Update final analysis and recommendation
            update_query = """
                UPDATE agent_reports 
                SET final_analysis = %s, 
                    recommendation = %s,
                    updated_at = CURRENT_TIMESTAMP
                WHERE session_id = %s
                RETURNING id
            """
            
            with self.connection_factory.get_cursor() as cursor:
                cursor.execute(update_query, (
                    sanitized_analysis, 
                    validated_recommendation, 
                    session_id
                ))
                result = cursor.fetchone()
                
                if not result:
                    raise ReportStorageError(f"Session {session_id} not found")
                
                logger.info(f"Saved final analysis and recommendation for session {session_id}")
                return True
                
        except (AgentValidationError, ReportStorageError):
            raise
        except Exception as e:
            logger.error(f"Failed to save final decision for session {session_id}: {e}")
            raise ReportStorageError(f"Failed to save final decision: {e}")
    
    @with_db_retry(max_retries=2)
    def update_session_timestamp(self, session_id: str) -> bool:
        """
        Update the session timestamp to mark activity.
        
        Args:
            session_id: Unique session identifier
            
        Returns:
            True if successful, False otherwise
            
        Raises:
            ReportStorageError: If update fails
        """
        try:
            # Validate session ID
            if not validate_session_id(session_id):
                raise AgentValidationError(f"Invalid session ID format: {session_id}")
            
            update_query = """
                UPDATE agent_reports 
                SET updated_at = CURRENT_TIMESTAMP
                WHERE session_id = %s
                RETURNING id
            """
            
            with self.connection_factory.get_cursor() as cursor:
                cursor.execute(update_query, (session_id,))
                result = cursor.fetchone()
                
                if not result:
                    raise ReportStorageError(f"Session {session_id} not found")
                
                logger.debug(f"Updated timestamp for session {session_id}")
                return True
                
        except (AgentValidationError, ReportStorageError):
            raise
        except Exception as e:
            logger.error(f"Failed to update timestamp for session {session_id}: {e}")
            raise ReportStorageError(f"Failed to update session timestamp: {e}")
    
    def session_exists(self, session_id: str) -> bool:
        """
        Check if a session exists in the database.
        
        Args:
            session_id: Session ID to check
            
        Returns:
            True if session exists, False otherwise
        """
        try:
            if not validate_session_id(session_id):
                return False
            
            query = "SELECT 1 FROM agent_reports WHERE session_id = %s"
            
            with self.connection_factory.get_cursor() as cursor:
                cursor.execute(query, (session_id,))
                result = cursor.fetchone()
                return result is not None
                
        except Exception as e:
            logger.error(f"Failed to check session existence for {session_id}: {e}")
            return False
    
    def get_session_info(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        Get basic session information.
        
        Args:
            session_id: Session ID to query
            
        Returns:
            Dictionary with session info or None if not found
        """
        try:
            if not validate_session_id(session_id):
                return None
            
            query = """
                SELECT session_id, ticker, analysis_date, created_at, updated_at
                FROM agent_reports 
                WHERE session_id = %s
            """
            
            with self.connection_factory.get_cursor() as cursor:
                cursor.execute(query, (session_id,))
                result = cursor.fetchone()
                
                if result:
                    return dict(result)
                return None
                
        except Exception as e:
            logger.error(f"Failed to get session info for {session_id}: {e}")
            return None
    
    def cleanup_old_sessions(self, days_old: int = 30) -> int:
        """
        Clean up old sessions from the database.
        
        Args:
            days_old: Number of days old to consider for cleanup
            
        Returns:
            Number of sessions cleaned up
        """
        try:
            cleanup_query = """
                DELETE FROM agent_reports 
                WHERE created_at < CURRENT_TIMESTAMP - INTERVAL '%s days'
                RETURNING session_id
            """
            
            with self.connection_factory.get_cursor() as cursor:
                cursor.execute(cleanup_query, (days_old,))
                deleted_sessions = cursor.fetchall()
                count = len(deleted_sessions)
                
                if count > 0:
                    logger.info(f"Cleaned up {count} sessions older than {days_old} days")
                
                return count
                
        except Exception as e:
            logger.error(f"Failed to cleanup old sessions: {e}")
            return 0