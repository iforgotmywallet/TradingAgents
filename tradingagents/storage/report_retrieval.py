"""
Report retrieval service for trading agent reports from Neon PostgreSQL.

This module provides services for retrieving individual agent reports, complete session data,
and final decisions from the database with comprehensive error handling and logging.
"""

import logging
from typing import Optional, Dict, Any, List
from datetime import datetime
import psycopg2
from psycopg2 import OperationalError, DatabaseError
from psycopg2.extras import RealDictCursor

from .neon_config import NeonConfig
from .schema import AgentReportSchema, AGENT_TYPE_MAPPING
from .session_utils import validate_session_id, parse_session_id
from .agent_validation import AgentValidationError

logger = logging.getLogger(__name__)

# Configure logging for debugging report retrieval issues
def configure_retrieval_logging(level: str = "INFO") -> None:
    """
    Configure logging for report retrieval debugging.
    
    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR)
    """
    log_level = getattr(logging, level.upper(), logging.INFO)
    
    # Create formatter for detailed logging
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s'
    )
    
    # Configure handler if not already configured
    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(formatter)
        logger.addHandler(handler)
    
    logger.setLevel(log_level)
    logger.info(f"Report retrieval logging configured at {level} level")


class ErrorResponseFormatter:
    """Formatter for consistent API error responses."""
    
    @staticmethod
    def format_error_response(error: Exception, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Format an exception into a consistent error response.
        
        Args:
            error: The exception to format
            context: Additional context information
            
        Returns:
            Formatted error response dictionary
        """
        response = {
            'success': False,
            'error': {
                'type': error.__class__.__name__,
                'message': str(error),
                'timestamp': datetime.utcnow().isoformat()
            },
            'data': None
        }
        
        # Add error code if available
        if hasattr(error, 'error_code'):
            response['error']['code'] = error.error_code
        
        # Add error details if available
        if hasattr(error, 'details'):
            response['error']['details'] = error.details
        
        # Add context if provided
        if context:
            response['error']['context'] = context
        
        return response
    
    @staticmethod
    def format_success_response(data: Any, message: str = "Success") -> Dict[str, Any]:
        """
        Format a successful response.
        
        Args:
            data: The response data
            message: Success message
            
        Returns:
            Formatted success response dictionary
        """
        return {
            'success': True,
            'message': message,
            'data': data,
            'timestamp': datetime.utcnow().isoformat()
        }
    
    @staticmethod
    def format_not_found_response(resource_type: str, identifier: str, details: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Format a not found response.
        
        Args:
            resource_type: Type of resource not found (e.g., 'report', 'session')
            identifier: The identifier that was not found
            details: Additional details
            
        Returns:
            Formatted not found response dictionary
        """
        response = {
            'success': False,
            'error': {
                'type': 'NotFoundError',
                'code': f"{resource_type.upper()}_NOT_FOUND",
                'message': f"{resource_type.title()} not found: {identifier}",
                'timestamp': datetime.utcnow().isoformat()
            },
            'data': None
        }
        
        if details:
            response['error']['details'] = details
        
        return response


class ReportRetrievalError(Exception):
    """Custom exception for report retrieval errors."""
    
    def __init__(self, message: str, error_code: str = "RETRIEVAL_ERROR", details: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.error_code = error_code
        self.details = details or {}


class ReportNotFoundError(ReportRetrievalError):
    """Exception raised when a requested report is not found."""
    
    def __init__(self, message: str, session_id: str = None, agent_type: str = None):
        super().__init__(message, "REPORT_NOT_FOUND", {
            'session_id': session_id,
            'agent_type': agent_type
        })


class SessionNotFoundError(ReportRetrievalError):
    """Exception raised when a requested session is not found."""
    
    def __init__(self, message: str, session_id: str = None):
        super().__init__(message, "SESSION_NOT_FOUND", {
            'session_id': session_id
        })


class DatabaseConnectionError(ReportRetrievalError):
    """Exception raised when database connection fails."""
    
    def __init__(self, message: str, original_error: Exception = None):
        super().__init__(message, "DATABASE_CONNECTION_ERROR", {
            'original_error': str(original_error) if original_error else None
        })


class ReportRetrievalService:
    """Service for retrieving agent reports from Neon PostgreSQL database."""
    
    def __init__(self, config: Optional[NeonConfig] = None):
        """
        Initialize the report retrieval service.
        
        Args:
            config: Neon database configuration. If None, creates a new instance.
        """
        self.config = config or NeonConfig()
        self._ensure_connection_pool()
    
    def _ensure_connection_pool(self) -> None:
        """Ensure connection pool is created."""
        try:
            if self.config.connection_pool is None:
                self.config.create_connection_pool()
        except Exception as e:
            logger.error(f"Failed to create connection pool: {e}")
            raise ReportRetrievalError(f"Database connection failed: {e}")
    
    def _get_connection(self):
        """Get a database connection with error handling."""
        try:
            return self.config.get_connection()
        except Exception as e:
            logger.error(f"Failed to get database connection: {e}")
            raise DatabaseConnectionError(f"Database connection failed: {e}", e)
    
    def _return_connection(self, conn) -> None:
        """Return connection to pool with error handling."""
        try:
            self.config.return_connection(conn)
        except Exception as e:
            logger.warning(f"Failed to return connection to pool: {e}")
    
    def session_exists(self, session_id: str) -> bool:
        """
        Check if a session exists in the database.
        
        Args:
            session_id: The session ID to check
            
        Returns:
            True if session exists, False otherwise
            
        Raises:
            ReportRetrievalError: If database operation fails
        """
        if not validate_session_id(session_id):
            logger.warning(f"Invalid session ID format: {session_id}")
            return False
        
        conn = None
        try:
            conn = self._get_connection()
            with conn.cursor() as cursor:
                cursor.execute(
                    "SELECT 1 FROM agent_reports WHERE session_id = %s LIMIT 1",
                    (session_id,)
                )
                result = cursor.fetchone()
                exists = result is not None
                
                logger.debug(f"Session {session_id} exists: {exists}")
                return exists
                
        except (OperationalError, DatabaseError) as e:
            logger.error(f"Database error checking session existence: {e}")
            raise ReportRetrievalError(f"Failed to check session existence: {e}")
        except Exception as e:
            logger.error(f"Unexpected error checking session existence: {e}")
            raise ReportRetrievalError(f"Unexpected error: {e}")
        finally:
            if conn:
                self._return_connection(conn)
    
    def get_agent_report(self, session_id: str, agent_type: str) -> Optional[str]:
        """
        Retrieve an individual agent report by session ID and agent type.
        
        Args:
            session_id: The session ID
            agent_type: The agent type (e.g., 'Market Analyst')
            
        Returns:
            The report content or None if not available
            
        Raises:
            ReportRetrievalError: If database operation fails
            SessionNotFoundError: If session doesn't exist
            AgentValidationError: If agent type is invalid
        """
        # Validate inputs
        if not validate_session_id(session_id):
            raise ReportRetrievalError(f"Invalid session ID format: {session_id}")
        
        if not AgentReportSchema.is_valid_agent_type(agent_type):
            raise AgentValidationError(f"Invalid agent type: {agent_type}")
        
        # Get column name for agent type
        try:
            column_name = AgentReportSchema.get_agent_column(agent_type)
        except ValueError as e:
            raise AgentValidationError(str(e))
        
        conn = None
        try:
            conn = self._get_connection()
            with conn.cursor() as cursor:
                # First check if session exists
                cursor.execute(
                    "SELECT 1 FROM agent_reports WHERE session_id = %s LIMIT 1",
                    (session_id,)
                )
                if not cursor.fetchone():
                    raise SessionNotFoundError(f"Session not found: {session_id}")
                
                # Get the specific agent report
                cursor.execute(
                    f"SELECT {column_name} FROM agent_reports WHERE session_id = %s",
                    (session_id,)
                )
                result = cursor.fetchone()
                
                if result and result[column_name]:
                    logger.debug(f"Retrieved {agent_type} report for session {session_id}")
                    return result[column_name]
                else:
                    logger.debug(f"No {agent_type} report available for session {session_id}")
                    return None
                    
        except SessionNotFoundError:
            raise
        except AgentValidationError:
            raise
        except (OperationalError, DatabaseError) as e:
            logger.error(f"Database error retrieving agent report: {e}")
            raise ReportRetrievalError(f"Failed to retrieve agent report: {e}")
        except Exception as e:
            logger.error(f"Unexpected error retrieving agent report: {e}")
            raise ReportRetrievalError(f"Unexpected error: {e}")
        finally:
            if conn:
                self._return_connection(conn)
    
    def get_session_reports(self, session_id: str) -> Dict[str, Any]:
        """
        Retrieve complete session data including all agent reports and metadata.
        
        Args:
            session_id: The session ID
            
        Returns:
            Dictionary containing all session data
            
        Raises:
            ReportRetrievalError: If database operation fails
            SessionNotFoundError: If session doesn't exist
        """
        if not validate_session_id(session_id):
            raise ReportRetrievalError(f"Invalid session ID format: {session_id}")
        
        conn = None
        try:
            conn = self._get_connection()
            with conn.cursor() as cursor:
                cursor.execute(
                    "SELECT * FROM agent_reports WHERE session_id = %s",
                    (session_id,)
                )
                result = cursor.fetchone()
                
                if not result:
                    raise SessionNotFoundError(f"Session not found: {session_id}")
                
                # Convert to dictionary and organize data
                session_data = dict(result)
                
                # Organize agent reports
                agent_reports = {}
                for agent_type, column_name in AGENT_TYPE_MAPPING.items():
                    if session_data.get(column_name):
                        agent_reports[agent_type] = session_data[column_name]
                
                # Build response
                response = {
                    'session_id': session_data['session_id'],
                    'ticker': session_data['ticker'],
                    'analysis_date': session_data['analysis_date'].isoformat() if session_data['analysis_date'] else None,
                    'created_at': session_data['created_at'].isoformat() if session_data['created_at'] else None,
                    'updated_at': session_data['updated_at'].isoformat() if session_data['updated_at'] else None,
                    'agent_reports': agent_reports,
                    'final_analysis': session_data.get('final_analysis'),
                    'recommendation': session_data.get('recommendation')
                }
                
                logger.debug(f"Retrieved complete session data for {session_id}")
                return response
                
        except SessionNotFoundError:
            raise
        except (OperationalError, DatabaseError) as e:
            logger.error(f"Database error retrieving session reports: {e}")
            raise ReportRetrievalError(f"Failed to retrieve session reports: {e}")
        except Exception as e:
            logger.error(f"Unexpected error retrieving session reports: {e}")
            raise ReportRetrievalError(f"Unexpected error: {e}")
        finally:
            if conn:
                self._return_connection(conn)
    
    def get_final_analysis(self, session_id: str) -> Optional[Dict[str, str]]:
        """
        Retrieve final analysis and recommendation for a session.
        
        Args:
            session_id: The session ID
            
        Returns:
            Dictionary with final_analysis and recommendation, or None if not available
            
        Raises:
            ReportRetrievalError: If database operation fails
            SessionNotFoundError: If session doesn't exist
        """
        if not validate_session_id(session_id):
            raise ReportRetrievalError(f"Invalid session ID format: {session_id}")
        
        conn = None
        try:
            conn = self._get_connection()
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT final_analysis, recommendation 
                    FROM agent_reports 
                    WHERE session_id = %s
                    """,
                    (session_id,)
                )
                result = cursor.fetchone()
                
                if not result:
                    raise SessionNotFoundError(f"Session not found: {session_id}")
                
                # Check if any final data is available
                if not any([result['final_analysis'], result['recommendation']]):
                    logger.debug(f"No final analysis available for session {session_id}")
                    return None
                
                response = {
                    'final_analysis': result['final_analysis'],
                    'recommendation': result['recommendation']
                }
                
                logger.debug(f"Retrieved final analysis for session {session_id}")
                return response
                
        except SessionNotFoundError:
            raise
        except (OperationalError, DatabaseError) as e:
            logger.error(f"Database error retrieving final analysis: {e}")
            raise ReportRetrievalError(f"Failed to retrieve final analysis: {e}")
        except Exception as e:
            logger.error(f"Unexpected error retrieving final analysis: {e}")
            raise ReportRetrievalError(f"Unexpected error: {e}")
        finally:
            if conn:
                self._return_connection(conn)
    
    def get_sessions_by_ticker(self, ticker: str, limit: int = 50) -> List[Dict[str, Any]]:
        """
        Retrieve recent sessions for a specific ticker.
        
        Args:
            ticker: Stock ticker symbol
            limit: Maximum number of sessions to return
            
        Returns:
            List of session summaries
            
        Raises:
            ReportRetrievalError: If database operation fails
        """
        if not ticker or not isinstance(ticker, str):
            raise ReportRetrievalError("Ticker must be a non-empty string")
        
        ticker = ticker.upper()
        
        conn = None
        try:
            conn = self._get_connection()
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT session_id, ticker, analysis_date, created_at, updated_at, 
                           recommendation, 
                           CASE WHEN final_analysis IS NOT NULL THEN true ELSE false END as has_final_analysis
                    FROM agent_reports 
                    WHERE ticker = %s 
                    ORDER BY created_at DESC 
                    LIMIT %s
                    """,
                    (ticker, limit)
                )
                results = cursor.fetchall()
                
                sessions = []
                for row in results:
                    sessions.append({
                        'session_id': row['session_id'],
                        'ticker': row['ticker'],
                        'analysis_date': row['analysis_date'].isoformat() if row['analysis_date'] else None,
                        'created_at': row['created_at'].isoformat() if row['created_at'] else None,
                        'updated_at': row['updated_at'].isoformat() if row['updated_at'] else None,
                        'recommendation': row['recommendation'],
                        'has_final_analysis': row['has_final_analysis']
                    })
                
                logger.debug(f"Retrieved {len(sessions)} sessions for ticker {ticker}")
                return sessions
                
        except (OperationalError, DatabaseError) as e:
            logger.error(f"Database error retrieving sessions by ticker: {e}")
            raise ReportRetrievalError(f"Failed to retrieve sessions: {e}")
        except Exception as e:
            logger.error(f"Unexpected error retrieving sessions by ticker: {e}")
            raise ReportRetrievalError(f"Unexpected error: {e}")
        finally:
            if conn:
                self._return_connection(conn)
    
    def get_available_reports(self, session_id: str) -> List[str]:
        """
        Get list of available agent reports for a session.
        
        Args:
            session_id: The session ID
            
        Returns:
            List of agent types that have reports available
            
        Raises:
            ReportRetrievalError: If database operation fails
            SessionNotFoundError: If session doesn't exist
        """
        if not validate_session_id(session_id):
            raise ReportRetrievalError(f"Invalid session ID format: {session_id}")
        
        conn = None
        try:
            conn = self._get_connection()
            with conn.cursor() as cursor:
                # Get all report columns
                columns = list(AGENT_TYPE_MAPPING.values())
                column_list = ', '.join(columns)
                
                cursor.execute(
                    f"SELECT {column_list} FROM agent_reports WHERE session_id = %s",
                    (session_id,)
                )
                result = cursor.fetchone()
                
                if not result:
                    raise SessionNotFoundError(f"Session not found: {session_id}")
                
                # Find which reports are available
                available_reports = []
                for agent_type, column_name in AGENT_TYPE_MAPPING.items():
                    if result[column_name] is not None:
                        available_reports.append(agent_type)
                
                logger.debug(f"Available reports for session {session_id}: {available_reports}")
                return available_reports
                
        except SessionNotFoundError:
            raise
        except (OperationalError, DatabaseError) as e:
            logger.error(f"Database error getting available reports: {e}")
            raise ReportRetrievalError(f"Failed to get available reports: {e}")
        except Exception as e:
            logger.error(f"Unexpected error getting available reports: {e}")
            raise ReportRetrievalError(f"Unexpected error: {e}")
        finally:
            if conn:
                self._return_connection(conn)
    
    def health_check(self) -> Dict[str, Any]:
        """
        Perform health check on the retrieval service.
        
        Returns:
            Dictionary with health status information
        """
        health_status = {
            'service': 'ReportRetrievalService',
            'healthy': False,
            'database_connection': False,
            'error': None
        }
        
        try:
            # Test database connection
            db_health = self.config.health_check()
            health_status['database_connection'] = db_health['healthy']
            
            if db_health['healthy']:
                # Test a simple query
                conn = self._get_connection()
                try:
                    with conn.cursor() as cursor:
                        cursor.execute("SELECT COUNT(*) FROM agent_reports LIMIT 1")
                        cursor.fetchone()
                    health_status['healthy'] = True
                finally:
                    self._return_connection(conn)
            else:
                health_status['error'] = db_health.get('error', 'Database connection failed')
                
        except Exception as e:
            health_status['error'] = str(e)
            logger.error(f"Health check failed: {e}")
        
        return health_status
    
    # API-friendly methods with consistent response format
    
    def get_agent_report_safe(self, session_id: str, agent_type: str) -> Dict[str, Any]:
        """
        Safely retrieve an agent report with consistent error handling.
        
        Args:
            session_id: The session ID
            agent_type: The agent type
            
        Returns:
            Formatted response dictionary with success/error status
        """
        try:
            report_content = self.get_agent_report(session_id, agent_type)
            
            if report_content is None:
                return ErrorResponseFormatter.format_not_found_response(
                    'report', 
                    f"{agent_type} for session {session_id}",
                    {
                        'session_id': session_id,
                        'agent_type': agent_type,
                        'reason': 'Report not yet available or analysis not completed'
                    }
                )
            
            return ErrorResponseFormatter.format_success_response(
                {
                    'session_id': session_id,
                    'agent_type': agent_type,
                    'content': report_content,
                    'content_length': len(report_content)
                },
                f"Successfully retrieved {agent_type} report"
            )
            
        except SessionNotFoundError as e:
            logger.warning(f"Session not found: {session_id}")
            return ErrorResponseFormatter.format_error_response(e, {
                'session_id': session_id,
                'agent_type': agent_type
            })
        except AgentValidationError as e:
            logger.warning(f"Invalid agent type: {agent_type}")
            return ErrorResponseFormatter.format_error_response(e, {
                'session_id': session_id,
                'agent_type': agent_type
            })
        except DatabaseConnectionError as e:
            logger.error(f"Database connection error retrieving report: {e}")
            return ErrorResponseFormatter.format_error_response(e, {
                'session_id': session_id,
                'agent_type': agent_type
            })
        except Exception as e:
            logger.error(f"Unexpected error retrieving agent report: {e}")
            return ErrorResponseFormatter.format_error_response(
                ReportRetrievalError(f"Unexpected error: {e}", "UNEXPECTED_ERROR"),
                {
                    'session_id': session_id,
                    'agent_type': agent_type
                }
            )
    
    def get_session_reports_safe(self, session_id: str) -> Dict[str, Any]:
        """
        Safely retrieve complete session data with consistent error handling.
        
        Args:
            session_id: The session ID
            
        Returns:
            Formatted response dictionary with success/error status
        """
        try:
            session_data = self.get_session_reports(session_id)
            
            # Add summary information
            available_reports = list(session_data['agent_reports'].keys())
            total_reports = len(available_reports)
            has_final_analysis = bool(session_data.get('final_analysis'))
            
            session_data['summary'] = {
                'total_reports': total_reports,
                'available_reports': available_reports,
                'has_final_analysis': has_final_analysis,
                'completion_status': 'complete' if has_final_analysis else 'in_progress'
            }
            
            return ErrorResponseFormatter.format_success_response(
                session_data,
                f"Successfully retrieved session data with {total_reports} reports"
            )
            
        except SessionNotFoundError as e:
            logger.warning(f"Session not found: {session_id}")
            return ErrorResponseFormatter.format_error_response(e, {
                'session_id': session_id
            })
        except DatabaseConnectionError as e:
            logger.error(f"Database connection error retrieving session: {e}")
            return ErrorResponseFormatter.format_error_response(e, {
                'session_id': session_id
            })
        except Exception as e:
            logger.error(f"Unexpected error retrieving session reports: {e}")
            return ErrorResponseFormatter.format_error_response(
                ReportRetrievalError(f"Unexpected error: {e}", "UNEXPECTED_ERROR"),
                {
                    'session_id': session_id
                }
            )
    
    def get_final_analysis_safe(self, session_id: str) -> Dict[str, Any]:
        """
        Safely retrieve final analysis with consistent error handling.
        
        Args:
            session_id: The session ID
            
        Returns:
            Formatted response dictionary with success/error status
        """
        try:
            final_analysis = self.get_final_analysis(session_id)
            
            if final_analysis is None:
                return ErrorResponseFormatter.format_not_found_response(
                    'final analysis',
                    f"session {session_id}",
                    {
                        'session_id': session_id,
                        'reason': 'Final analysis not yet available or analysis not completed'
                    }
                )
            
            return ErrorResponseFormatter.format_success_response(
                final_analysis,
                "Successfully retrieved final analysis"
            )
            
        except SessionNotFoundError as e:
            logger.warning(f"Session not found: {session_id}")
            return ErrorResponseFormatter.format_error_response(e, {
                'session_id': session_id
            })
        except DatabaseConnectionError as e:
            logger.error(f"Database connection error retrieving final decision: {e}")
            return ErrorResponseFormatter.format_error_response(e, {
                'session_id': session_id
            })
        except Exception as e:
            logger.error(f"Unexpected error retrieving final decision: {e}")
            return ErrorResponseFormatter.format_error_response(
                ReportRetrievalError(f"Unexpected error: {e}", "UNEXPECTED_ERROR"),
                {
                    'session_id': session_id
                }
            )
    
    def get_report_status(self, session_id: str) -> Dict[str, Any]:
        """
        Get the status of reports for a session without retrieving full content.
        
        Args:
            session_id: The session ID
            
        Returns:
            Formatted response with report availability status
        """
        try:
            if not self.session_exists(session_id):
                return ErrorResponseFormatter.format_not_found_response(
                    'session',
                    session_id,
                    {'reason': 'Session does not exist'}
                )
            
            available_reports = self.get_available_reports(session_id)
            final_analysis = self.get_final_analysis(session_id)
            
            # Calculate completion percentage
            total_possible_reports = len(AGENT_TYPE_MAPPING)
            completion_percentage = (len(available_reports) / total_possible_reports) * 100
            
            status_data = {
                'session_id': session_id,
                'available_reports': available_reports,
                'total_reports': len(available_reports),
                'total_possible_reports': total_possible_reports,
                'completion_percentage': round(completion_percentage, 1),
                'has_final_analysis': final_analysis is not None,
                'status': 'complete' if final_analysis else 'in_progress',
                'missing_reports': [
                    agent_type for agent_type in AGENT_TYPE_MAPPING.keys()
                    if agent_type not in available_reports
                ]
            }
            
            return ErrorResponseFormatter.format_success_response(
                status_data,
                f"Report status retrieved - {len(available_reports)}/{total_possible_reports} reports available"
            )
            
        except DatabaseConnectionError as e:
            logger.error(f"Database connection error getting report status: {e}")
            return ErrorResponseFormatter.format_error_response(e, {
                'session_id': session_id
            })
        except Exception as e:
            logger.error(f"Unexpected error getting report status: {e}")
            return ErrorResponseFormatter.format_error_response(
                ReportRetrievalError(f"Unexpected error: {e}", "UNEXPECTED_ERROR"),
                {
                    'session_id': session_id
                }
            )