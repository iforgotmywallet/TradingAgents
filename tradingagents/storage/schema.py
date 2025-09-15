"""
Database schema definition for agent reports storage in Neon PostgreSQL.

This module defines the database schema for storing trading agent reports,
including table definitions, indexes, and constraints.
"""

from typing import Dict, List
import uuid
from datetime import datetime, date


# SQL schema definition for agent_reports table
AGENT_REPORTS_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS agent_reports (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id VARCHAR(255) UNIQUE NOT NULL,
    ticker VARCHAR(10) NOT NULL,
    analysis_date DATE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
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
    final_analysis TEXT,
    recommendation VARCHAR(10) CHECK (recommendation IN ('BUY', 'SELL', 'HOLD'))
);
"""

# Index definitions for optimized queries
INDEXES_SQL = [
    "CREATE INDEX IF NOT EXISTS idx_agent_reports_session_id ON agent_reports(session_id);",
    "CREATE INDEX IF NOT EXISTS idx_agent_reports_ticker_date ON agent_reports(ticker, analysis_date);",
    "CREATE INDEX IF NOT EXISTS idx_agent_reports_ticker ON agent_reports(ticker);",
    "CREATE INDEX IF NOT EXISTS idx_agent_reports_date ON agent_reports(analysis_date);",
    "CREATE INDEX IF NOT EXISTS idx_agent_reports_created_at ON agent_reports(created_at);"
]

# Trigger for updating updated_at timestamp
UPDATE_TIMESTAMP_TRIGGER_SQL = """
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_agent_reports_updated_at 
    BEFORE UPDATE ON agent_reports 
    FOR EACH ROW 
    EXECUTE FUNCTION update_updated_at_column();
"""

# Agent type to column mapping for dynamic report storage
AGENT_TYPE_MAPPING: Dict[str, str] = {
    'Market Analyst': 'market_analyst_report',
    'News Analyst': 'news_analyst_report',
    'Fundamentals Analyst': 'fundamentals_analyst_report',
    'Social Analyst': 'social_analyst_report',
    'Bull Researcher': 'bull_researcher_report',
    'Bear Researcher': 'bear_researcher_report',
    'Research Manager': 'research_manager_report',
    'Trader': 'trader_report',
    'Risky Analyst': 'risky_analyst_report',
    'Neutral Analyst': 'neutral_analyst_report',
    'Safe Analyst': 'safe_analyst_report',
    'Portfolio Manager': 'portfolio_manager_report'
}

# Reverse mapping for column to agent type
COLUMN_TO_AGENT_TYPE: Dict[str, str] = {v: k for k, v in AGENT_TYPE_MAPPING.items()}

# All report columns for validation
REPORT_COLUMNS: List[str] = list(AGENT_TYPE_MAPPING.values()) + [
    'final_analysis'
]

# Schema validation queries
SCHEMA_VALIDATION_QUERIES = [
    "SELECT column_name, data_type FROM information_schema.columns WHERE table_name = 'agent_reports';",
    "SELECT indexname FROM pg_indexes WHERE tablename = 'agent_reports';",
    "SELECT trigger_name FROM information_schema.triggers WHERE event_object_table = 'agent_reports';"
]


class AgentReportSchema:
    """
    Schema definition and validation class for agent reports table.
    """
    
    @staticmethod
    def get_table_creation_sql() -> str:
        """Get the SQL statement for creating the agent_reports table."""
        return AGENT_REPORTS_TABLE_SQL
    
    @staticmethod
    def get_indexes_sql() -> List[str]:
        """Get the SQL statements for creating indexes."""
        return INDEXES_SQL
    
    @staticmethod
    def get_trigger_sql() -> str:
        """Get the SQL statement for creating the update timestamp trigger."""
        return UPDATE_TIMESTAMP_TRIGGER_SQL
    
    @staticmethod
    def get_agent_column(agent_type: str) -> str:
        """
        Get the database column name for a given agent type.
        
        Args:
            agent_type: The agent type name
            
        Returns:
            The corresponding database column name
            
        Raises:
            ValueError: If agent type is not supported
        """
        if agent_type not in AGENT_TYPE_MAPPING:
            raise ValueError(f"Unsupported agent type: {agent_type}")
        return AGENT_TYPE_MAPPING[agent_type]
    
    @staticmethod
    def get_agent_type(column_name: str) -> str:
        """
        Get the agent type for a given database column name.
        
        Args:
            column_name: The database column name
            
        Returns:
            The corresponding agent type name
            
        Raises:
            ValueError: If column name is not a valid agent column
        """
        if column_name not in COLUMN_TO_AGENT_TYPE:
            raise ValueError(f"Invalid agent column: {column_name}")
        return COLUMN_TO_AGENT_TYPE[column_name]
    
    @staticmethod
    def is_valid_agent_type(agent_type: str) -> bool:
        """Check if an agent type is valid."""
        return agent_type in AGENT_TYPE_MAPPING
    
    @staticmethod
    def is_valid_report_column(column_name: str) -> bool:
        """Check if a column name is a valid report column."""
        return column_name in REPORT_COLUMNS
    
    @staticmethod
    def get_all_agent_types() -> List[str]:
        """Get all supported agent types."""
        return list(AGENT_TYPE_MAPPING.keys())
    
    @staticmethod
    def get_all_report_columns() -> List[str]:
        """Get all report column names."""
        return REPORT_COLUMNS.copy()
    
    @staticmethod
    def validate_recommendation(recommendation: str) -> bool:
        """Validate that a recommendation value is allowed."""
        return recommendation in ['BUY', 'SELL', 'HOLD']


# Complete schema deployment SQL (for migration use)
COMPLETE_SCHEMA_SQL = f"""
-- Create agent_reports table
{AGENT_REPORTS_TABLE_SQL}

-- Create indexes
{chr(10).join(INDEXES_SQL)}

-- Create update timestamp trigger
{UPDATE_TIMESTAMP_TRIGGER_SQL}
"""