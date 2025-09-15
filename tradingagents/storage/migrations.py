"""
Database migration system for Neon PostgreSQL.

This module provides migration functionality to create, update, and rollback
database schema changes in a controlled manner.
"""

import logging
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
from typing import List, Dict, Optional, Tuple
from datetime import datetime
import hashlib

from .neon_config import NeonConfig
from .schema import COMPLETE_SCHEMA_SQL, SCHEMA_VALIDATION_QUERIES


logger = logging.getLogger(__name__)


class Migration:
    """Represents a single database migration."""
    
    def __init__(self, version: str, name: str, up_sql: str, down_sql: str = ""):
        self.version = version
        self.name = name
        self.up_sql = up_sql
        self.down_sql = down_sql
        self.checksum = self._calculate_checksum()
    
    def _calculate_checksum(self) -> str:
        """Calculate checksum for migration integrity verification."""
        content = f"{self.version}{self.name}{self.up_sql}{self.down_sql}"
        return hashlib.sha256(content.encode()).hexdigest()


class MigrationRunner:
    """
    Handles database migrations for the agent reports system.
    """
    
    def __init__(self, config: NeonConfig):
        self.config = config
        self.migrations = self._get_migrations()
    
    def _get_migrations(self) -> List[Migration]:
        """Define all available migrations."""
        return [
            Migration(
                version="001",
                name="create_agent_reports_table",
                up_sql=COMPLETE_SCHEMA_SQL,
                down_sql="DROP TABLE IF EXISTS agent_reports CASCADE;"
            ),
            Migration(
                version="002",
                name="create_migration_history_table",
                up_sql=self._get_migration_history_table_sql(),
                down_sql="DROP TABLE IF EXISTS migration_history CASCADE;"
            ),
            Migration(
                version="003",
                name="remove_final_decision_column",
                up_sql="ALTER TABLE agent_reports DROP COLUMN IF EXISTS final_decision;",
                down_sql="ALTER TABLE agent_reports ADD COLUMN final_decision TEXT;"
            )
        ]
    
    def _get_migration_history_table_sql(self) -> str:
        """SQL for creating migration history tracking table."""
        return """
        CREATE TABLE IF NOT EXISTS migration_history (
            id SERIAL PRIMARY KEY,
            version VARCHAR(10) NOT NULL UNIQUE,
            name VARCHAR(255) NOT NULL,
            checksum VARCHAR(64) NOT NULL,
            applied_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
            applied_by VARCHAR(255) DEFAULT CURRENT_USER
        );
        
        CREATE INDEX IF NOT EXISTS idx_migration_history_version ON migration_history(version);
        """
    
    def _get_connection(self):
        """Get database connection with autocommit for DDL operations."""
        conn = psycopg2.connect(self.config.connection_string)
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        return conn
    
    def _migration_exists(self, conn, version: str) -> bool:
        """Check if a migration has already been applied."""
        try:
            with conn.cursor() as cursor:
                cursor.execute(
                    "SELECT 1 FROM migration_history WHERE version = %s",
                    (version,)
                )
                return cursor.fetchone() is not None
        except psycopg2.Error:
            # If migration_history table doesn't exist, no migrations have been applied
            return False
    
    def _record_migration(self, conn, migration: Migration) -> None:
        """Record a migration as applied in the migration history."""
        with conn.cursor() as cursor:
            cursor.execute("""
                INSERT INTO migration_history (version, name, checksum)
                VALUES (%s, %s, %s)
                ON CONFLICT (version) DO UPDATE SET
                    name = EXCLUDED.name,
                    checksum = EXCLUDED.checksum,
                    applied_at = CURRENT_TIMESTAMP
            """, (migration.version, migration.name, migration.checksum))
    
    def _remove_migration_record(self, conn, version: str) -> None:
        """Remove a migration record from history."""
        with conn.cursor() as cursor:
            cursor.execute(
                "DELETE FROM migration_history WHERE version = %s",
                (version,)
            )
    
    def _validate_migration_integrity(self, conn, migration: Migration) -> bool:
        """Validate that migration hasn't been tampered with."""
        try:
            with conn.cursor() as cursor:
                cursor.execute(
                    "SELECT checksum FROM migration_history WHERE version = %s",
                    (migration.version,)
                )
                result = cursor.fetchone()
                if result:
                    stored_checksum = result[0]
                    return stored_checksum == migration.checksum
                return True  # Migration not applied yet
        except psycopg2.Error:
            return True  # Assume valid if we can't check
    
    def migrate_up(self, target_version: Optional[str] = None) -> bool:
        """
        Apply migrations up to target version (or all if None).
        
        Args:
            target_version: Stop at this version, or apply all if None
            
        Returns:
            True if successful, False otherwise
        """
        try:
            conn = self._get_connection()
            
            # First, ensure migration history table exists
            migration_history_migration = next(
                (m for m in self.migrations if m.name == "create_migration_history_table"),
                None
            )
            
            if migration_history_migration and not self._migration_exists(conn, migration_history_migration.version):
                logger.info("Creating migration history table...")
                with conn.cursor() as cursor:
                    cursor.execute(migration_history_migration.up_sql)
                self._record_migration(conn, migration_history_migration)
            
            # Apply other migrations
            applied_count = 0
            for migration in self.migrations:
                if migration.name == "create_migration_history_table":
                    continue  # Already handled above
                
                if target_version and migration.version > target_version:
                    break
                
                if self._migration_exists(conn, migration.version):
                    if not self._validate_migration_integrity(conn, migration):
                        logger.error(f"Migration {migration.version} integrity check failed!")
                        return False
                    logger.info(f"Migration {migration.version} already applied, skipping...")
                    continue
                
                logger.info(f"Applying migration {migration.version}: {migration.name}")
                
                try:
                    with conn.cursor() as cursor:
                        cursor.execute(migration.up_sql)
                    
                    self._record_migration(conn, migration)
                    applied_count += 1
                    logger.info(f"Successfully applied migration {migration.version}")
                    
                except psycopg2.Error as e:
                    logger.error(f"Failed to apply migration {migration.version}: {e}")
                    return False
            
            logger.info(f"Migration complete. Applied {applied_count} migrations.")
            return True
            
        except Exception as e:
            logger.error(f"Migration failed: {e}")
            return False
        finally:
            if 'conn' in locals():
                conn.close()
    
    def migrate_down(self, target_version: str) -> bool:
        """
        Rollback migrations down to target version.
        
        Args:
            target_version: Rollback to this version
            
        Returns:
            True if successful, False otherwise
        """
        try:
            conn = self._get_connection()
            
            # Get applied migrations in reverse order
            applied_migrations = []
            for migration in reversed(self.migrations):
                if self._migration_exists(conn, migration.version):
                    applied_migrations.append(migration)
            
            rollback_count = 0
            for migration in applied_migrations:
                if migration.version <= target_version:
                    break
                
                if not migration.down_sql.strip():
                    logger.warning(f"No rollback SQL for migration {migration.version}, skipping...")
                    continue
                
                logger.info(f"Rolling back migration {migration.version}: {migration.name}")
                
                try:
                    with conn.cursor() as cursor:
                        cursor.execute(migration.down_sql)
                    
                    self._remove_migration_record(conn, migration.version)
                    rollback_count += 1
                    logger.info(f"Successfully rolled back migration {migration.version}")
                    
                except psycopg2.Error as e:
                    logger.error(f"Failed to rollback migration {migration.version}: {e}")
                    return False
            
            logger.info(f"Rollback complete. Rolled back {rollback_count} migrations.")
            return True
            
        except Exception as e:
            logger.error(f"Rollback failed: {e}")
            return False
        finally:
            if 'conn' in locals():
                conn.close()
    
    def get_migration_status(self) -> List[Dict[str, any]]:
        """
        Get the status of all migrations.
        
        Returns:
            List of migration status dictionaries
        """
        try:
            conn = self._get_connection()
            status = []
            
            for migration in self.migrations:
                is_applied = self._migration_exists(conn, migration.version)
                integrity_ok = self._validate_migration_integrity(conn, migration) if is_applied else True
                
                status.append({
                    'version': migration.version,
                    'name': migration.name,
                    'applied': is_applied,
                    'integrity_ok': integrity_ok,
                    'checksum': migration.checksum
                })
            
            return status
            
        except Exception as e:
            logger.error(f"Failed to get migration status: {e}")
            return []
        finally:
            if 'conn' in locals():
                conn.close()
    
    def validate_schema(self) -> Tuple[bool, List[str]]:
        """
        Validate that the current database schema matches expectations.
        
        Returns:
            Tuple of (is_valid, list_of_issues)
        """
        issues = []
        
        try:
            conn = self._get_connection()
            
            # Check if agent_reports table exists
            with conn.cursor() as cursor:
                cursor.execute("""
                    SELECT EXISTS (
                        SELECT FROM information_schema.tables 
                        WHERE table_name = 'agent_reports'
                    )
                """)
                
                if not cursor.fetchone()[0]:
                    issues.append("agent_reports table does not exist")
                    return False, issues
            
            # Validate table structure
            expected_columns = {
                'id': 'uuid',
                'session_id': 'character varying',
                'ticker': 'character varying',
                'analysis_date': 'date',
                'created_at': 'timestamp with time zone',
                'updated_at': 'timestamp with time zone',
                'market_analyst_report': 'text',
                'news_analyst_report': 'text',
                'fundamentals_analyst_report': 'text',
                'social_analyst_report': 'text',
                'bull_researcher_report': 'text',
                'bear_researcher_report': 'text',
                'research_manager_report': 'text',
                'trader_report': 'text',
                'risky_analyst_report': 'text',
                'neutral_analyst_report': 'text',
                'safe_analyst_report': 'text',
                'portfolio_manager_report': 'text',
                'final_decision': 'text',
                'final_analysis': 'text',
                'recommendation': 'character varying'
            }
            
            with conn.cursor() as cursor:
                cursor.execute(SCHEMA_VALIDATION_QUERIES[0])
                actual_columns = {row[0]: row[1] for row in cursor.fetchall()}
            
            for col_name, expected_type in expected_columns.items():
                if col_name not in actual_columns:
                    issues.append(f"Missing column: {col_name}")
                elif not actual_columns[col_name].startswith(expected_type):
                    issues.append(f"Column {col_name} has wrong type: expected {expected_type}, got {actual_columns[col_name]}")
            
            # Check for required indexes
            expected_indexes = [
                'idx_agent_reports_session_id',
                'idx_agent_reports_ticker_date',
                'idx_agent_reports_ticker',
                'idx_agent_reports_date',
                'idx_agent_reports_created_at'
            ]
            
            with conn.cursor() as cursor:
                cursor.execute(SCHEMA_VALIDATION_QUERIES[1])
                actual_indexes = [row[0] for row in cursor.fetchall()]
            
            for index_name in expected_indexes:
                if index_name not in actual_indexes:
                    issues.append(f"Missing index: {index_name}")
            
            return len(issues) == 0, issues
            
        except Exception as e:
            issues.append(f"Schema validation failed: {e}")
            return False, issues
        finally:
            if 'conn' in locals():
                conn.close()


def run_migrations(config: NeonConfig, target_version: Optional[str] = None) -> bool:
    """
    Convenience function to run migrations.
    
    Args:
        config: Database configuration
        target_version: Target version to migrate to (None for latest)
        
    Returns:
        True if successful, False otherwise
    """
    runner = MigrationRunner(config)
    return runner.migrate_up(target_version)


def rollback_migrations(config: NeonConfig, target_version: str) -> bool:
    """
    Convenience function to rollback migrations.
    
    Args:
        config: Database configuration
        target_version: Target version to rollback to
        
    Returns:
        True if successful, False otherwise
    """
    runner = MigrationRunner(config)
    return runner.migrate_down(target_version)