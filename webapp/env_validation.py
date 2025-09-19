"""
Environment Variable Validation Module for Railway Deployment

This module provides comprehensive validation of environment variables required
for the TradingAgents web application to run properly in Railway environment.
"""

import os
import logging
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class ValidationLevel(Enum):
    """Validation levels for environment variables"""
    REQUIRED = "required"
    OPTIONAL = "optional"
    CONDITIONAL = "conditional"


@dataclass
class EnvVarConfig:
    """Configuration for an environment variable"""
    name: str
    level: ValidationLevel
    description: str
    default_value: Optional[str] = None
    validation_func: Optional[callable] = None
    depends_on: Optional[str] = None  # For conditional variables


class EnvironmentValidator:
    """Validates environment variables for Railway deployment"""
    
    def __init__(self):
        self.validation_errors: List[str] = []
        self.validation_warnings: List[str] = []
        self.validated_vars: Dict[str, str] = {}
        
        # Define all environment variables with their validation rules
        self.env_vars = [
            # Required API Keys
            EnvVarConfig(
                name="OPENAI_API_KEY",
                level=ValidationLevel.REQUIRED,
                description="OpenAI API key for LLM agents (required for analysis)",
                validation_func=self._validate_openai_key
            ),
            EnvVarConfig(
                name="FINNHUB_API_KEY", 
                level=ValidationLevel.REQUIRED,
                description="Finnhub API key for financial data (free tier available)",
                validation_func=self._validate_finnhub_key
            ),
            
            # Required Database Configuration
            EnvVarConfig(
                name="NEON_DATABASE_URL",
                level=ValidationLevel.REQUIRED,
                description="PostgreSQL database connection URL for Neon database",
                validation_func=self._validate_database_url
            ),
            
            # Optional Database Configuration
            EnvVarConfig(
                name="DB_POOL_SIZE",
                level=ValidationLevel.OPTIONAL,
                description="Database connection pool size",
                default_value="10",
                validation_func=self._validate_positive_integer
            ),
            EnvVarConfig(
                name="DB_SSL_MODE",
                level=ValidationLevel.OPTIONAL,
                description="Database SSL mode (require, prefer, disable)",
                default_value="require",
                validation_func=self._validate_ssl_mode
            ),
            
            # Optional Additional LLM Provider Keys
            EnvVarConfig(
                name="ANTHROPIC_API_KEY",
                level=ValidationLevel.OPTIONAL,
                description="Anthropic API key for Claude models (optional)"
            ),
            EnvVarConfig(
                name="GOOGLE_API_KEY",
                level=ValidationLevel.OPTIONAL,
                description="Google API key for Gemini models (optional)"
            ),
            
            # Railway-Specific Variables (provided by Railway)
            EnvVarConfig(
                name="PORT",
                level=ValidationLevel.CONDITIONAL,
                description="Port number for the web server (provided by Railway)",
                default_value="8001",
                validation_func=self._validate_port,
                depends_on="RAILWAY_ENVIRONMENT"
            ),
            EnvVarConfig(
                name="RAILWAY_ENVIRONMENT",
                level=ValidationLevel.OPTIONAL,
                description="Railway deployment environment (production, staging, etc.)"
            ),
            EnvVarConfig(
                name="RAILWAY_PROJECT_ID",
                level=ValidationLevel.OPTIONAL,
                description="Railway project identifier"
            ),
            EnvVarConfig(
                name="RAILWAY_PUBLIC_DOMAIN",
                level=ValidationLevel.OPTIONAL,
                description="Railway public domain for CORS configuration"
            ),
            
            # Optional Application Configuration
            EnvVarConfig(
                name="LOG_LEVEL",
                level=ValidationLevel.OPTIONAL,
                description="Logging level (DEBUG, INFO, WARNING, ERROR)",
                default_value="INFO",
                validation_func=self._validate_log_level
            ),
            EnvVarConfig(
                name="TRADINGAGENTS_DEBUG",
                level=ValidationLevel.OPTIONAL,
                description="Enable debug mode for TradingAgents (true/false)",
                default_value="false",
                validation_func=self._validate_boolean
            ),
            EnvVarConfig(
                name="TRADINGAGENTS_RESULTS_DIR",
                level=ValidationLevel.OPTIONAL,
                description="Directory for storing analysis results",
                default_value="./results"
            )
        ]
    
    def validate_all(self) -> Tuple[bool, Dict[str, any]]:
        """
        Validate all environment variables.
        
        Returns:
            Tuple of (is_valid, validation_report)
        """
        logger.info("🔍 Starting environment variable validation...")
        
        self.validation_errors.clear()
        self.validation_warnings.clear()
        self.validated_vars.clear()
        
        # Check Railway environment
        is_railway = bool(os.environ.get("RAILWAY_ENVIRONMENT"))
        logger.info(f"Environment: {'Railway' if is_railway else 'Local Development'}")
        
        # Validate each environment variable
        for env_var in self.env_vars:
            self._validate_single_var(env_var, is_railway)
        
        # Generate validation report
        is_valid = len(self.validation_errors) == 0
        report = {
            "valid": is_valid,
            "environment": "railway" if is_railway else "local",
            "validated_vars": self.validated_vars.copy(),
            "errors": self.validation_errors.copy(),
            "warnings": self.validation_warnings.copy(),
            "summary": self._generate_summary()
        }
        
        # Log validation results
        self._log_validation_results(is_valid, report)
        
        return is_valid, report
    
    def _validate_single_var(self, env_var: EnvVarConfig, is_railway: bool):
        """Validate a single environment variable"""
        value = os.environ.get(env_var.name)
        
        # Handle conditional variables
        if env_var.level == ValidationLevel.CONDITIONAL:
            if env_var.depends_on and not os.environ.get(env_var.depends_on):
                # Dependency not met, skip validation
                return
        
        # Check if required variable is missing
        if env_var.level == ValidationLevel.REQUIRED and not value:
            self.validation_errors.append(
                f"❌ {env_var.name}: Required environment variable is missing. "
                f"{env_var.description}"
            )
            return
        
        # Use default value if not set and default is available
        if not value and env_var.default_value is not None:
            value = env_var.default_value
            self.validation_warnings.append(
                f"⚠️ {env_var.name}: Using default value '{value}'. "
                f"{env_var.description}"
            )
        
        # Skip validation if optional and not set
        if not value and env_var.level == ValidationLevel.OPTIONAL:
            return
        
        # Run custom validation if provided
        if value and env_var.validation_func:
            try:
                is_valid, error_msg = env_var.validation_func(value)
                if not is_valid:
                    self.validation_errors.append(
                        f"❌ {env_var.name}: {error_msg}"
                    )
                    return
            except Exception as e:
                self.validation_errors.append(
                    f"❌ {env_var.name}: Validation error - {str(e)}"
                )
                return
        
        # Store validated value
        if value:
            self.validated_vars[env_var.name] = value
            logger.debug(f"✅ {env_var.name}: Validated successfully")
    
    def _validate_openai_key(self, value: str) -> Tuple[bool, str]:
        """Validate OpenAI API key format"""
        if not value.startswith("sk-"):
            return False, "OpenAI API key must start with 'sk-'"
        if len(value) < 20:
            return False, "OpenAI API key appears to be too short"
        return True, ""
    
    def _validate_finnhub_key(self, value: str) -> Tuple[bool, str]:
        """Validate Finnhub API key format"""
        if len(value) < 10:
            return False, "Finnhub API key appears to be too short"
        # Finnhub keys are typically alphanumeric
        if not value.replace("_", "").isalnum():
            return False, "Finnhub API key should be alphanumeric"
        return True, ""
    
    def _validate_database_url(self, value: str) -> Tuple[bool, str]:
        """Validate database URL format"""
        if not value.startswith("postgresql://"):
            return False, "Database URL must start with 'postgresql://'"
        if "@" not in value:
            return False, "Database URL must contain credentials"
        if ".neon.tech" not in value and "localhost" not in value:
            return False, "Database URL should be a Neon PostgreSQL URL or localhost"
        return True, ""
    
    def _validate_positive_integer(self, value: str) -> Tuple[bool, str]:
        """Validate positive integer value"""
        try:
            int_value = int(value)
            if int_value <= 0:
                return False, "Value must be a positive integer"
            return True, ""
        except ValueError:
            return False, "Value must be a valid integer"
    
    def _validate_ssl_mode(self, value: str) -> Tuple[bool, str]:
        """Validate SSL mode value"""
        valid_modes = ["require", "prefer", "disable", "allow"]
        if value not in valid_modes:
            return False, f"SSL mode must be one of: {', '.join(valid_modes)}"
        return True, ""
    
    def _validate_port(self, value: str) -> Tuple[bool, str]:
        """Validate port number"""
        try:
            port = int(value)
            if port < 1 or port > 65535:
                return False, "Port must be between 1 and 65535"
            return True, ""
        except ValueError:
            return False, "Port must be a valid integer"
    
    def _validate_log_level(self, value: str) -> Tuple[bool, str]:
        """Validate log level value"""
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if value.upper() not in valid_levels:
            return False, f"Log level must be one of: {', '.join(valid_levels)}"
        return True, ""
    
    def _validate_boolean(self, value: str) -> Tuple[bool, str]:
        """Validate boolean value"""
        valid_values = ["true", "false", "1", "0", "yes", "no"]
        if value.lower() not in valid_values:
            return False, f"Boolean value must be one of: {', '.join(valid_values)}"
        return True, ""
    
    def _generate_summary(self) -> Dict[str, any]:
        """Generate validation summary"""
        total_vars = len(self.env_vars)
        validated_count = len(self.validated_vars)
        error_count = len(self.validation_errors)
        warning_count = len(self.validation_warnings)
        
        return {
            "total_variables": total_vars,
            "validated_variables": validated_count,
            "errors": error_count,
            "warnings": warning_count,
            "status": "valid" if error_count == 0 else "invalid"
        }
    
    def _log_validation_results(self, is_valid: bool, report: Dict[str, any]):
        """Log validation results with appropriate level"""
        summary = report["summary"]
        
        if is_valid:
            logger.info(
                f"✅ Environment validation successful: "
                f"{summary['validated_variables']}/{summary['total_variables']} variables validated"
            )
            if summary['warnings'] > 0:
                logger.info(f"⚠️ {summary['warnings']} warnings found")
        else:
            logger.error(
                f"❌ Environment validation failed: "
                f"{summary['errors']} errors, {summary['warnings']} warnings"
            )
        
        # Log individual errors and warnings
        for error in self.validation_errors:
            logger.error(error)
        
        for warning in self.validation_warnings:
            logger.warning(warning)
    
    def get_missing_required_vars(self) -> List[str]:
        """Get list of missing required environment variables"""
        missing = []
        for env_var in self.env_vars:
            if env_var.level == ValidationLevel.REQUIRED:
                if not os.environ.get(env_var.name):
                    missing.append(env_var.name)
        return missing
    
    def get_validation_errors_for_display(self) -> List[str]:
        """Get formatted validation errors for display to users"""
        return [error.replace("❌ ", "").replace("⚠️ ", "") for error in self.validation_errors]


def validate_environment() -> Tuple[bool, Dict[str, any]]:
    """
    Convenience function to validate environment variables.
    
    Returns:
        Tuple of (is_valid, validation_report)
    """
    validator = EnvironmentValidator()
    return validator.validate_all()


def check_critical_services() -> Dict[str, bool]:
    """
    Check if critical services are properly configured.
    
    Returns:
        Dictionary with service availability status
    """
    services = {
        "openai": bool(os.environ.get("OPENAI_API_KEY")),
        "finnhub": bool(os.environ.get("FINNHUB_API_KEY")),
        "database": bool(os.environ.get("NEON_DATABASE_URL")),
        "anthropic": bool(os.environ.get("ANTHROPIC_API_KEY")),
        "google": bool(os.environ.get("GOOGLE_API_KEY"))
    }
    
    logger.info("🔍 Critical services status:")
    for service, available in services.items():
        status = "✅ Available" if available else "❌ Not configured"
        logger.info(f"  {service}: {status}")
    
    return services