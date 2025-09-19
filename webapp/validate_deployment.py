#!/usr/bin/env python3
"""
Railway Deployment Validation Script

This script validates that the TradingAgents application is properly deployed
and configured on Railway. It tests database connectivity, API service availability,
and verifies all application endpoints respond correctly.

Usage:
    python validate_deployment.py [--base-url URL] [--timeout SECONDS]
"""

import asyncio
import json
import os
import sys
import time
from typing import Dict, List, Optional, Tuple
import argparse
import logging
from datetime import datetime

# Third-party imports
import requests
import psycopg2
from psycopg2 import sql
import websockets
from urllib.parse import urlparse

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('deployment_validation.log')
    ]
)
logger = logging.getLogger(__name__)


class DeploymentValidator:
    """Validates Railway deployment configuration and functionality."""
    
    def __init__(self, base_url: str = None, timeout: int = 30):
        self.base_url = base_url or os.getenv('RAILWAY_URL', 'http://localhost:8001')
        self.timeout = timeout
        self.results = {
            'timestamp': datetime.now().isoformat(),
            'base_url': self.base_url,
            'tests': {},
            'summary': {
                'total': 0,
                'passed': 0,
                'failed': 0,
                'warnings': 0
            }
        }
        
    def log_test_result(self, test_name: str, passed: bool, message: str, details: Dict = None):
        """Log test result and update summary."""
        status = 'PASS' if passed else 'FAIL'
        logger.info(f"{test_name}: {status} - {message}")
        
        self.results['tests'][test_name] = {
            'status': status,
            'message': message,
            'details': details or {}
        }
        
        self.results['summary']['total'] += 1
        if passed:
            self.results['summary']['passed'] += 1
        else:
            self.results['summary']['failed'] += 1
    
    def log_warning(self, test_name: str, message: str, details: Dict = None):
        """Log warning result."""
        logger.warning(f"{test_name}: WARNING - {message}")
        
        self.results['tests'][test_name] = {
            'status': 'WARNING',
            'message': message,
            'details': details or {}
        }
        
        self.results['summary']['total'] += 1
        self.results['summary']['warnings'] += 1

    def validate_environment_variables(self) -> bool:
        """Validate required environment variables are present."""
        logger.info("Validating environment variables...")
        
        required_vars = [
            'OPENAI_API_KEY',
            'FINNHUB_API_KEY', 
            'NEON_DATABASE_URL'
        ]
        
        railway_vars = [
            'PORT',
            'RAILWAY_ENVIRONMENT'
        ]
        
        missing_required = []
        missing_railway = []
        
        for var in required_vars:
            if not os.getenv(var):
                missing_required.append(var)
        
        for var in railway_vars:
            if not os.getenv(var):
                missing_railway.append(var)
        
        if missing_required:
            self.log_test_result(
                'environment_variables',
                False,
                f"Missing required environment variables: {', '.join(missing_required)}",
                {'missing_required': missing_required, 'missing_railway': missing_railway}
            )
            return False
        
        if missing_railway:
            self.log_warning(
                'railway_environment_variables',
                f"Missing Railway-specific variables: {', '.join(missing_railway)}",
                {'missing_railway': missing_railway}
            )
        
        self.log_test_result(
            'environment_variables',
            True,
            "All required environment variables are present",
            {'checked_vars': required_vars + railway_vars}
        )
        return True

    def test_database_connectivity(self) -> bool:
        """Test database connectivity and basic operations."""
        logger.info("Testing database connectivity...")
        
        database_url = os.getenv('NEON_DATABASE_URL')
        if not database_url:
            self.log_test_result(
                'database_connectivity',
                False,
                "NEON_DATABASE_URL environment variable not set"
            )
            return False
        
        try:
            # Test connection
            conn = psycopg2.connect(database_url)
            cursor = conn.cursor()
            
            # Test basic query
            cursor.execute("SELECT version();")
            version = cursor.fetchone()[0]
            
            # Test table access (if tables exist)
            cursor.execute("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public'
            """)
            tables = cursor.fetchall()
            
            cursor.close()
            conn.close()
            
            self.log_test_result(
                'database_connectivity',
                True,
                "Database connection successful",
                {
                    'postgres_version': version,
                    'table_count': len(tables),
                    'tables': [table[0] for table in tables]
                }
            )
            return True
            
        except Exception as e:
            self.log_test_result(
                'database_connectivity',
                False,
                f"Database connection failed: {str(e)}",
                {'error_type': type(e).__name__}
            )
            return False

    def test_api_service_availability(self) -> bool:
        """Test external API service availability."""
        logger.info("Testing API service availability...")
        
        api_tests = []
        
        # Test OpenAI API
        openai_key = os.getenv('OPENAI_API_KEY')
        if openai_key:
            try:
                headers = {'Authorization': f'Bearer {openai_key}'}
                response = requests.get(
                    'https://api.openai.com/v1/models',
                    headers=headers,
                    timeout=self.timeout
                )
                api_tests.append({
                    'service': 'OpenAI',
                    'status': response.status_code == 200,
                    'response_time': response.elapsed.total_seconds()
                })
            except Exception as e:
                api_tests.append({
                    'service': 'OpenAI',
                    'status': False,
                    'error': str(e)
                })
        
        # Test Finnhub API
        finnhub_key = os.getenv('FINNHUB_API_KEY')
        if finnhub_key:
            try:
                response = requests.get(
                    f'https://finnhub.io/api/v1/quote?symbol=AAPL&token={finnhub_key}',
                    timeout=self.timeout
                )
                api_tests.append({
                    'service': 'Finnhub',
                    'status': response.status_code == 200,
                    'response_time': response.elapsed.total_seconds()
                })
            except Exception as e:
                api_tests.append({
                    'service': 'Finnhub',
                    'status': False,
                    'error': str(e)
                })
        
        # Evaluate results
        successful_apis = [test for test in api_tests if test['status']]
        failed_apis = [test for test in api_tests if not test['status']]
        
        if failed_apis:
            self.log_test_result(
                'api_service_availability',
                False,
                f"Some API services failed: {[api['service'] for api in failed_apis]}",
                {'successful': successful_apis, 'failed': failed_apis}
            )
            return False
        
        self.log_test_result(
            'api_service_availability',
            True,
            f"All API services available ({len(successful_apis)} tested)",
            {'services': successful_apis}
        )
        return True

    def test_application_endpoints(self) -> bool:
        """Test all application endpoints respond correctly."""
        logger.info("Testing application endpoints...")
        
        endpoints = [
            {'path': '/', 'method': 'GET', 'expected_status': 200, 'description': 'Main page'},
            {'path': '/health', 'method': 'GET', 'expected_status': 200, 'description': 'Health check'},
            {'path': '/api/analyze', 'method': 'POST', 'expected_status': [200, 422], 'description': 'Analysis endpoint'},
            {'path': '/static/style.css', 'method': 'GET', 'expected_status': 200, 'description': 'Static CSS'},
            {'path': '/static/app.js', 'method': 'GET', 'expected_status': 200, 'description': 'Static JS'},
        ]
        
        endpoint_results = []
        
        for endpoint in endpoints:
            try:
                if endpoint['method'] == 'GET':
                    response = requests.get(
                        f"{self.base_url}{endpoint['path']}",
                        timeout=self.timeout
                    )
                elif endpoint['method'] == 'POST':
                    # Send minimal valid payload for POST endpoints
                    response = requests.post(
                        f"{self.base_url}{endpoint['path']}",
                        json={'symbol': 'AAPL'},  # Basic test payload
                        timeout=self.timeout
                    )
                
                expected_status = endpoint['expected_status']
                if isinstance(expected_status, list):
                    status_ok = response.status_code in expected_status
                else:
                    status_ok = response.status_code == expected_status
                
                endpoint_results.append({
                    'path': endpoint['path'],
                    'method': endpoint['method'],
                    'description': endpoint['description'],
                    'status_code': response.status_code,
                    'expected_status': expected_status,
                    'success': status_ok,
                    'response_time': response.elapsed.total_seconds(),
                    'content_length': len(response.content)
                })
                
            except Exception as e:
                endpoint_results.append({
                    'path': endpoint['path'],
                    'method': endpoint['method'],
                    'description': endpoint['description'],
                    'success': False,
                    'error': str(e)
                })
        
        # Evaluate results
        successful_endpoints = [ep for ep in endpoint_results if ep.get('success', False)]
        failed_endpoints = [ep for ep in endpoint_results if not ep.get('success', False)]
        
        if failed_endpoints:
            self.log_test_result(
                'application_endpoints',
                False,
                f"Some endpoints failed: {[ep['path'] for ep in failed_endpoints]}",
                {'successful': successful_endpoints, 'failed': failed_endpoints}
            )
            return False
        
        self.log_test_result(
            'application_endpoints',
            True,
            f"All endpoints responding correctly ({len(successful_endpoints)} tested)",
            {'endpoints': endpoint_results}
        )
        return True

    async def test_websocket_connectivity(self) -> bool:
        """Test WebSocket connectivity."""
        logger.info("Testing WebSocket connectivity...")
        
        # Convert HTTP URL to WebSocket URL
        ws_url = self.base_url.replace('http://', 'ws://').replace('https://', 'wss://')
        ws_url += '/ws'
        
        try:
            async with websockets.connect(ws_url, timeout=self.timeout) as websocket:
                # Send test message
                test_message = json.dumps({'type': 'ping', 'data': 'test'})
                await websocket.send(test_message)
                
                # Wait for response (with timeout)
                try:
                    response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                    self.log_test_result(
                        'websocket_connectivity',
                        True,
                        "WebSocket connection successful",
                        {'test_message': test_message, 'response': response}
                    )
                    return True
                except asyncio.TimeoutError:
                    self.log_warning(
                        'websocket_connectivity',
                        "WebSocket connected but no response received",
                        {'test_message': test_message}
                    )
                    return True  # Connection works, just no response
                    
        except Exception as e:
            self.log_test_result(
                'websocket_connectivity',
                False,
                f"WebSocket connection failed: {str(e)}",
                {'error_type': type(e).__name__, 'ws_url': ws_url}
            )
            return False

    def test_railway_configuration(self) -> bool:
        """Test Railway-specific configuration."""
        logger.info("Testing Railway configuration...")
        
        config_checks = []
        
        # Check if running on Railway
        railway_env = os.getenv('RAILWAY_ENVIRONMENT')
        if railway_env:
            config_checks.append({
                'check': 'Railway Environment',
                'status': True,
                'value': railway_env
            })
        else:
            config_checks.append({
                'check': 'Railway Environment',
                'status': False,
                'message': 'Not running on Railway (RAILWAY_ENVIRONMENT not set)'
            })
        
        # Check PORT configuration
        port = os.getenv('PORT')
        if port:
            try:
                port_int = int(port)
                config_checks.append({
                    'check': 'PORT Configuration',
                    'status': True,
                    'value': port_int
                })
            except ValueError:
                config_checks.append({
                    'check': 'PORT Configuration',
                    'status': False,
                    'message': f'Invalid PORT value: {port}'
                })
        else:
            config_checks.append({
                'check': 'PORT Configuration',
                'status': False,
                'message': 'PORT environment variable not set'
            })
        
        # Check for Railway configuration files
        config_files = ['railway.toml', 'Procfile']
        for config_file in config_files:
            if os.path.exists(config_file):
                config_checks.append({
                    'check': f'{config_file} exists',
                    'status': True,
                    'path': config_file
                })
            else:
                config_checks.append({
                    'check': f'{config_file} exists',
                    'status': False,
                    'message': f'Configuration file not found: {config_file}'
                })
        
        # Evaluate results
        failed_checks = [check for check in config_checks if not check['status']]
        
        if failed_checks:
            self.log_test_result(
                'railway_configuration',
                False,
                f"Railway configuration issues found: {len(failed_checks)}",
                {'checks': config_checks, 'failed': failed_checks}
            )
            return False
        
        self.log_test_result(
            'railway_configuration',
            True,
            "Railway configuration validated successfully",
            {'checks': config_checks}
        )
        return True

    async def run_all_tests(self) -> Dict:
        """Run all validation tests."""
        logger.info(f"Starting deployment validation for {self.base_url}")
        
        # Run synchronous tests
        tests = [
            self.validate_environment_variables,
            self.test_database_connectivity,
            self.test_api_service_availability,
            self.test_application_endpoints,
            self.test_railway_configuration
        ]
        
        for test in tests:
            try:
                test()
            except Exception as e:
                test_name = test.__name__
                self.log_test_result(
                    test_name,
                    False,
                    f"Test failed with exception: {str(e)}",
                    {'error_type': type(e).__name__}
                )
        
        # Run asynchronous tests
        try:
            await self.test_websocket_connectivity()
        except Exception as e:
            self.log_test_result(
                'websocket_connectivity',
                False,
                f"WebSocket test failed with exception: {str(e)}",
                {'error_type': type(e).__name__}
            )
        
        # Generate summary
        summary = self.results['summary']
        success_rate = (summary['passed'] / summary['total']) * 100 if summary['total'] > 0 else 0
        
        logger.info(f"Validation complete: {summary['passed']}/{summary['total']} tests passed ({success_rate:.1f}%)")
        if summary['failed'] > 0:
            logger.error(f"{summary['failed']} tests failed")
        if summary['warnings'] > 0:
            logger.warning(f"{summary['warnings']} warnings")
        
        return self.results

    def save_results(self, filename: str = None):
        """Save validation results to JSON file."""
        if not filename:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f'deployment_validation_{timestamp}.json'
        
        with open(filename, 'w') as f:
            json.dump(self.results, f, indent=2)
        
        logger.info(f"Results saved to {filename}")


async def main():
    """Main function to run deployment validation."""
    parser = argparse.ArgumentParser(description='Validate Railway deployment')
    parser.add_argument('--base-url', help='Base URL of the deployed application')
    parser.add_argument('--timeout', type=int, default=30, help='Request timeout in seconds')
    parser.add_argument('--output', help='Output file for results (JSON)')
    parser.add_argument('--verbose', '-v', action='store_true', help='Verbose logging')
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Create validator
    validator = DeploymentValidator(
        base_url=args.base_url,
        timeout=args.timeout
    )
    
    # Run validation
    results = await validator.run_all_tests()
    
    # Save results
    validator.save_results(args.output)
    
    # Exit with appropriate code
    if results['summary']['failed'] > 0:
        sys.exit(1)
    else:
        sys.exit(0)


if __name__ == '__main__':
    asyncio.run(main())