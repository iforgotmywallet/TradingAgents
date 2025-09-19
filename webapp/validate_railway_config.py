#!/usr/bin/env python3
"""
Railway Configuration Validation Script

This script validates the Railway deployment configuration without requiring a running server.
It checks:
- Configuration files
- Environment variables
- Code structure
- Dependencies
"""

import json
import os
import sys
from pathlib import Path
from typing import Dict, List, Any

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))

class RailwayConfigValidator:
    def __init__(self):
        self.webapp_dir = Path(__file__).parent
        self.root_dir = self.webapp_dir.parent
        self.results = {}
        
    def validate_railway_files(self) -> Dict[str, Any]:
        """Validate Railway configuration files"""
        print("🔍 Validating Railway configuration files...")
        
        results = {}
        
        # Check railway.toml
        railway_toml = self.webapp_dir / "railway.toml"
        if railway_toml.exists():
            print("   ✅ railway.toml exists")
            try:
                content = railway_toml.read_text()
                results["railway_toml"] = {
                    "exists": True,
                    "has_build_section": "[build]" in content,
                    "has_deploy_section": "[deploy]" in content,
                    "has_healthcheck": "healthcheckPath" in content,
                    "python_version": "python" in content.lower(),
                }
                
                if results["railway_toml"]["has_healthcheck"]:
                    print("   ✅ Health check configured")
                else:
                    print("   ⚠️ Health check not configured")
                    
            except Exception as e:
                results["railway_toml"] = {"exists": True, "error": str(e)}
                print(f"   ❌ Error reading railway.toml: {e}")
        else:
            results["railway_toml"] = {"exists": False}
            print("   ❌ railway.toml not found")
        
        # Check Procfile
        procfile = self.webapp_dir / "Procfile"
        if procfile.exists():
            print("   ✅ Procfile exists")
            try:
                content = procfile.read_text()
                results["procfile"] = {
                    "exists": True,
                    "has_web_process": content.startswith("web:"),
                    "uses_gunicorn": "gunicorn" in content,
                    "uses_uvicorn": "uvicorn" in content,
                    "binds_to_port": "$PORT" in content,
                }
                
                if results["procfile"]["binds_to_port"]:
                    print("   ✅ Procfile binds to $PORT")
                else:
                    print("   ⚠️ Procfile doesn't bind to $PORT")
                    
            except Exception as e:
                results["procfile"] = {"exists": True, "error": str(e)}
                print(f"   ❌ Error reading Procfile: {e}")
        else:
            results["procfile"] = {"exists": False}
            print("   ❌ Procfile not found")
        
        return results
    
    def validate_app_structure(self) -> Dict[str, Any]:
        """Validate application structure"""
        print("🔍 Validating application structure...")
        
        results = {}
        
        # Check main app file
        app_py = self.webapp_dir / "app.py"
        if app_py.exists():
            print("   ✅ app.py exists")
            try:
                content = app_py.read_text()
                results["app_py"] = {
                    "exists": True,
                    "has_fastapi": "FastAPI" in content,
                    "has_cors": "CORSMiddleware" in content,
                    "has_websocket": "@app.websocket" in content,
                    "has_railway_proxy": "RailwayProxyMiddleware" in content,
                    "has_health_endpoint": "/health" in content,
                    "has_static_mount": "StaticFiles" in content,
                }
                
                for feature, present in results["app_py"].items():
                    if feature != "exists" and present:
                        print(f"   ✅ {feature.replace('_', ' ').title()}")
                    elif feature != "exists":
                        print(f"   ❌ {feature.replace('_', ' ').title()} missing")
                        
            except Exception as e:
                results["app_py"] = {"exists": True, "error": str(e)}
                print(f"   ❌ Error reading app.py: {e}")
        else:
            results["app_py"] = {"exists": False}
            print("   ❌ app.py not found")
        
        # Check static files
        static_dir = self.webapp_dir / "static"
        if static_dir.exists():
            print("   ✅ static directory exists")
            static_files = list(static_dir.glob("*"))
            results["static_files"] = {
                "exists": True,
                "files": [f.name for f in static_files],
                "has_index": "index.html" in [f.name for f in static_files],
                "has_js": "app.js" in [f.name for f in static_files],
                "has_css": "style.css" in [f.name for f in static_files],
            }
            
            print(f"   📁 Found {len(static_files)} static files")
            for file in static_files:
                print(f"      - {file.name}")
        else:
            results["static_files"] = {"exists": False}
            print("   ❌ static directory not found")
        
        return results
    
    def validate_dependencies(self) -> Dict[str, Any]:
        """Validate dependencies"""
        print("🔍 Validating dependencies...")
        
        results = {}
        
        # Check requirements.txt
        requirements_txt = self.webapp_dir / "requirements.txt"
        if requirements_txt.exists():
            print("   ✅ requirements.txt exists")
            try:
                content = requirements_txt.read_text()
                lines = [line.strip() for line in content.split('\n') if line.strip() and not line.startswith('#')]
                
                required_packages = [
                    "fastapi", "uvicorn", "websockets", "pydantic",
                    "python-dotenv", "aiohttp", "psycopg2-binary",
                    "gunicorn"
                ]
                
                found_packages = []
                for line in lines:
                    package_name = line.split('>=')[0].split('==')[0].split('[')[0]
                    found_packages.append(package_name.lower())
                
                results["requirements"] = {
                    "exists": True,
                    "total_packages": len(lines),
                    "required_packages": {},
                }
                
                for package in required_packages:
                    is_present = any(package.lower() in found.lower() for found in found_packages)
                    results["requirements"]["required_packages"][package] = is_present
                    
                    if is_present:
                        print(f"   ✅ {package}")
                    else:
                        print(f"   ❌ {package} missing")
                        
            except Exception as e:
                results["requirements"] = {"exists": True, "error": str(e)}
                print(f"   ❌ Error reading requirements.txt: {e}")
        else:
            results["requirements"] = {"exists": False}
            print("   ❌ requirements.txt not found")
        
        return results
    
    def validate_cors_config(self) -> Dict[str, Any]:
        """Validate CORS configuration in code"""
        print("🔍 Validating CORS configuration...")
        
        results = {}
        
        app_py = self.webapp_dir / "app.py"
        if app_py.exists():
            try:
                content = app_py.read_text()
                
                results["cors_config"] = {
                    "has_cors_middleware": "CORSMiddleware" in content,
                    "has_railway_domain_check": "RAILWAY_PUBLIC_DOMAIN" in content,
                    "has_dynamic_origins": "get_allowed_origins" in content,
                    "has_proxy_middleware": "RailwayProxyMiddleware" in content,
                    "handles_forwarded_headers": "x-forwarded-proto" in content.lower(),
                }
                
                for feature, present in results["cors_config"].items():
                    if present:
                        print(f"   ✅ {feature.replace('_', ' ').title()}")
                    else:
                        print(f"   ❌ {feature.replace('_', ' ').title()} missing")
                        
            except Exception as e:
                results["cors_config"] = {"error": str(e)}
                print(f"   ❌ Error validating CORS config: {e}")
        else:
            results["cors_config"] = {"error": "app.py not found"}
            print("   ❌ app.py not found")
        
        return results
    
    def validate_websocket_config(self) -> Dict[str, Any]:
        """Validate WebSocket configuration"""
        print("🔍 Validating WebSocket configuration...")
        
        results = {}
        
        # Check server-side WebSocket config
        app_py = self.webapp_dir / "app.py"
        if app_py.exists():
            try:
                content = app_py.read_text()
                
                results["websocket_server"] = {
                    "has_websocket_endpoint": "@app.websocket" in content,
                    "has_connection_manager": "ConnectionManager" in content,
                    "handles_proxy_headers": "x-forwarded-proto" in content.lower() and "websocket" in content.lower(),
                    "has_graceful_shutdown": "shutdown_all_connections" in content,
                }
                
                for feature, present in results["websocket_server"].items():
                    if present:
                        print(f"   ✅ Server: {feature.replace('_', ' ').title()}")
                    else:
                        print(f"   ❌ Server: {feature.replace('_', ' ').title()} missing")
                        
            except Exception as e:
                results["websocket_server"] = {"error": str(e)}
                print(f"   ❌ Error validating server WebSocket config: {e}")
        
        # Check client-side WebSocket config
        app_js = self.webapp_dir / "static" / "app.js"
        if app_js.exists():
            try:
                content = app_js.read_text()
                
                results["websocket_client"] = {
                    "has_websocket_setup": "setupWebSocket" in content,
                    "has_protocol_detection": "wss:" in content and "ws:" in content,
                    "has_reconnection": "reconnect" in content.lower(),
                    "handles_railway_proxy": "railway_proxy" in content.lower(),
                }
                
                for feature, present in results["websocket_client"].items():
                    if present:
                        print(f"   ✅ Client: {feature.replace('_', ' ').title()}")
                    else:
                        print(f"   ❌ Client: {feature.replace('_', ' ').title()} missing")
                        
            except Exception as e:
                results["websocket_client"] = {"error": str(e)}
                print(f"   ❌ Error validating client WebSocket config: {e}")
        else:
            results["websocket_client"] = {"error": "app.js not found"}
            print("   ❌ app.js not found")
        
        return results
    
    def validate_environment_vars(self) -> Dict[str, Any]:
        """Validate environment variable configuration"""
        print("🔍 Validating environment variable configuration...")
        
        results = {}
        
        # Check .env.example
        env_example = self.webapp_dir.parent / ".env.example"
        if env_example.exists():
            print("   ✅ .env.example exists")
            try:
                content = env_example.read_text()
                
                railway_vars = [
                    "PORT", "RAILWAY_ENVIRONMENT", "RAILWAY_PUBLIC_DOMAIN",
                    "RAILWAY_PROJECT_ID", "RAILWAY_STATIC_URL"
                ]
                
                results["env_example"] = {
                    "exists": True,
                    "railway_vars": {},
                }
                
                for var in railway_vars:
                    is_present = var in content
                    results["env_example"]["railway_vars"][var] = is_present
                    
                    if is_present:
                        print(f"   ✅ {var} documented")
                    else:
                        print(f"   ⚠️ {var} not documented")
                        
            except Exception as e:
                results["env_example"] = {"exists": True, "error": str(e)}
                print(f"   ❌ Error reading .env.example: {e}")
        else:
            results["env_example"] = {"exists": False}
            print("   ⚠️ .env.example not found")
        
        # Check current environment
        current_env = {
            "PORT": os.environ.get("PORT"),
            "RAILWAY_ENVIRONMENT": os.environ.get("RAILWAY_ENVIRONMENT"),
            "RAILWAY_PUBLIC_DOMAIN": os.environ.get("RAILWAY_PUBLIC_DOMAIN"),
        }
        
        results["current_env"] = current_env
        
        print("   📋 Current environment:")
        for var, value in current_env.items():
            if value:
                print(f"      ✅ {var}={value}")
            else:
                print(f"      ⚠️ {var} not set")
        
        return results
    
    def run_validation(self) -> bool:
        """Run all validations"""
        print("🚀 Starting Railway configuration validation")
        print("=" * 60)
        
        # Run all validations
        self.results["railway_files"] = self.validate_railway_files()
        self.results["app_structure"] = self.validate_app_structure()
        self.results["dependencies"] = self.validate_dependencies()
        self.results["cors_config"] = self.validate_cors_config()
        self.results["websocket_config"] = self.validate_websocket_config()
        self.results["environment_vars"] = self.validate_environment_vars()
        
        # Calculate score
        total_checks = 0
        passed_checks = 0
        
        def count_checks(data, prefix=""):
            nonlocal total_checks, passed_checks
            
            if isinstance(data, dict):
                for key, value in data.items():
                    if isinstance(value, bool):
                        total_checks += 1
                        if value:
                            passed_checks += 1
                    elif isinstance(value, dict) and "exists" in value:
                        total_checks += 1
                        if value["exists"]:
                            passed_checks += 1
                    elif isinstance(value, dict):
                        count_checks(value, f"{prefix}.{key}" if prefix else key)
        
        count_checks(self.results)
        
        # Print summary
        print("\n" + "=" * 60)
        print("📊 Validation Summary:")
        
        score_percentage = (passed_checks / total_checks * 100) if total_checks > 0 else 0
        
        print(f"🎯 Score: {passed_checks}/{total_checks} checks passed ({score_percentage:.1f}%)")
        
        if score_percentage >= 90:
            print("🎉 Excellent! Railway configuration is ready for deployment.")
            status = True
        elif score_percentage >= 75:
            print("✅ Good! Railway configuration is mostly ready. Address remaining issues.")
            status = True
        elif score_percentage >= 50:
            print("⚠️ Fair. Several configuration issues need to be addressed.")
            status = False
        else:
            print("❌ Poor. Major configuration issues need to be fixed before deployment.")
            status = False
        
        # Save results
        results_file = self.webapp_dir / "railway_config_validation.json"
        with open(results_file, "w") as f:
            json.dump({
                "timestamp": __import__("time").time(),
                "score": {
                    "passed": passed_checks,
                    "total": total_checks,
                    "percentage": score_percentage
                },
                "results": self.results,
                "status": status
            }, f, indent=2)
        
        print(f"\n📄 Detailed results saved to: {results_file}")
        
        return status

def main():
    """Main validation function"""
    validator = RailwayConfigValidator()
    success = validator.run_validation()
    
    return success

if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n⚠️ Validation interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Validation failed with error: {e}")
        sys.exit(1)