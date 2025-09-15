"""
Agent type mapping and validation utilities for report storage.

This module provides validation and sanitization functions for agent reports,
including content validation, agent type mapping, and large content handling.
"""

import re
import html
from typing import Optional, Dict, Any, List
from .schema import AGENT_TYPE_MAPPING, AgentReportSchema


# Maximum report content size (1MB)
MAX_REPORT_SIZE = 1024 * 1024

# Minimum report content size (10 characters)
MIN_REPORT_SIZE = 10

# Allowed HTML tags for report content (basic formatting)
ALLOWED_HTML_TAGS = {
    'p', 'br', 'strong', 'em', 'ul', 'ol', 'li', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
    'blockquote', 'code', 'pre', 'table', 'tr', 'td', 'th', 'thead', 'tbody'
}


class AgentValidationError(Exception):
    """Custom exception for agent validation errors."""
    pass


class ReportContentValidator:
    """Validator for agent report content."""
    
    @staticmethod
    def validate_agent_type(agent_type: str) -> bool:
        """
        Validate that an agent type is supported.
        
        Args:
            agent_type: The agent type to validate
            
        Returns:
            True if valid, False otherwise
        """
        return AgentReportSchema.is_valid_agent_type(agent_type)
    
    @staticmethod
    def get_column_for_agent(agent_type: str) -> str:
        """
        Get the database column name for an agent type.
        
        Args:
            agent_type: The agent type
            
        Returns:
            Database column name
            
        Raises:
            AgentValidationError: If agent type is invalid
        """
        try:
            return AgentReportSchema.get_agent_column(agent_type)
        except ValueError as e:
            raise AgentValidationError(str(e))
    
    @staticmethod
    def validate_report_content(content: str, agent_type: str) -> str:
        """
        Validate and sanitize report content.
        
        Args:
            content: The report content to validate
            agent_type: The agent type for context
            
        Returns:
            Sanitized content
            
        Raises:
            AgentValidationError: If content is invalid
        """
        if not isinstance(content, str):
            raise AgentValidationError("Report content must be a string")
        
        if not content.strip():
            raise AgentValidationError("Report content cannot be empty")
        
        if len(content) < MIN_REPORT_SIZE:
            raise AgentValidationError(f"Report content too short (minimum {MIN_REPORT_SIZE} characters)")
        
        if len(content.encode('utf-8')) > MAX_REPORT_SIZE:
            raise AgentValidationError(f"Report content too large (maximum {MAX_REPORT_SIZE} bytes)")
        
        # Sanitize content
        sanitized = ReportContentValidator._sanitize_content(content)
        
        return sanitized
    
    @staticmethod
    def _sanitize_content(content: str) -> str:
        """
        Sanitize report content by removing potentially harmful elements.
        
        Args:
            content: Raw content to sanitize
            
        Returns:
            Sanitized content
        """
        # Remove null bytes
        content = content.replace('\x00', '')
        
        # Escape HTML entities for safety (but preserve basic formatting)
        content = html.escape(content, quote=False)
        
        # Remove excessive whitespace
        content = re.sub(r'\n\s*\n\s*\n', '\n\n', content)  # Max 2 consecutive newlines
        content = re.sub(r'[ \t]+', ' ', content)  # Normalize spaces and tabs
        
        # Trim whitespace
        content = content.strip()
        
        return content
    
    @staticmethod
    def validate_recommendation(recommendation: str) -> str:
        """
        Validate and normalize recommendation value.
        
        Args:
            recommendation: The recommendation to validate
            
        Returns:
            Normalized recommendation
            
        Raises:
            AgentValidationError: If recommendation is invalid
        """
        if not isinstance(recommendation, str):
            raise AgentValidationError("Recommendation must be a string")
        
        normalized = recommendation.strip().upper()
        
        if not AgentReportSchema.validate_recommendation(normalized):
            raise AgentValidationError(f"Invalid recommendation: {recommendation}. Must be BUY, SELL, or HOLD")
        
        return normalized
    
    @staticmethod
    def validate_session_data(session_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate complete session data before storage.
        
        Args:
            session_data: Dictionary containing session data
            
        Returns:
            Validated and sanitized session data
            
        Raises:
            AgentValidationError: If session data is invalid
        """
        if not isinstance(session_data, dict):
            raise AgentValidationError("Session data must be a dictionary")
        
        validated_data = {}
        
        # Validate required fields
        required_fields = ['session_id', 'ticker', 'analysis_date']
        for field in required_fields:
            if field not in session_data:
                raise AgentValidationError(f"Missing required field: {field}")
            validated_data[field] = session_data[field]
        
        # Validate ticker
        ticker = session_data['ticker']
        if not isinstance(ticker, str) or not re.match(r'^[A-Z0-9]{1,10}$', ticker.upper()):
            raise AgentValidationError("Invalid ticker format")
        validated_data['ticker'] = ticker.upper()
        
        # Validate analysis_date
        analysis_date = session_data['analysis_date']
        if not isinstance(analysis_date, str) or not re.match(r'^\d{4}-\d{2}-\d{2}$', analysis_date):
            raise AgentValidationError("Invalid analysis_date format (must be YYYY-MM-DD)")
        validated_data['analysis_date'] = analysis_date
        
        # Validate agent reports
        for agent_type in AgentReportSchema.get_all_agent_types():
            column_name = AgentReportSchema.get_agent_column(agent_type)
            if column_name in session_data and session_data[column_name] is not None:
                validated_data[column_name] = ReportContentValidator.validate_report_content(
                    session_data[column_name], agent_type
                )
        
        # Validate final analysis
        if 'final_analysis' in session_data and session_data['final_analysis'] is not None:
            validated_data['final_analysis'] = ReportContentValidator.validate_report_content(
                session_data['final_analysis'], 'Final Analysis'
            )
        
        # Validate recommendation
        if 'recommendation' in session_data and session_data['recommendation'] is not None:
            validated_data['recommendation'] = ReportContentValidator.validate_recommendation(
                session_data['recommendation']
            )
        
        return validated_data


class LargeContentHandler:
    """Handler for large report content that exceeds normal limits."""
    
    @staticmethod
    def compress_content(content: str) -> str:
        """
        Compress large content by removing redundant information.
        
        Args:
            content: Content to compress
            
        Returns:
            Compressed content
        """
        if len(content.encode('utf-8')) <= MAX_REPORT_SIZE:
            return content
        
        # Remove excessive repetition
        lines = content.split('\n')
        compressed_lines = []
        prev_line = None
        repeat_count = 0
        
        for line in lines:
            if line.strip() == prev_line:
                repeat_count += 1
                if repeat_count <= 2:  # Allow up to 2 repetitions
                    compressed_lines.append(line)
            else:
                if repeat_count > 2:
                    compressed_lines.append(f"... (repeated {repeat_count - 2} more times)")
                compressed_lines.append(line)
                prev_line = line.strip()
                repeat_count = 0
        
        compressed = '\n'.join(compressed_lines)
        
        # If still too large, truncate with warning
        if len(compressed.encode('utf-8')) > MAX_REPORT_SIZE:
            max_chars = MAX_REPORT_SIZE - 100  # Leave room for truncation message
            compressed = compressed[:max_chars] + "\n\n[CONTENT TRUNCATED - Report exceeded maximum size]"
        
        return compressed
    
    @staticmethod
    def split_large_content(content: str, max_size: int = MAX_REPORT_SIZE) -> List[str]:
        """
        Split large content into smaller chunks.
        
        Args:
            content: Content to split
            max_size: Maximum size per chunk
            
        Returns:
            List of content chunks
        """
        if len(content.encode('utf-8')) <= max_size:
            return [content]
        
        chunks = []
        current_chunk = ""
        
        for line in content.split('\n'):
            test_chunk = current_chunk + '\n' + line if current_chunk else line
            if len(test_chunk.encode('utf-8')) > max_size:
                if current_chunk:
                    chunks.append(current_chunk)
                    current_chunk = line
                else:
                    # Single line is too large, force split
                    chunks.append(line[:max_size])
                    current_chunk = line[max_size:]
            else:
                current_chunk = test_chunk
        
        if current_chunk:
            chunks.append(current_chunk)
        
        return chunks


# Convenience functions for common validation tasks
def validate_agent_report(agent_type: str, content: str) -> tuple[str, str]:
    """
    Validate agent type and report content.
    
    Returns:
        Tuple of (column_name, sanitized_content)
    """
    validator = ReportContentValidator()
    column_name = validator.get_column_for_agent(agent_type)
    sanitized_content = validator.validate_report_content(content, agent_type)
    return column_name, sanitized_content


def get_supported_agent_types() -> List[str]:
    """Get list of all supported agent types."""
    return AgentReportSchema.get_all_agent_types()


def is_valid_agent_type(agent_type: str) -> bool:
    """Check if agent type is supported."""
    return ReportContentValidator.validate_agent_type(agent_type)