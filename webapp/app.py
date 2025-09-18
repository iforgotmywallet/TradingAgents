# Core FastAPI imports - loaded immediately for basic functionality
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import asyncio
import json
import datetime
from pathlib import Path
import os
import sys
import logging
import signal
import atexit
from contextlib import asynccontextmanager

# Load environment variables first
from dotenv import load_dotenv
load_dotenv()

# Add the parent directory to the path to import tradingagents
sys.path.append(str(Path(__file__).parent.parent))

# Global shutdown event for coordinating graceful shutdown
shutdown_event = asyncio.Event()
background_tasks = set()  # Track background tasks for cleanup

# Lazy import cache for heavy modules
_lazy_imports = {}

def get_trading_graph():
    """Lazy import TradingAgentsGraph only when needed"""
    if 'TradingAgentsGraph' not in _lazy_imports:
        try:
            from tradingagents.graph.trading_graph import TradingAgentsGraph
            _lazy_imports['TradingAgentsGraph'] = TradingAgentsGraph
        except ImportError as e:
            logging.error(f"❌ Failed to import TradingAgentsGraph: {e}")
            raise
    return _lazy_imports['TradingAgentsGraph']

def get_default_config():
    """Lazy import DEFAULT_CONFIG only when needed"""
    if 'DEFAULT_CONFIG' not in _lazy_imports:
        try:
            from tradingagents.default_config import DEFAULT_CONFIG
            _lazy_imports['DEFAULT_CONFIG'] = DEFAULT_CONFIG
        except ImportError as e:
            logging.error(f"❌ Failed to import DEFAULT_CONFIG: {e}")
            raise
    return _lazy_imports['DEFAULT_CONFIG']

def get_report_retrieval_classes():
    """Lazy import report retrieval classes only when needed"""
    if 'report_classes' not in _lazy_imports:
        try:
            from tradingagents.storage.report_retrieval import (
                ReportRetrievalService, ReportRetrievalError, 
                ReportNotFoundError, SessionNotFoundError, DatabaseConnectionError
            )
            from tradingagents.storage.neon_config import NeonConfig
            from tradingagents.storage.session_utils import (
                generate_session_id, validate_session_id, 
                get_session_ticker, get_session_date
            )
            from tradingagents.storage.agent_validation import AgentValidationError
            from tradingagents.storage.schema import AgentReportSchema
            
            _lazy_imports['report_classes'] = {
                'ReportRetrievalService': ReportRetrievalService,
                'ReportRetrievalError': ReportRetrievalError,
                'ReportNotFoundError': ReportNotFoundError,
                'SessionNotFoundError': SessionNotFoundError,
                'DatabaseConnectionError': DatabaseConnectionError,
                'NeonConfig': NeonConfig,
                'generate_session_id': generate_session_id,
                'validate_session_id': validate_session_id,
                'get_session_ticker': get_session_ticker,
                'get_session_date': get_session_date,
                'AgentValidationError': AgentValidationError,
                'AgentReportSchema': AgentReportSchema
            }
        except ImportError as e:
            logging.error(f"❌ Failed to import report retrieval classes: {e}")
            raise
    return _lazy_imports['report_classes']

def get_env_validation():
    """Lazy import environment validation only when needed"""
    if 'env_validation' not in _lazy_imports:
        try:
            from env_validation import validate_environment, check_critical_services
            _lazy_imports['env_validation'] = {
                'validate_environment': validate_environment,
                'check_critical_services': check_critical_services
            }
        except ImportError as e:
            logging.error(f"❌ Failed to import environment validation: {e}")
            raise
    return _lazy_imports['env_validation']

def get_traceback():
    """Lazy import traceback module only when needed"""
    if 'traceback' not in _lazy_imports:
        import traceback
        _lazy_imports['traceback'] = traceback
    return _lazy_imports['traceback']

# Configure logging for Railway deployment
log_level = os.environ.get("LOG_LEVEL", "INFO").upper()
logging.basicConfig(
    level=getattr(logging, log_level, logging.INFO),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Log Railway environment information
railway_env = os.environ.get("RAILWAY_ENVIRONMENT")
if railway_env:
    logger.info(f"Running in Railway environment: {railway_env}")
    logger.info(f"Railway project ID: {os.environ.get('RAILWAY_PROJECT_ID', 'Not set')}")
    logger.info(f"Port: {os.environ.get('PORT', 'Not set')}")
else:
    logger.info("Running in local development environment")

# Quick API key check without full validation (optimization)
logger.info("🔍 Performing initial environment validation...")
api_keys_present = {
    "openai": bool(os.getenv("OPENAI_API_KEY")),
    "finnhub": bool(os.getenv("FINNHUB_API_KEY")),
    "database": bool(os.getenv("NEON_DATABASE_URL"))
}

missing_keys = [k for k, v in api_keys_present.items() if not v]
if missing_keys:
    logger.warning(f"⚠️ Missing API keys: {', '.join(missing_keys)}")
    logger.warning("The application will start in limited mode.")
else:
    logger.info("✅ All critical API keys are present")

# Log API key status
print(f"🔑 OpenAI API Key loaded: {'Yes' if api_keys_present['openai'] else 'No'}")
print(f"🔑 Finnhub API Key loaded: {'Yes' if api_keys_present['finnhub'] else 'No'}")

# Global lazy-initialized services
_report_retrieval_service = None
_report_service_initialized = False

def get_report_retrieval_service():
    """Lazy initialize report retrieval service only when needed"""
    global _report_retrieval_service, _report_service_initialized
    
    if not _report_service_initialized:
        _report_service_initialized = True
        try:
            if os.getenv('NEON_DATABASE_URL'):
                classes = get_report_retrieval_classes()
                neon_config = classes['NeonConfig']()
                _report_retrieval_service = classes['ReportRetrievalService'](neon_config)
                logger.info("✅ Report retrieval service initialized successfully")
            else:
                logger.warning("⚠️ Database URL not configured - running without database support")
                _report_retrieval_service = None
        except Exception as e:
            logger.error(f"❌ Failed to initialize report retrieval service: {e}")
            logger.error("Database connection failed - running without database support")
            _report_retrieval_service = None
    
    return _report_retrieval_service

# Create a simple function that acts like a property for backward compatibility
def report_retrieval_service():
    return get_report_retrieval_service()

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifespan with proper startup and shutdown handling"""
    # Startup
    logger.info("🚀 Starting TradingAgents Web App...")
    
    # Setup signal handlers for graceful shutdown
    setup_signal_handlers()
    
    # Perform startup tasks
    await startup_tasks()
    
    yield
    
    # Shutdown
    logger.info("🛑 Shutting down TradingAgents Web App...")
    await shutdown_tasks()
    logger.info("✅ Shutdown complete")

app = FastAPI(title="TradingAgents Web App", version="1.0.0", lifespan=lifespan)

def setup_signal_handlers():
    """Setup signal handlers for graceful shutdown"""
    def signal_handler(signum, frame):
        logger.info(f"Received signal {signum}. Initiating graceful shutdown...")
        shutdown_event.set()
    
    # Handle SIGTERM (Railway uses this for graceful shutdown)
    signal.signal(signal.SIGTERM, signal_handler)
    # Handle SIGINT (Ctrl+C)
    signal.signal(signal.SIGINT, signal_handler)
    
    # Register cleanup function to run on exit
    atexit.register(cleanup_on_exit)
    
    logger.info("Signal handlers configured for graceful shutdown")

def cleanup_on_exit():
    """Cleanup function called on process exit"""
    logger.info("Process exit cleanup initiated")
    global _report_retrieval_service, _report_service_initialized
    if _report_service_initialized and _report_retrieval_service and hasattr(_report_retrieval_service, 'neon_config'):
        try:
            _report_retrieval_service.neon_config.close_connection_pool()
        except Exception as e:
            logger.error(f"Error closing database connection pool on exit: {e}")

async def startup_tasks():
    """Perform optimized startup tasks with minimal blocking operations"""
    # Log basic environment information immediately
    port = os.environ.get("PORT", "Not set")
    railway_env = os.environ.get("RAILWAY_ENVIRONMENT", "development")
    logger.info(f"🚀 Starting TradingAgents Web App - Environment: {railway_env}, Port: {port}")
    

    
    # Quick API key check without full validation
    api_keys_present = {
        "openai": bool(os.getenv("OPENAI_API_KEY")),
        "finnhub": bool(os.getenv("FINNHUB_API_KEY")),
        "database": bool(os.getenv("NEON_DATABASE_URL"))
    }
    
    logger.info(f"� APaI Keys: OpenAI: {'✓' if api_keys_present['openai'] else '✗'}, "
               f"Finnhub: {'✓' if api_keys_present['finnhub'] else '✗'}, "
               f"Database: {'✓' if api_keys_present['database'] else '✗'}")
    
    # Quick static files check
    static_dir = Path(__file__).parent / "static"
    static_exists = static_dir.exists()
    logger.info(f"📁 Static files: {'✓' if static_exists else '✗'}")
    
    # Schedule comprehensive validation as background task (non-blocking)
    task = asyncio.create_task(_background_validation())
    background_tasks.add(task)
    task.add_done_callback(background_tasks.discard)
    
    logger.info("🎯 TradingAgents Web App startup complete - Background validation in progress")

async def _background_validation():
    """Perform comprehensive validation in background without blocking startup"""
    try:
        # Wait a moment to let the server start accepting requests
        await asyncio.sleep(1.0)
        
        # Now perform comprehensive validation
        env_validation = get_env_validation()
        is_valid, validation_report = env_validation['validate_environment']()
        
        # Log detailed validation results
        summary = validation_report["summary"]
        logger.info(f"📋 Background validation complete: {summary['validated_variables']}/{summary['total_variables']} variables validated")
        
        if not is_valid:
            logger.warning("⚠️ Environment validation issues found:")
            for error in validation_report["errors"]:
                logger.warning(f"  {error}")
        
        if validation_report["warnings"]:
            for warning in validation_report["warnings"]:
                logger.info(f"  ℹ️ {warning}")
        
        # Test database connection if configured (non-blocking)
        if os.getenv('NEON_DATABASE_URL'):
            try:
                service = get_report_retrieval_service()
                if service:
                    db_health = service.health_check()
                    if db_health["healthy"]:
                        logger.info("✅ Database connection validated")
                    else:
                        logger.warning(f"⚠️ Database connection issues: {db_health.get('error', 'Unknown error')}")
            except Exception as e:
                logger.warning(f"⚠️ Database validation error: {e}")
        
        logger.info("✅ Background validation completed")
        
    except Exception as e:
        logger.error(f"❌ Background validation failed: {e}")

async def shutdown_tasks():
    """Perform graceful shutdown tasks"""
    logger.info("Starting graceful shutdown sequence...")
    
    # 1. Stop accepting new WebSocket connections and close existing ones
    logger.info("Closing WebSocket connections...")
    await manager.shutdown_all_connections()
    
    # 2. Cancel all background tasks
    logger.info("Cancelling background tasks...")
    if background_tasks:
        for task in background_tasks.copy():
            if not task.done():
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    logger.debug("Background task cancelled successfully")
                except Exception as e:
                    logger.warning(f"Error cancelling background task: {e}")
        background_tasks.clear()
        logger.info("All background tasks cancelled")
    
    # 3. Close database connections (only if initialized)
    logger.info("Closing database connections...")
    global _report_retrieval_service, _report_service_initialized
    if _report_service_initialized and _report_retrieval_service and hasattr(_report_retrieval_service, 'neon_config'):
        try:
            _report_retrieval_service.neon_config.close_connection_pool()
            logger.info("Database connection pool closed")
        except Exception as e:
            logger.error(f"Error closing database connection pool: {e}")
    
    # 4. Give a moment for any remaining cleanup
    await asyncio.sleep(0.1)
    
    logger.info("Graceful shutdown sequence completed")

# Enhanced CORS middleware with Railway proxy handling
def get_allowed_origins():
    """Get allowed origins with comprehensive Railway proxy support"""
    origins = [
        "http://localhost:8000",
        "http://localhost:8001", 
        "http://127.0.0.1:8000",
        "http://127.0.0.1:8001"
    ]
    
    # Railway domain configurations
    railway_domain = os.environ.get("RAILWAY_PUBLIC_DOMAIN")
    railway_static_url = os.environ.get("RAILWAY_STATIC_URL")
    railway_project_domain = os.environ.get("RAILWAY_PROJECT_DOMAIN")
    
    # Add Railway domains with comprehensive coverage
    railway_domains = []
    if railway_domain:
        railway_domains.extend([railway_domain])
    if railway_static_url:
        # Extract domain from static URL
        import re
        domain_match = re.search(r'https?://([^/]+)', railway_static_url)
        if domain_match:
            railway_domains.append(domain_match.group(1))
    if railway_project_domain:
        railway_domains.append(railway_project_domain)
    
    # Add all Railway domains with both HTTP and HTTPS
    for domain in railway_domains:
        origins.extend([
            f"https://{domain}",
            f"http://{domain}"
        ])
    
    # In development or if no specific domain, allow all origins
    railway_env = os.environ.get("RAILWAY_ENVIRONMENT", "development")
    if railway_env != "production" or not railway_domains:
        logger.info("CORS: Allowing all origins (development mode or no Railway domain configured)")
        return ["*"]
    
    logger.info(f"CORS: Configured origins: {origins}")
    return origins

# Enhanced CORS headers for Railway proxy compatibility
def get_cors_headers():
    """Get CORS headers optimized for Railway's reverse proxy"""
    return {
        "Access-Control-Allow-Origin": "*",  # Will be overridden by middleware
        "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS, PATCH",
        "Access-Control-Allow-Headers": "Content-Type, Authorization, X-Requested-With, Accept, Origin, Cache-Control, X-File-Name",
        "Access-Control-Allow-Credentials": "true",
        "Access-Control-Expose-Headers": "Content-Length, X-JSON",
        "Access-Control-Max-Age": "86400"  # 24 hours
    }

allowed_origins = get_allowed_origins()

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
    allow_headers=["*"],
    expose_headers=["Content-Length", "X-JSON"],
    max_age=86400,
)

# Railway proxy handling middleware
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

class RailwayProxyMiddleware(BaseHTTPMiddleware):
    """Middleware to handle Railway's reverse proxy headers and routing"""
    
    async def dispatch(self, request: Request, call_next):
        # Handle Railway proxy headers
        forwarded_proto = request.headers.get("x-forwarded-proto")
        forwarded_host = request.headers.get("x-forwarded-host")
        forwarded_for = request.headers.get("x-forwarded-for")
        
        # Log proxy information for debugging
        if forwarded_proto or forwarded_host or forwarded_for:
            logger.debug(f"Railway proxy headers - Proto: {forwarded_proto}, Host: {forwarded_host}, For: {forwarded_for}")
        
        # Set proper scheme for Railway HTTPS termination
        if forwarded_proto:
            request.scope["scheme"] = forwarded_proto
        
        # Set proper host for Railway routing
        if forwarded_host:
            request.scope["server"] = (forwarded_host, 443 if forwarded_proto == "https" else 80)
        
        # Add Railway-specific headers to response
        response = await call_next(request)
        
        # Add headers for Railway proxy compatibility
        response.headers["X-Railway-Proxy"] = "handled"
        
        # Ensure WebSocket upgrade headers are preserved
        if request.headers.get("upgrade") == "websocket":
            response.headers["Connection"] = "Upgrade"
            response.headers["Upgrade"] = "websocket"
        
        return response

# Add Railway proxy middleware
app.add_middleware(RailwayProxyMiddleware)

# Custom exception handler for consistent error responses
from fastapi.responses import JSONResponse

@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    """Custom HTTP exception handler with structured logging"""
    
    # Log the error with context
    logger.error(f"HTTP {exc.status_code}: {exc.detail}")
    logger.error(f"Request: {request.method} {request.url}")
    
    # Return consistent error response format
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "error": {
                "type": "HTTPException",
                "code": exc.status_code,
                "message": exc.detail,
                "timestamp": datetime.datetime.utcnow().isoformat()
            },
            "data": None
        }
    )


@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    """General exception handler for unexpected errors"""
    
    # Log the error with full traceback
    logger.error(f"Unexpected error: {str(exc)}")
    logger.error(f"Request: {request.method} {request.url}")
    traceback_module = get_traceback()
    logger.error(f"Traceback: {traceback_module.format_exc()}")
    
    # Return generic error response
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "error": {
                "type": "InternalServerError",
                "code": 500,
                "message": "An unexpected error occurred. Please try again later.",
                "timestamp": datetime.datetime.utcnow().isoformat()
            },
            "data": None
        }
    )

# Mount static files with production-ready configuration
static_dir = Path(__file__).parent / "static"
if not static_dir.exists():
    logger.warning(f"Static directory not found: {static_dir}")
    static_dir.mkdir(parents=True, exist_ok=True)

app.mount("/static", StaticFiles(directory=str(static_dir), html=True), name="static")

class AnalysisRequest(BaseModel):
    ticker: str
    analysis_date: str
    analysts: List[str]
    research_depth: int
    llm_provider: str
    backend_url: str
    shallow_thinker: str
    deep_thinker: str

class ReportResponse(BaseModel):
    success: bool
    agent: str
    report_content: Optional[str] = None
    report_type: str = "markdown"
    error: Optional[str] = None
    message: Optional[str] = None

# Removed file-based report mapping - now using database only

# Reverse mapping from frontend keys to full agent names
AGENT_KEY_TO_NAME_MAPPING = {
    'market': 'Market Analyst',
    'sentiment': 'Social Analyst',
    'news': 'News Analyst',
    'fundamentals': 'Fundamentals Analyst',
    'investment': 'Bull Researcher',  # Note: multiple agents map to this
    'trader': 'Trader',
    'final': 'Risky Analyst'  # Note: multiple agents map to this
}

class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self._shutdown_initiated = False

    async def connect(self, websocket: WebSocket):
        if self._shutdown_initiated:
            await websocket.close(code=1001, reason="Server shutting down")
            return
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info(f"WebSocket connected. Active connections: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
            logger.info(f"WebSocket disconnected. Active connections: {len(self.active_connections)}")

    async def send_personal_message(self, message: str, websocket: WebSocket):
        if self._shutdown_initiated:
            return
        try:
            await websocket.send_text(message)
        except Exception as e:
            logger.warning(f"Error sending personal message: {e}")
            self.disconnect(websocket)

    async def broadcast(self, message: str):
        if self._shutdown_initiated:
            return
        disconnected = []
        for connection in self.active_connections:
            try:
                await connection.send_text(message)
            except Exception as e:
                logger.warning(f"Error broadcasting to connection: {e}")
                disconnected.append(connection)
        
        # Remove disconnected connections
        for conn in disconnected:
            self.disconnect(conn)

    async def shutdown_all_connections(self):
        """Gracefully close all WebSocket connections during shutdown"""
        self._shutdown_initiated = True
        logger.info(f"Shutting down {len(self.active_connections)} WebSocket connections...")
        
        if self.active_connections:
            # Send shutdown notification to all clients
            shutdown_message = json.dumps({
                "type": "server_shutdown",
                "message": "Server is shutting down. Please reconnect in a moment."
            })
            
            # Broadcast shutdown message
            await self.broadcast(shutdown_message)
            
            # Give clients a moment to receive the message
            await asyncio.sleep(0.5)
            
            # Close all connections
            close_tasks = []
            for connection in self.active_connections.copy():
                try:
                    close_tasks.append(connection.close(code=1001, reason="Server shutdown"))
                except Exception as e:
                    logger.warning(f"Error closing WebSocket connection: {e}")
            
            # Wait for all connections to close
            if close_tasks:
                await asyncio.gather(*close_tasks, return_exceptions=True)
            
            self.active_connections.clear()
            logger.info("All WebSocket connections closed")

manager = ConnectionManager()

def convert_to_serializable(obj):
    """Convert objects to JSON-serializable format"""
    if isinstance(obj, dict):
        return {k: convert_to_serializable(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [convert_to_serializable(item) for item in obj]
    elif isinstance(obj, (str, int, float, bool)) or obj is None:
        return obj
    else:
        # Convert other objects to string representation
        return str(obj)

def get_recommendation_from_database(session_id: str) -> str:
    """
    Retrieve recommendation from database for a given session.
    
    Args:
        session_id: The session ID to retrieve recommendation for
        
    Returns:
        The recommendation (BUY/SELL/HOLD) or "HOLD" as fallback
    """
    service = report_retrieval_service()
    if not service or not session_id:
        logger.warning("Report retrieval service not available or no session ID provided")
        return "HOLD"
    
    try:
        # Get final analysis which includes recommendation
        result = service.get_final_analysis_safe(session_id)
        
        if result['success'] and result['data']:
            recommendation = result['data'].get('recommendation')
            if recommendation and recommendation in ['BUY', 'SELL', 'HOLD']:
                logger.debug(f"Retrieved recommendation from database: {recommendation}")
                return recommendation
        
        # Log the reason for fallback
        if not result['success']:
            logger.debug(f"Failed to retrieve recommendation: {result.get('error', {}).get('message', 'Unknown error')}")
        else:
            logger.debug("No recommendation found in database")
            
    except Exception as e:
        logger.error(f"Error retrieving recommendation from database: {e}")
    
    # Fallback to HOLD
    logger.debug("Using fallback recommendation: HOLD")
    return "HOLD"


def check_api_keys(provider: str) -> Optional[str]:
    """Check if required API keys are set for the provider"""
    provider = provider.lower()
    
    if provider == "openai":
        if not os.getenv("OPENAI_API_KEY"):
            return "OpenAI API key is required. Please set the OPENAI_API_KEY environment variable."
    elif provider == "anthropic":
        if not os.getenv("ANTHROPIC_API_KEY"):
            return "Anthropic API key is required. Please set the ANTHROPIC_API_KEY environment variable."
    elif provider == "google":
        if not os.getenv("GOOGLE_API_KEY"):
            return "Google API key is required. Please set the GOOGLE_API_KEY environment variable."
    
    return None




def find_session_for_ticker_date(ticker: str, date: str) -> Optional[str]:
    """
    Find the most recent session ID for a given ticker and date.
    
    Args:
        ticker: Stock ticker symbol
        date: Analysis date in YYYY-MM-DD format
        
    Returns:
        Session ID if found, None otherwise
    """
    service = report_retrieval_service()
    if not service:
        return None
    
    try:
        # Get recent sessions for the ticker
        sessions = service.get_sessions_by_ticker(ticker.upper(), limit=100)
        
        # Find sessions that match the date
        matching_sessions = [
            session for session in sessions 
            if session.get('analysis_date') == date
        ]
        
        if not matching_sessions:
            logger.debug(f"No sessions found for {ticker} on {date}")
            return None
        
        # Return the most recent session (sessions are ordered by created_at DESC)
        most_recent = matching_sessions[0]
        logger.debug(f"Found session {most_recent['session_id']} for {ticker} on {date}")
        return most_recent['session_id']
        
    except Exception as e:
        logger.error(f"Error finding session for {ticker}/{date}: {e}")
        return None


def load_report_from_database(ticker: str, date: str, agent: str) -> ReportResponse:
    """
    Load agent report from database using the new retrieval service.
    
    Args:
        ticker: Stock ticker symbol
        date: Analysis date in YYYY-MM-DD format
        agent: Agent name
        
    Returns:
        ReportResponse with report content or error information
    """
    try:
        # Find session for ticker and date
        session_id = find_session_for_ticker_date(ticker, date)
        
        if not session_id:
            return ReportResponse(
                success=False,
                agent=agent,
                error="Session not found",
                message=f"No analysis session found for {ticker} on {date}. Analysis may not have been completed yet."
            )
        
        # Retrieve the agent report using the safe method
        service = report_retrieval_service()
        if not service:
            return ReportResponse(
                success=False,
                agent=agent,
                error="Database error",
                message="Database service not available"
            )
        
        result = service.get_agent_report_safe(session_id, agent)
        
        if result['success']:
            # Extract report content from the response
            report_data = result['data']
            return ReportResponse(
                success=True,
                agent=agent,
                report_content=report_data['content'],
                report_type="markdown"
            )
        else:
            # Handle different error types
            error_info = result['error']
            error_type = error_info.get('type', 'Unknown')
            error_message = error_info.get('message', 'Unknown error')
            
            if error_type == 'NotFoundError':
                return ReportResponse(
                    success=False,
                    agent=agent,
                    error="Report not available",
                    message=f"Report for {agent} is not yet available. Analysis may still be in progress."
                )
            elif error_type == 'SessionNotFoundError':
                return ReportResponse(
                    success=False,
                    agent=agent,
                    error="Session not found",
                    message=f"Analysis session not found for {ticker} on {date}"
                )
            elif error_type == 'AgentValidationError':
                return ReportResponse(
                    success=False,
                    agent=agent,
                    error="Invalid agent",
                    message=f"Invalid agent type: {agent}"
                )
            elif error_type == 'DatabaseConnectionError':
                return ReportResponse(
                    success=False,
                    agent=agent,
                    error="Database error",
                    message="Database connection failed. Please try again later."
                )
            else:
                return ReportResponse(
                    success=False,
                    agent=agent,
                    error="Retrieval error",
                    message=f"Failed to retrieve report: {error_message}"
                )
                
    except Exception as e:
        logger.error(f"Unexpected error loading report from database: {e}")
        return ReportResponse(
            success=False,
            agent=agent,
            error="Internal error",
            message=f"Internal server error: {str(e)}"
        )


# Removed file-based report loading - now using database only

@app.get("/health")
async def health_check():
    """Enhanced health check endpoint for Railway monitoring with comprehensive service checks"""
    # Lazy import heavy modules only when health check is called
    import time
    
    def get_health_check_modules():
        """Lazy import modules needed for health checks"""
        if 'health_modules' not in _lazy_imports:
            from fastapi import status
            import asyncio
            import aiohttp
            _lazy_imports['health_modules'] = {
                'status': status,
                'asyncio': asyncio,
                'aiohttp': aiohttp
            }
        return _lazy_imports['health_modules']
    
    modules = get_health_check_modules()
    status = modules['status']
    asyncio = modules['asyncio']
    aiohttp = modules['aiohttp']
    
    start_time = time.time()
    
    # Perform environment validation
    env_validation = get_env_validation()
    is_env_valid, validation_report = env_validation['validate_environment']()
    
    health_status = {
        "status": "healthy", 
        "message": "TradingAgents Web App is running",
        "timestamp": datetime.datetime.utcnow().isoformat(),
        "environment": os.environ.get("RAILWAY_ENVIRONMENT", "development"),
        "port": os.environ.get("PORT", "8000"),
        "version": "1.0.0",
        "uptime_seconds": time.time() - start_time,
        "database": {
            "status": "not_configured",
            "connection_time_ms": None,
            "error": None
        },
        "api_services": {},
        "static_files": {
            "status": "unknown",
            "files_found": []
        },
        "environment_validation": {
            "valid": is_env_valid,
            "errors": len(validation_report["errors"]),
            "warnings": len(validation_report["warnings"]),
            "validated_vars": len(validation_report["validated_vars"])
        }
    }
    
    # Add environment validation details if there are issues
    if not is_env_valid:
        health_status["environment_validation"]["error_details"] = validation_report["errors"]
        health_status["status"] = "degraded"
    
    if validation_report["warnings"]:
        health_status["environment_validation"]["warning_details"] = validation_report["warnings"]
    
    # Enhanced database connectivity validation
    service = report_retrieval_service()
    if service:
        db_start = time.time()
        try:
            db_health = service.health_check()
            db_time = (time.time() - db_start) * 1000  # Convert to milliseconds
            
            health_status["database"] = {
                "status": "healthy" if db_health["healthy"] else "unhealthy",
                "connection_time_ms": round(db_time, 2),
                "error": None if db_health["healthy"] else db_health.get("error", "Unknown database error"),
                "details": db_health
            }
            
            if not db_health["healthy"]:
                health_status["status"] = "degraded"
                
        except Exception as e:
            db_time = (time.time() - db_start) * 1000
            health_status["database"] = {
                "status": "error",
                "connection_time_ms": round(db_time, 2),
                "error": str(e),
                "details": None
            }
            health_status["status"] = "unhealthy"
    else:
        health_status["database"] = {
            "status": "not_configured",
            "connection_time_ms": None,
            "error": "Database URL not configured",
            "details": None
        }
    
    # Enhanced API service availability checks with actual connectivity testing
    api_services = {}
    
    # Test OpenAI API
    openai_key = os.getenv("OPENAI_API_KEY")
    if openai_key:
        api_services["openai"] = await _test_openai_api(openai_key)
    else:
        api_services["openai"] = {
            "configured": False,
            "available": False,
            "response_time_ms": None,
            "error": "API key not configured"
        }
    
    # Test Finnhub API
    finnhub_key = os.getenv("FINNHUB_API_KEY")
    if finnhub_key:
        api_services["finnhub"] = await _test_finnhub_api(finnhub_key)
    else:
        api_services["finnhub"] = {
            "configured": False,
            "available": False,
            "response_time_ms": None,
            "error": "API key not configured"
        }
    
    # Test Anthropic API (optional)
    anthropic_key = os.getenv("ANTHROPIC_API_KEY")
    if anthropic_key:
        api_services["anthropic"] = await _test_anthropic_api(anthropic_key)
    else:
        api_services["anthropic"] = {
            "configured": False,
            "available": False,
            "response_time_ms": None,
            "error": "API key not configured (optional)"
        }
    
    # Test Google API (optional)
    google_key = os.getenv("GOOGLE_API_KEY")
    if google_key:
        api_services["google"] = await _test_google_api(google_key)
    else:
        api_services["google"] = {
            "configured": False,
            "available": False,
            "response_time_ms": None,
            "error": "API key not configured (optional)"
        }
    
    health_status["api_services"] = api_services
    
    # Enhanced static files availability check
    static_dir = Path(__file__).parent / "static"
    static_files = {
        "status": "missing",
        "files_found": [],
        "required_files": ["index.html", "app.js", "style.css"]
    }
    
    if static_dir.exists():
        found_files = [f.name for f in static_dir.iterdir() if f.is_file()]
        static_files["files_found"] = found_files
        
        # Check for required files
        required_files = static_files["required_files"]
        missing_files = [f for f in required_files if f not in found_files]
        
        if not missing_files:
            static_files["status"] = "complete"
        elif "index.html" in found_files:
            static_files["status"] = "partial"
            static_files["missing_files"] = missing_files
        else:
            static_files["status"] = "missing"
            static_files["missing_files"] = missing_files
    else:
        static_files["missing_files"] = static_files["required_files"]
    
    health_status["static_files"] = static_files
    
    # Overall health assessment with proper HTTP status codes
    critical_services_down = 0
    optional_services_down = 0
    
    # Check critical services
    if health_status["database"]["status"] == "error":
        critical_services_down += 1
    if not api_services["openai"]["available"] and api_services["openai"]["configured"]:
        critical_services_down += 1
    if not api_services["finnhub"]["available"] and api_services["finnhub"]["configured"]:
        critical_services_down += 1
    if static_files["status"] == "missing":
        critical_services_down += 1
    
    # Check optional services
    if health_status["database"]["status"] == "unhealthy":
        optional_services_down += 1
    if not api_services["anthropic"]["available"] and api_services["anthropic"]["configured"]:
        optional_services_down += 1
    if not api_services["google"]["available"] and api_services["google"]["configured"]:
        optional_services_down += 1
    if static_files["status"] == "partial":
        optional_services_down += 1
    
    # Determine overall status
    if critical_services_down > 0 or not is_env_valid:
        health_status["status"] = "unhealthy"
        response_status = status.HTTP_503_SERVICE_UNAVAILABLE
    elif optional_services_down > 0:
        health_status["status"] = "degraded"
        response_status = status.HTTP_200_OK
    else:
        health_status["status"] = "healthy"
        response_status = status.HTTP_200_OK
    
    # Add summary
    health_status["summary"] = {
        "critical_services_down": critical_services_down,
        "optional_services_down": optional_services_down,
        "total_response_time_ms": round((time.time() - start_time) * 1000, 2)
    }
    
    # Return with appropriate HTTP status code
    from fastapi.responses import JSONResponse
    return JSONResponse(content=health_status, status_code=response_status)


async def _test_openai_api(api_key: str) -> dict:
    """Test OpenAI API connectivity and response time"""
    import aiohttp
    import time
    
    start_time = time.time()
    try:
        timeout = aiohttp.ClientTimeout(total=10)  # 10 second timeout
        async with aiohttp.ClientSession(timeout=timeout) as session:
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            }
            
            # Test with a simple models list request
            async with session.get("https://api.openai.com/v1/models", headers=headers) as response:
                response_time = (time.time() - start_time) * 1000
                
                if response.status == 200:
                    return {
                        "configured": True,
                        "available": True,
                        "response_time_ms": round(response_time, 2),
                        "error": None
                    }
                else:
                    error_text = await response.text()
                    return {
                        "configured": True,
                        "available": False,
                        "response_time_ms": round(response_time, 2),
                        "error": f"HTTP {response.status}: {error_text[:100]}"
                    }
                    
    except asyncio.TimeoutError:
        response_time = (time.time() - start_time) * 1000
        return {
            "configured": True,
            "available": False,
            "response_time_ms": round(response_time, 2),
            "error": "Request timeout (>10s)"
        }
    except Exception as e:
        response_time = (time.time() - start_time) * 1000
        return {
            "configured": True,
            "available": False,
            "response_time_ms": round(response_time, 2),
            "error": f"Connection error: {str(e)}"
        }


async def _test_finnhub_api(api_key: str) -> dict:
    """Test Finnhub API connectivity and response time"""
    import aiohttp
    import time
    
    start_time = time.time()
    try:
        timeout = aiohttp.ClientTimeout(total=10)  # 10 second timeout
        async with aiohttp.ClientSession(timeout=timeout) as session:
            # Test with a simple quote request for AAPL
            url = f"https://finnhub.io/api/v1/quote?symbol=AAPL&token={api_key}"
            
            async with session.get(url) as response:
                response_time = (time.time() - start_time) * 1000
                
                if response.status == 200:
                    data = await response.json()
                    # Check if we got valid data (not an error response)
                    if 'c' in data:  # 'c' is current price in Finnhub response
                        return {
                            "configured": True,
                            "available": True,
                            "response_time_ms": round(response_time, 2),
                            "error": None
                        }
                    else:
                        return {
                            "configured": True,
                            "available": False,
                            "response_time_ms": round(response_time, 2),
                            "error": "Invalid API key or quota exceeded"
                        }
                else:
                    error_text = await response.text()
                    return {
                        "configured": True,
                        "available": False,
                        "response_time_ms": round(response_time, 2),
                        "error": f"HTTP {response.status}: {error_text[:100]}"
                    }
                    
    except asyncio.TimeoutError:
        response_time = (time.time() - start_time) * 1000
        return {
            "configured": True,
            "available": False,
            "response_time_ms": round(response_time, 2),
            "error": "Request timeout (>10s)"
        }
    except Exception as e:
        response_time = (time.time() - start_time) * 1000
        return {
            "configured": True,
            "available": False,
            "response_time_ms": round(response_time, 2),
            "error": f"Connection error: {str(e)}"
        }


async def _test_anthropic_api(api_key: str) -> dict:
    """Test Anthropic API connectivity and response time"""
    import aiohttp
    import time
    
    start_time = time.time()
    try:
        timeout = aiohttp.ClientTimeout(total=10)  # 10 second timeout
        async with aiohttp.ClientSession(timeout=timeout) as session:
            headers = {
                "x-api-key": api_key,
                "Content-Type": "application/json",
                "anthropic-version": "2023-06-01"
            }
            
            # Test with a simple message request
            payload = {
                "model": "claude-3-haiku-20240307",
                "max_tokens": 10,
                "messages": [{"role": "user", "content": "Hi"}]
            }
            
            async with session.post("https://api.anthropic.com/v1/messages", 
                                  headers=headers, json=payload) as response:
                response_time = (time.time() - start_time) * 1000
                
                if response.status == 200:
                    return {
                        "configured": True,
                        "available": True,
                        "response_time_ms": round(response_time, 2),
                        "error": None
                    }
                else:
                    error_text = await response.text()
                    return {
                        "configured": True,
                        "available": False,
                        "response_time_ms": round(response_time, 2),
                        "error": f"HTTP {response.status}: {error_text[:100]}"
                    }
                    
    except asyncio.TimeoutError:
        response_time = (time.time() - start_time) * 1000
        return {
            "configured": True,
            "available": False,
            "response_time_ms": round(response_time, 2),
            "error": "Request timeout (>10s)"
        }
    except Exception as e:
        response_time = (time.time() - start_time) * 1000
        return {
            "configured": True,
            "available": False,
            "response_time_ms": round(response_time, 2),
            "error": f"Connection error: {str(e)}"
        }


async def _test_google_api(api_key: str) -> dict:
    """Test Google API connectivity and response time"""
    import aiohttp
    import time
    
    start_time = time.time()
    try:
        timeout = aiohttp.ClientTimeout(total=10)  # 10 second timeout
        async with aiohttp.ClientSession(timeout=timeout) as session:
            headers = {
                "Content-Type": "application/json"
            }
            
            # Test with a simple generateContent request
            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent?key={api_key}"
            payload = {
                "contents": [{
                    "parts": [{"text": "Hi"}]
                }]
            }
            
            async with session.post(url, headers=headers, json=payload) as response:
                response_time = (time.time() - start_time) * 1000
                
                if response.status == 200:
                    return {
                        "configured": True,
                        "available": True,
                        "response_time_ms": round(response_time, 2),
                        "error": None
                    }
                else:
                    error_text = await response.text()
                    return {
                        "configured": True,
                        "available": False,
                        "response_time_ms": round(response_time, 2),
                        "error": f"HTTP {response.status}: {error_text[:100]}"
                    }
                    
    except asyncio.TimeoutError:
        response_time = (time.time() - start_time) * 1000
        return {
            "configured": True,
            "available": False,
            "response_time_ms": round(response_time, 2),
            "error": "Request timeout (>10s)"
        }
    except Exception as e:
        response_time = (time.time() - start_time) * 1000
        return {
            "configured": True,
            "available": False,
            "response_time_ms": round(response_time, 2),
            "error": f"Connection error: {str(e)}"
        }


@app.get("/api/environment/validation")
async def environment_validation_check():
    """Detailed environment variable validation endpoint"""
    try:
        env_validation = get_env_validation()
        is_valid, validation_report = env_validation['validate_environment']()
        
        # Add helpful setup information
        setup_info = {
            "railway_detected": bool(os.environ.get("RAILWAY_ENVIRONMENT")),
            "required_for_basic_operation": [
                "OPENAI_API_KEY",
                "FINNHUB_API_KEY", 
                "NEON_DATABASE_URL"
            ],
            "optional_for_enhanced_features": [
                "ANTHROPIC_API_KEY",
                "GOOGLE_API_KEY"
            ],
            "railway_provided_variables": [
                "PORT",
                "RAILWAY_ENVIRONMENT",
                "RAILWAY_PROJECT_ID",
                "RAILWAY_PUBLIC_DOMAIN"
            ]
        }
        
        return {
            "validation": validation_report,
            "setup_info": setup_info,
            "recommendations": _get_setup_recommendations(validation_report)
        }
        
    except Exception as e:
        logger.error(f"Environment validation check error: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Environment validation failed: {str(e)}"
        )

def _get_setup_recommendations(validation_report: Dict[str, any]) -> List[str]:
    """Generate setup recommendations based on validation results"""
    recommendations = []
    
    if validation_report["errors"]:
        recommendations.append(
            "❌ Fix the environment variable errors listed above before deploying to production"
        )
    
    # Check for missing critical services
    validated_vars = validation_report["validated_vars"]
    
    if "OPENAI_API_KEY" not in validated_vars:
        recommendations.append(
            "🔑 Set OPENAI_API_KEY: Get your API key from https://platform.openai.com/api-keys"
        )
    
    if "FINNHUB_API_KEY" not in validated_vars:
        recommendations.append(
            "🔑 Set FINNHUB_API_KEY: Get a free API key from https://finnhub.io/register"
        )
    
    if "NEON_DATABASE_URL" not in validated_vars:
        recommendations.append(
            "🗄️ Set NEON_DATABASE_URL: Create a free PostgreSQL database at https://neon.tech"
        )
    
    # Railway-specific recommendations
    if os.environ.get("RAILWAY_ENVIRONMENT"):
        recommendations.append(
            "🚂 Railway detected: Set environment variables in Railway dashboard under Variables tab"
        )
    else:
        recommendations.append(
            "💻 Local development: Copy .env.example to .env and fill in your API keys"
        )
    
    if not recommendations:
        recommendations.append("✅ All critical environment variables are properly configured!")
    
    return recommendations

@app.get("/api/database/health")
async def database_health_check():
    """Detailed database health check endpoint"""
    service = report_retrieval_service()
    if not service:
        raise HTTPException(
            status_code=503,
            detail="Database service not configured. Check environment variables."
        )
    
    try:
        health_status = service.health_check()
        
        if not health_status["healthy"]:
            raise HTTPException(
                status_code=503,
                detail=f"Database health check failed: {health_status.get('error', 'Unknown error')}"
            )
        
        return {
            "status": "healthy",
            "message": "Database connection is working properly",
            "details": health_status
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Database health check error: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Health check failed: {str(e)}"
        )

@app.get("/api/test-graph")
async def test_graph_initialization():
    """Test if TradingAgentsGraph can be initialized"""
    try:
        # Check if API keys are available
        openai_key = os.getenv('OPENAI_API_KEY')
        finnhub_key = os.getenv('FINNHUB_API_KEY')
        
        if not openai_key:
            return {"status": "error", "message": "OPENAI_API_KEY not found in environment"}
        if not finnhub_key:
            return {"status": "error", "message": "FINNHUB_API_KEY not found in environment"}
        
        # Lazy load the required classes
        TradingAgentsGraph = get_trading_graph()
        DEFAULT_CONFIG = get_default_config()
        
        config = DEFAULT_CONFIG.copy()
        config["llm_provider"] = "openai"
        config["backend_url"] = "https://api.openai.com/v1"
        config["quick_think_llm"] = "gpt-4o-mini"
        config["deep_think_llm"] = "gpt-4o"
        
        # Try to initialize with minimal config
        graph = TradingAgentsGraph(["market"], config=config, debug=True)
        return {
            "status": "success", 
            "message": "TradingAgentsGraph initialized successfully",
            "api_keys": {
                "openai": f"sk-...{openai_key[-4:]}" if openai_key else "Not found",
                "finnhub": f"...{finnhub_key[-4:]}" if finnhub_key else "Not found"
            }
        }
    except Exception as e:
        return {"status": "error", "message": f"Failed to initialize TradingAgentsGraph: {str(e)}"}

@app.get("/api/check-setup")
async def check_setup():
    """Check if the system is properly set up with API keys"""
    setup_status = {
        "openai": bool(os.getenv("OPENAI_API_KEY")),
        "anthropic": bool(os.getenv("ANTHROPIC_API_KEY")),
        "google": bool(os.getenv("GOOGLE_API_KEY")),
    }
    
    has_any_key = any(setup_status.values())
    
    return {
        "has_api_keys": has_any_key,
        "providers": setup_status,
        "message": "API keys configured" if has_any_key else "No API keys found. Demo mode available."
    }

@app.get("/", response_class=HTMLResponse)
async def get_index():
    """Serve the main web interface with Railway-compatible file serving"""
    html_file = Path(__file__).parent / "static" / "index.html"
    
    if not html_file.exists():
        logger.error(f"Index file not found at: {html_file}")
        # Try to create a basic index.html if it doesn't exist
        try:
            html_file.parent.mkdir(parents=True, exist_ok=True)
            basic_html = """<!DOCTYPE html>
<html>
<head>
    <title>TradingAgents Web App</title>
</head>
<body>
    <h1>TradingAgents Web App</h1>
    <p>The application is running, but the static files are not properly configured.</p>
    <p>Please check the static directory configuration.</p>
</body>
</html>"""
            html_file.write_text(basic_html)
            logger.info("Created basic index.html file")
        except Exception as e:
            logger.error(f"Failed to create basic index.html: {e}")
            raise HTTPException(status_code=404, detail="Index file not found and could not be created")
    
    try:
        return FileResponse(
            str(html_file),
            media_type="text/html",
            headers={"Cache-Control": "no-cache"}
        )
    except Exception as e:
        logger.error(f"Error serving index file: {e}")
        raise HTTPException(status_code=500, detail="Error serving index file")

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """Enhanced WebSocket endpoint with Railway proxy support"""
    
    # Log connection details for Railway debugging
    client_host = websocket.client.host if websocket.client else "unknown"
    forwarded_for = websocket.headers.get("x-forwarded-for", "")
    user_agent = websocket.headers.get("user-agent", "")
    
    logger.info(f"WebSocket connection attempt - Client: {client_host}, Forwarded: {forwarded_for}, UA: {user_agent[:50]}")
    
    # Check for Railway proxy headers
    railway_headers = {
        "x-forwarded-proto": websocket.headers.get("x-forwarded-proto"),
        "x-forwarded-host": websocket.headers.get("x-forwarded-host"),
        "x-forwarded-for": websocket.headers.get("x-forwarded-for"),
        "x-real-ip": websocket.headers.get("x-real-ip"),
    }
    
    # Log Railway proxy information
    railway_info = {k: v for k, v in railway_headers.items() if v}
    if railway_info:
        logger.debug(f"Railway proxy headers: {railway_info}")
    
    try:
        await manager.connect(websocket)
        logger.info("WebSocket connection established successfully")
        
        # Send initial connection confirmation with Railway info
        await websocket.send_text(json.dumps({
            "type": "connection_established",
            "message": "WebSocket connected successfully",
            "railway_proxy": bool(railway_info),
            "timestamp": datetime.datetime.utcnow().isoformat()
        }))
        
        while not shutdown_event.is_set():
            try:
                # Use a timeout to periodically check for shutdown
                data = await asyncio.wait_for(websocket.receive_text(), timeout=1.0)
                
                # Parse and handle the message
                try:
                    message = json.loads(data)
                    message_type = message.get("type", "unknown")
                    
                    if message_type == "ping":
                        # Respond to ping with pong
                        await websocket.send_text(json.dumps({
                            "type": "pong", 
                            "message": "pong",
                            "timestamp": datetime.datetime.utcnow().isoformat()
                        }))
                    else:
                        # Echo other messages for debugging
                        await websocket.send_text(json.dumps({
                            "type": "echo", 
                            "original_message": message,
                            "timestamp": datetime.datetime.utcnow().isoformat()
                        }))
                        
                except json.JSONDecodeError:
                    # Handle non-JSON messages
                    await websocket.send_text(json.dumps({
                        "type": "echo", 
                        "message": data,
                        "timestamp": datetime.datetime.utcnow().isoformat()
                    }))
                
            except asyncio.TimeoutError:
                # Timeout is expected, continue loop to check shutdown event
                continue
            except WebSocketDisconnect:
                logger.info("WebSocket client disconnected normally")
                break
            except Exception as e:
                logger.warning(f"WebSocket message handling error: {e}")
                # Try to send error message to client
                try:
                    await websocket.send_text(json.dumps({
                        "type": "error",
                        "message": f"Message handling error: {str(e)}",
                        "timestamp": datetime.datetime.utcnow().isoformat()
                    }))
                except:
                    # If we can't send error message, connection is likely broken
                    break
        
        # If shutdown event is set, close gracefully
        if shutdown_event.is_set():
            logger.info("Closing WebSocket due to server shutdown")
            await websocket.close(code=1001, reason="Server shutdown")
            
    except WebSocketDisconnect:
        logger.debug("WebSocket client disconnected")
        
    except Exception as e:
        logger.error(f"Unexpected WebSocket error: {e}")
        traceback_module = get_traceback()
        logger.error(f"WebSocket error traceback: {traceback_module.format_exc()}")
        
    finally:
        manager.disconnect(websocket)
        logger.debug("WebSocket cleanup completed")

@app.get("/api/railway/proxy-test")
async def railway_proxy_test(request: Request):
    """Test Railway proxy configuration and headers"""
    
    # Collect all relevant headers
    headers_info = {
        "x-forwarded-proto": request.headers.get("x-forwarded-proto"),
        "x-forwarded-host": request.headers.get("x-forwarded-host"),
        "x-forwarded-for": request.headers.get("x-forwarded-for"),
        "x-real-ip": request.headers.get("x-real-ip"),
        "host": request.headers.get("host"),
        "user-agent": request.headers.get("user-agent"),
        "origin": request.headers.get("origin"),
        "referer": request.headers.get("referer"),
    }
    
    # Railway environment info
    railway_info = {
        "railway_environment": os.environ.get("RAILWAY_ENVIRONMENT"),
        "railway_public_domain": os.environ.get("RAILWAY_PUBLIC_DOMAIN"),
        "railway_static_url": os.environ.get("RAILWAY_STATIC_URL"),
        "railway_project_domain": os.environ.get("RAILWAY_PROJECT_DOMAIN"),
        "railway_project_id": os.environ.get("RAILWAY_PROJECT_ID"),
        "port": os.environ.get("PORT"),
    }
    
    # Request info
    request_info = {
        "method": request.method,
        "url": str(request.url),
        "scheme": request.url.scheme,
        "hostname": request.url.hostname,
        "port": request.url.port,
        "path": request.url.path,
        "client_host": request.client.host if request.client else None,
        "client_port": request.client.port if request.client else None,
    }
    
    # CORS configuration
    cors_info = {
        "allowed_origins": allowed_origins,
        "cors_configured": True,
    }
    
    return {
        "success": True,
        "message": "Railway proxy test completed",
        "timestamp": datetime.datetime.utcnow().isoformat(),
        "headers": headers_info,
        "railway": railway_info,
        "request": request_info,
        "cors": cors_info,
        "proxy_detected": bool(headers_info["x-forwarded-proto"] or headers_info["x-forwarded-host"]),
    }

@app.get("/api/environment/status")
async def environment_status():
    """Get current environment status with user-friendly messages"""
    try:
        env_validation = get_env_validation()
        is_valid, validation_report = env_validation['validate_environment']()
        services_status = env_validation['check_critical_services']()
        
        # Determine overall status
        if is_valid and services_status["openai"] and services_status["finnhub"] and services_status["database"]:
            overall_status = "ready"
            message = "All systems operational - ready for trading analysis"
        elif services_status["openai"] and services_status["finnhub"]:
            overall_status = "limited"
            message = "Core services available - database features may be limited"
        else:
            overall_status = "setup_required"
            message = "Setup required - missing critical API keys or database configuration"
        
        # Generate user-friendly error messages
        user_friendly_errors = []
        if not services_status["openai"]:
            user_friendly_errors.append({
                "service": "OpenAI",
                "message": "OpenAI API key is required for AI-powered analysis",
                "action": "Set OPENAI_API_KEY environment variable",
                "help_url": "https://platform.openai.com/api-keys"
            })
        
        if not services_status["finnhub"]:
            user_friendly_errors.append({
                "service": "Finnhub",
                "message": "Finnhub API key is required for financial data",
                "action": "Set FINNHUB_API_KEY environment variable", 
                "help_url": "https://finnhub.io/register"
            })
        
        if not services_status["database"]:
            user_friendly_errors.append({
                "service": "Database",
                "message": "Database connection is required for storing analysis results",
                "action": "Set NEON_DATABASE_URL environment variable",
                "help_url": "https://neon.tech"
            })
        
        return {
            "status": overall_status,
            "message": message,
            "services": services_status,
            "validation": {
                "valid": is_valid,
                "errors_count": len(validation_report["errors"]),
                "warnings_count": len(validation_report["warnings"])
            },
            "setup_errors": user_friendly_errors,
            "railway_environment": bool(os.environ.get("RAILWAY_ENVIRONMENT")),
            "setup_guide": "/static/RAILWAY_ENV_SETUP.md" if os.environ.get("RAILWAY_ENVIRONMENT") else "See .env.example file"
        }
        
    except Exception as e:
        logger.error(f"Environment status check error: {e}")
        return {
            "status": "error",
            "message": f"Unable to check environment status: {str(e)}",
            "services": {},
            "validation": {"valid": False, "errors_count": 1, "warnings_count": 0},
            "setup_errors": [],
            "railway_environment": bool(os.environ.get("RAILWAY_ENVIRONMENT"))
        }

@app.post("/api/analyze")
async def start_analysis(request: AnalysisRequest):
    """Start the trading analysis process with enhanced environment validation"""
    try:
        print(f"📊 Starting analysis for {request.ticker}")
        
        # Perform comprehensive environment validation before starting analysis
        env_validation = get_env_validation()
        is_valid, validation_report = env_validation['validate_environment']()
        
        if not is_valid:
            # Provide detailed error information
            missing_vars = []
            for error in validation_report["errors"]:
                if "OPENAI_API_KEY" in error:
                    missing_vars.append("OpenAI API key is required for LLM analysis")
                elif "FINNHUB_API_KEY" in error:
                    missing_vars.append("Finnhub API key is required for financial data")
                elif "NEON_DATABASE_URL" in error:
                    missing_vars.append("Database URL is required for storing results")
            
            if missing_vars:
                error_detail = {
                    "error": "Environment configuration incomplete",
                    "missing_requirements": missing_vars,
                    "setup_guide": "See /api/environment/validation for detailed setup instructions"
                }
                raise HTTPException(status_code=400, detail=error_detail)
        
        # Check for API keys based on provider
        api_key_error = check_api_keys(request.llm_provider)
        if api_key_error:
            raise HTTPException(
                status_code=400, 
                detail={
                    "error": api_key_error,
                    "setup_guide": "Check /api/environment/validation for setup instructions"
                }
            )
        
        # Create config with user selections
        config = DEFAULT_CONFIG.copy()
        config["max_debate_rounds"] = request.research_depth
        config["max_risk_discuss_rounds"] = request.research_depth
        config["quick_think_llm"] = request.shallow_thinker
        config["deep_think_llm"] = request.deep_thinker
        config["backend_url"] = request.backend_url
        config["llm_provider"] = request.llm_provider.lower()

        # Results will be saved directly to database by TradingAgentsGraph

        # Initialize the graph
        print("Initializing TradingAgentsGraph...")
        TradingAgentsGraph = get_trading_graph()
        graph = TradingAgentsGraph(
            request.analysts, config=config, debug=True
        )
        print("Graph initialized successfully")

        # Start analysis in background
        print("Starting background analysis...")
        task = asyncio.create_task(run_analysis_background(graph, request))
        background_tasks.add(task)
        # Remove task from set when it completes
        task.add_done_callback(background_tasks.discard)

        return {"status": "started", "message": "Analysis started successfully"}

    except HTTPException:
        raise
    except Exception as e:
        error_msg = f"Error starting analysis: {str(e)}"
        print(f"❌ {error_msg}")
        traceback_module = get_traceback()
        print(f"Traceback: {traceback_module.format_exc()}")
        raise HTTPException(status_code=500, detail=error_msg)

async def run_analysis_background(graph, request: AnalysisRequest):
    """Run the analysis in the background and send updates via WebSocket"""
    try:
        # Check if shutdown is already initiated
        if shutdown_event.is_set():
            logger.info("Shutdown initiated, skipping analysis")
            return
            
        # Send initial status
        await manager.broadcast(json.dumps({
            "type": "status",
            "message": f"Starting analysis for {request.ticker} on {request.analysis_date}"
        }))

        # Initialize agent status tracking
        agents = [
            "Market Analyst", "Social Analyst", "News Analyst", "Fundamentals Analyst",
            "Bull Researcher", "Bear Researcher", "Research Manager",
            "Trader", "Risky Analyst", "Neutral Analyst", "Safe Analyst", "Portfolio Manager"
        ]

        for agent in agents:
            await manager.broadcast(json.dumps({
                "type": "agent_status",
                "agent": agent,
                "status": "pending"
            }))

        # Simulate progressive agent completion during analysis
        async def update_agent_progress():
            # Check for shutdown before each step
            if shutdown_event.is_set():
                return
                
            # Market Analyst
            await asyncio.sleep(2)
            if shutdown_event.is_set():
                return
            await manager.broadcast(json.dumps({
                "type": "agent_status",
                "agent": "Market Analyst",
                "status": "in_progress"
            }))
            
            await asyncio.sleep(3)
            if shutdown_event.is_set():
                return
            await manager.broadcast(json.dumps({
                "type": "agent_status",
                "agent": "Market Analyst",
                "status": "completed"
            }))
            
            # Social Analyst
            if shutdown_event.is_set():
                return
            await manager.broadcast(json.dumps({
                "type": "agent_status",
                "agent": "Social Analyst",
                "status": "in_progress"
            }))
            
            await asyncio.sleep(2)
            if shutdown_event.is_set():
                return
            await manager.broadcast(json.dumps({
                "type": "agent_status",
                "agent": "Social Analyst",
                "status": "completed"
            }))
            
            # News Analyst
            await manager.broadcast(json.dumps({
                "type": "agent_status",
                "agent": "News Analyst",
                "status": "in_progress"
            }))
            
            await asyncio.sleep(2)
            await manager.broadcast(json.dumps({
                "type": "agent_status",
                "agent": "News Analyst",
                "status": "completed"
            }))
            
            # Fundamentals Analyst
            await manager.broadcast(json.dumps({
                "type": "agent_status",
                "agent": "Fundamentals Analyst",
                "status": "in_progress"
            }))
            
            await asyncio.sleep(2)
            await manager.broadcast(json.dumps({
                "type": "agent_status",
                "agent": "Fundamentals Analyst",
                "status": "completed"
            }))
            
            # Research Team
            await manager.broadcast(json.dumps({
                "type": "agent_status",
                "agent": "Bull Researcher",
                "status": "in_progress"
            }))
            
            await asyncio.sleep(3)
            await manager.broadcast(json.dumps({
                "type": "agent_status",
                "agent": "Bull Researcher",
                "status": "completed"
            }))
            
            await manager.broadcast(json.dumps({
                "type": "agent_status",
                "agent": "Bear Researcher",
                "status": "in_progress"
            }))
            
            await asyncio.sleep(3)
            await manager.broadcast(json.dumps({
                "type": "agent_status",
                "agent": "Bear Researcher",
                "status": "completed"
            }))
            
            await manager.broadcast(json.dumps({
                "type": "agent_status",
                "agent": "Research Manager",
                "status": "in_progress"
            }))
            
            await asyncio.sleep(2)
            await manager.broadcast(json.dumps({
                "type": "agent_status",
                "agent": "Research Manager",
                "status": "completed"
            }))
            
            # Trading Team
            await manager.broadcast(json.dumps({
                "type": "agent_status",
                "agent": "Trader",
                "status": "in_progress"
            }))
            
            await asyncio.sleep(2)
            await manager.broadcast(json.dumps({
                "type": "agent_status",
                "agent": "Trader",
                "status": "completed"
            }))
            
            # Risk Management
            await manager.broadcast(json.dumps({
                "type": "agent_status",
                "agent": "Risky Analyst",
                "status": "in_progress"
            }))
            
            await asyncio.sleep(2)
            await manager.broadcast(json.dumps({
                "type": "agent_status",
                "agent": "Risky Analyst",
                "status": "completed"
            }))
            
            await manager.broadcast(json.dumps({
                "type": "agent_status",
                "agent": "Neutral Analyst",
                "status": "in_progress"
            }))
            
            await asyncio.sleep(2)
            await manager.broadcast(json.dumps({
                "type": "agent_status",
                "agent": "Neutral Analyst",
                "status": "completed"
            }))
            
            await manager.broadcast(json.dumps({
                "type": "agent_status",
                "agent": "Safe Analyst",
                "status": "in_progress"
            }))
            
            await asyncio.sleep(2)
            await manager.broadcast(json.dumps({
                "type": "agent_status",
                "agent": "Safe Analyst",
                "status": "completed"
            }))
            
            # Portfolio Management
            await manager.broadcast(json.dumps({
                "type": "agent_status",
                "agent": "Portfolio Manager",
                "status": "in_progress"
            }))
            
            await asyncio.sleep(3)
            await manager.broadcast(json.dumps({
                "type": "agent_status",
                "agent": "Portfolio Manager",
                "status": "completed"
            }))

        # Start progress updates in parallel with analysis
        progress_task = asyncio.create_task(update_agent_progress())
        
        # Check for shutdown before starting analysis
        if shutdown_event.is_set():
            progress_task.cancel()
            await manager.broadcast(json.dumps({
                "type": "analysis_cancelled",
                "message": "Analysis cancelled due to server shutdown"
            }))
            return
        
        # Run the actual analysis
        try:
            final_state, decision = graph.propagate(request.ticker, request.analysis_date)
        except Exception as e:
            # Cancel progress updates if analysis fails
            progress_task.cancel()
            raise e
        
        # Wait for progress updates to complete (or cancel if shutdown)
        if not shutdown_event.is_set():
            try:
                await progress_task
            except asyncio.CancelledError:
                pass

        # Check for shutdown before processing results
        if shutdown_event.is_set():
            await manager.broadcast(json.dumps({
                "type": "analysis_cancelled",
                "message": "Analysis cancelled due to server shutdown"
            }))
            return
        
        # Convert to JSON-serializable format
        serializable_state = convert_to_serializable(final_state)
        serializable_decision = convert_to_serializable(decision)
        
        # Get recommendation from database using the session ID
        final_recommendation = get_recommendation_from_database(graph.current_session_id)

        # Send completion status with recommendation (if not shutting down)
        if not shutdown_event.is_set():
            await manager.broadcast(json.dumps({
                "type": "analysis_complete",
                "final_state": serializable_state,
                "decision": serializable_decision,
                "recommendation": final_recommendation
            }))

        # Results are automatically saved to database by TradingAgentsGraph
        logger.info(f"Analysis completed for {request.ticker} - results saved to database")

    except asyncio.CancelledError:
        logger.info("Background analysis cancelled due to shutdown")
        if not shutdown_event.is_set():
            await manager.broadcast(json.dumps({
                "type": "analysis_cancelled",
                "message": "Analysis was cancelled"
            }))
    except Exception as e:
        error_message = f"Analysis failed: {str(e)}"
        logger.error(f"Error in background analysis: {error_message}")
        traceback_module = get_traceback()
        logger.error(f"Traceback: {traceback_module.format_exc()}")
        
        # Only send error message if not shutting down
        if not shutdown_event.is_set():
            await manager.broadcast(json.dumps({
                "type": "error",
                "message": error_message
            }))

@app.get("/api/analyst-options")
async def get_analyst_options():
    """Get available analyst options"""
    return {
        "analysts": [
            {"value": "market", "label": "Market Analyst"},
            {"value": "social", "label": "Social Media Analyst"},
            {"value": "news", "label": "News Analyst"},
            {"value": "fundamentals", "label": "Fundamentals Analyst"}
        ]
    }

@app.get("/api/llm-providers")
async def get_llm_providers():
    """Get available LLM providers and their models"""
    return {
        "providers": {
            "openai": {
                "url": "https://api.openai.com/v1",
                "shallow_models": [
                    {"value": "gpt-4o-mini", "label": "GPT-4o-mini - Fast and efficient"},
                    {"value": "gpt-4.1-nano", "label": "GPT-4.1-nano - Ultra-lightweight"},
                    {"value": "gpt-4.1-mini", "label": "GPT-4.1-mini - Compact model"},
                    {"value": "gpt-4o", "label": "GPT-4o - Standard model"}
                ],
                "deep_models": [
                    {"value": "gpt-4.1-nano", "label": "GPT-4.1-nano - Ultra-lightweight"},
                    {"value": "gpt-4.1-mini", "label": "GPT-4.1-mini - Compact model"},
                    {"value": "gpt-4o", "label": "GPT-4o - Standard model"},
                    {"value": "o4-mini", "label": "o4-mini - Specialized reasoning"},
                    {"value": "o3-mini", "label": "o3-mini - Advanced reasoning"},
                    {"value": "o3", "label": "o3 - Full advanced reasoning"},
                    {"value": "o1", "label": "o1 - Premier reasoning"}
                ]
            },
            "anthropic": {
                "url": "https://api.anthropic.com/",
                "shallow_models": [
                    {"value": "claude-3-5-haiku-latest", "label": "Claude Haiku 3.5 - Fast inference"},
                    {"value": "claude-3-5-sonnet-latest", "label": "Claude Sonnet 3.5 - Highly capable"},
                    {"value": "claude-3-7-sonnet-latest", "label": "Claude Sonnet 3.7 - Exceptional reasoning"},
                    {"value": "claude-sonnet-4-0", "label": "Claude Sonnet 4 - High performance"}
                ],
                "deep_models": [
                    {"value": "claude-3-5-haiku-latest", "label": "Claude Haiku 3.5 - Fast inference"},
                    {"value": "claude-3-5-sonnet-latest", "label": "Claude Sonnet 3.5 - Highly capable"},
                    {"value": "claude-3-7-sonnet-latest", "label": "Claude Sonnet 3.7 - Exceptional reasoning"},
                    {"value": "claude-sonnet-4-0", "label": "Claude Sonnet 4 - High performance"},
                    {"value": "claude-opus-4-0", "label": "Claude Opus 4 - Most powerful"}
                ]
            },
            "google": {
                "url": "https://generativelanguage.googleapis.com/v1",
                "shallow_models": [
                    {"value": "gemini-2.0-flash-lite", "label": "Gemini 2.0 Flash-Lite - Cost efficient"},
                    {"value": "gemini-2.0-flash", "label": "Gemini 2.0 Flash - Next generation"},
                    {"value": "gemini-2.5-flash-preview-05-20", "label": "Gemini 2.5 Flash - Adaptive thinking"}
                ],
                "deep_models": [
                    {"value": "gemini-2.0-flash-lite", "label": "Gemini 2.0 Flash-Lite - Cost efficient"},
                    {"value": "gemini-2.0-flash", "label": "Gemini 2.0 Flash - Next generation"},
                    {"value": "gemini-2.5-flash-preview-05-20", "label": "Gemini 2.5 Flash - Adaptive thinking"},
                    {"value": "gemini-2.5-pro-preview-06-05", "label": "Gemini 2.5 Pro"}
                ]
            }
        }
    }

@app.get("/api/research-depth-options")
async def get_research_depth_options():
    """Get research depth options"""
    return {
        "options": [
            {"value": 1, "label": "Shallow - Quick research, few debate rounds"},
            {"value": 3, "label": "Medium - Moderate debate rounds"},
            {"value": 5, "label": "Deep - Comprehensive research, in-depth debate"}
        ]
    }


@app.get("/api/sessions/{ticker}/{date}")
async def get_session_info(ticker: str, date: str):
    """Get session information and available reports for a ticker and date"""
    try:
        # Input validation
        import re
        
        if not re.match(r'^[A-Z]{1,5}$', ticker):
            logger.warning(f"Invalid ticker format: {ticker}")
            raise HTTPException(
                status_code=400,
                detail=f"Invalid ticker format: {ticker}. Must be 1-5 uppercase letters."
            )
        
        if not re.match(r'^\d{4}-\d{2}-\d{2}$', date):
            logger.warning(f"Invalid date format: {date}")
            raise HTTPException(
                status_code=400,
                detail=f"Invalid date format: {date}. Must be YYYY-MM-DD format."
            )
        
        service = report_retrieval_service()
        if not service:
            raise HTTPException(
                status_code=503,
                detail="Database service not available. Session information cannot be retrieved."
            )
        
        # Find session for ticker and date
        session_id = find_session_for_ticker_date(ticker, date)
        
        if not session_id:
            raise HTTPException(
                status_code=404,
                detail=f"No analysis session found for {ticker} on {date}"
            )
        
        # Get available reports for the session
        try:
            available_reports = service.get_available_reports(session_id)
            session_data = service.get_session_reports_safe(session_id)
            
            if not session_data['success']:
                raise HTTPException(
                    status_code=500,
                    detail=f"Failed to retrieve session data: {session_data['error']['message']}"
                )
            
            return {
                "session_id": session_id,
                "ticker": ticker,
                "date": date,
                "available_reports": available_reports,
                "session_summary": session_data['data']['summary'],
                "created_at": session_data['data']['created_at'],
                "updated_at": session_data['data']['updated_at']
            }
            
        except Exception as e:
            logger.error(f"Error retrieving session data: {e}")
            raise HTTPException(
                status_code=500,
                detail=f"Failed to retrieve session information: {str(e)}"
            )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error in get_session_info: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )


@app.get("/api/sessions/{ticker}")
async def get_ticker_sessions(ticker: str, limit: int = 10):
    """Get recent sessions for a ticker"""
    try:
        # Input validation
        import re
        
        if not re.match(r'^[A-Z]{1,5}$', ticker):
            logger.warning(f"Invalid ticker format: {ticker}")
            raise HTTPException(
                status_code=400,
                detail=f"Invalid ticker format: {ticker}. Must be 1-5 uppercase letters."
            )
        
        if limit < 1 or limit > 100:
            raise HTTPException(
                status_code=400,
                detail="Limit must be between 1 and 100"
            )
        
        service = report_retrieval_service()
        if not service:
            raise HTTPException(
                status_code=503,
                detail="Database service not available. Session information cannot be retrieved."
            )
        
        try:
            sessions = service.get_sessions_by_ticker(ticker, limit)
            
            return {
                "ticker": ticker,
                "sessions": sessions,
                "total_found": len(sessions)
            }
            
        except Exception as e:
            logger.error(f"Error retrieving sessions for ticker {ticker}: {e}")
            raise HTTPException(
                status_code=500,
                detail=f"Failed to retrieve sessions: {str(e)}"
            )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error in get_ticker_sessions: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )

@app.get("/api/reports/{ticker}/{date}/{agent}", response_model=ReportResponse)
async def get_agent_report(ticker: str, date: str, agent: str):
    """Get the report content for a specific agent"""
    try:
        # Input validation
        import re
        
        # Validate ticker format (1-5 uppercase letters)
        if not re.match(r'^[A-Z]{1,5}$', ticker):
            logger.warning(f"Invalid ticker format: {ticker}")
            raise HTTPException(
                status_code=400,
                detail=f"Invalid ticker format: {ticker}. Must be 1-5 uppercase letters."
            )
        
        # Validate date format (YYYY-MM-DD)
        if not re.match(r'^\d{4}-\d{2}-\d{2}$', date):
            logger.warning(f"Invalid date format: {date}")
            raise HTTPException(
                status_code=400,
                detail=f"Invalid date format: {date}. Must be YYYY-MM-DD format."
            )
        
        # Convert agent key to full agent name if needed
        original_agent = agent
        if agent in AGENT_KEY_TO_NAME_MAPPING:
            agent = AGENT_KEY_TO_NAME_MAPPING[agent]
            logger.debug(f"🔄 Converted agent key '{original_agent}' to '{agent}'")
        
        # Validate agent name using database schema
        classes = get_report_retrieval_classes()
        AgentReportSchema = classes['AgentReportSchema']
        
        if not AgentReportSchema.is_valid_agent_type(agent):
            logger.warning(f"Unknown agent: {original_agent} -> {agent}")
            valid_agents = AgentReportSchema.get_all_agent_types()
            raise HTTPException(
                status_code=400, 
                detail=f"Unknown agent: {original_agent}. Valid agents: {valid_agents}"
            )
        
        logger.info(f"📊 Retrieving report for {agent} - {ticker}/{date}")
        
        # Database-only retrieval
        service = report_retrieval_service()
        if not service:
            raise HTTPException(
                status_code=503,
                detail="Database service not available. Please check configuration."
            )
        
        logger.debug("🗄️ Retrieving from database")
        response = load_report_from_database(ticker, date, agent)
        
        if response.success:
            logger.info(f"✅ Successfully retrieved {agent} report from database")
        else:
            logger.warning(f"❌ Failed to retrieve {agent} report: {response.message}")
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        error_msg = f"Internal server error while loading report: {str(e)}"
        logger.error(f"❌ {error_msg}")
        traceback_module = get_traceback()
        logger.error(f"Traceback: {traceback_module.format_exc()}")
        
        # Log structured error information for debugging
        logger.error(f"Error context - Ticker: {ticker}, Date: {date}, Agent: {agent}")
        logger.error(f"Database service available: {report_retrieval_service() is not None}")
        
        raise HTTPException(status_code=500, detail=error_msg)


@app.get("/api/final-analysis/{ticker}/{date}")
async def get_final_analysis(ticker: str, date: str):
    """Get the final trading analysis for a ticker and date"""
    try:
        # Input validation
        import re
        
        if not re.match(r'^[A-Z]{1,5}$', ticker):
            logger.warning(f"Invalid ticker format: {ticker}")
            raise HTTPException(
                status_code=400,
                detail=f"Invalid ticker format: {ticker}. Must be 1-5 uppercase letters."
            )
        
        if not re.match(r'^\d{4}-\d{2}-\d{2}$', date):
            logger.warning(f"Invalid date format: {date}")
            raise HTTPException(
                status_code=400,
                detail=f"Invalid date format: {date}. Must be YYYY-MM-DD format."
            )
        
        logger.info(f"📊 Retrieving final analysis for {ticker}/{date}")
        
        # Database-only approach
        service = report_retrieval_service()
        if not service:
            raise HTTPException(
                status_code=503,
                detail="Database service not available. Please check configuration."
            )
        
        # Find session for ticker and date
        session_id = find_session_for_ticker_date(ticker, date)
        
        if not session_id:
            raise HTTPException(
                status_code=404,
                detail=f"No analysis session found for {ticker} on {date}"
            )
        
        # Get final analysis from database
        try:
            result = service.get_final_analysis_safe(session_id)
            
            if result['success']:
                analysis_data = result['data']
                return {
                    "success": True,
                    "ticker": ticker,
                    "date": date,
                    "session_id": session_id,
                    "final_analysis": analysis_data.get('final_analysis'),
                    "recommendation": analysis_data.get('recommendation', 'HOLD'),
                    "source": "database"
                }
            else:
                error_info = result['error']
                error_type = error_info.get('type', 'Unknown')
                
                if error_type == 'NotFoundError':
                    raise HTTPException(
                        status_code=404,
                        detail=f"Final analysis not yet available for {ticker} on {date}. Analysis may still be in progress."
                    )
                elif error_type == 'SessionNotFoundError':
                    raise HTTPException(
                        status_code=404,
                        detail=f"Analysis session not found for {ticker} on {date}"
                    )
                elif error_type == 'DatabaseConnectionError':
                    raise HTTPException(
                        status_code=503,
                        detail="Database connection failed. Please try again later."
                    )
                else:
                    raise HTTPException(
                        status_code=500,
                        detail=f"Failed to retrieve final decision: {error_info.get('message', 'Unknown error')}"
                    )
                    
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error retrieving final decision from database: {e}")
            raise HTTPException(
                status_code=500,
                detail=f"Failed to retrieve final decision: {str(e)}"
            )
        
    except HTTPException:
        raise
    except Exception as e:
        error_msg = f"Internal server error while retrieving final decision: {str(e)}"
        logger.error(f"❌ {error_msg}")
        traceback_module = get_traceback()
        logger.error(f"Traceback: {traceback_module.format_exc()}")
        
        # Log structured error information for debugging
        logger.error(f"Error context - Ticker: {ticker}, Date: {date}")
        logger.error(f"Database service available: {report_retrieval_service() is not None}")
        
        raise HTTPException(status_code=500, detail=error_msg)


@app.get("/api/reports/{ticker}/{date}")
async def get_all_reports(ticker: str, date: str):
    """Get all available reports for a ticker and date"""
    try:
        # Input validation
        import re
        
        if not re.match(r'^[A-Z]{1,5}$', ticker):
            logger.warning(f"Invalid ticker format: {ticker}")
            raise HTTPException(
                status_code=400,
                detail=f"Invalid ticker format: {ticker}. Must be 1-5 uppercase letters."
            )
        
        if not re.match(r'^\d{4}-\d{2}-\d{2}$', date):
            logger.warning(f"Invalid date format: {date}")
            raise HTTPException(
                status_code=400,
                detail=f"Invalid date format: {date}. Must be YYYY-MM-DD format."
            )
        
        logger.info(f"📊 Retrieving all reports for {ticker}/{date}")
        
        service = report_retrieval_service()
        if not service:
            raise HTTPException(
                status_code=503,
                detail="Database service not available. Cannot retrieve complete session data."
            )
        
        # Find session for ticker and date
        session_id = find_session_for_ticker_date(ticker, date)
        
        if not session_id:
            raise HTTPException(
                status_code=404,
                detail=f"No analysis session found for {ticker} on {date}"
            )
        
        # Get complete session data
        try:
            result = service.get_session_reports_safe(session_id)
            
            if result['success']:
                session_data = result['data']
                return {
                    "success": True,
                    "ticker": ticker,
                    "date": date,
                    "session_id": session_id,
                    "reports": session_data['agent_reports'],
                    "final_analysis": session_data.get('final_analysis'),
                    "recommendation": session_data.get('recommendation'),
                    "summary": session_data['summary'],
                    "created_at": session_data['created_at'],
                    "updated_at": session_data['updated_at']
                }
            else:
                error_info = result['error']
                error_type = error_info.get('type', 'Unknown')
                
                if error_type == 'SessionNotFoundError':
                    raise HTTPException(
                        status_code=404,
                        detail=f"Analysis session not found for {ticker} on {date}"
                    )
                elif error_type == 'DatabaseConnectionError':
                    raise HTTPException(
                        status_code=503,
                        detail="Database connection failed. Please try again later."
                    )
                else:
                    raise HTTPException(
                        status_code=500,
                        detail=f"Failed to retrieve session data: {error_info.get('message', 'Unknown error')}"
                    )
                    
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error retrieving session data from database: {e}")
            raise HTTPException(
                status_code=500,
                detail=f"Failed to retrieve session data: {str(e)}"
            )
        
    except HTTPException:
        raise
    except Exception as e:
        error_msg = f"Internal server error while retrieving session data: {str(e)}"
        logger.error(f"❌ {error_msg}")
        traceback_module = get_traceback()
        logger.error(f"Traceback: {traceback_module.format_exc()}")
        
        # Log structured error information for debugging
        logger.error(f"Error context - Ticker: {ticker}, Date: {date}")
        logger.error(f"Database service available: {report_retrieval_service() is not None}")
        
        raise HTTPException(status_code=500, detail=error_msg)

if __name__ == "__main__":
    import uvicorn
    # Use Railway's PORT environment variable, fallback to 8000 for local development
    port = int(os.environ.get("PORT", 8000))
    # Bind to 0.0.0.0 to accept connections from Railway's proxy
    uvicorn.run(app, host="0.0.0.0", port=port)