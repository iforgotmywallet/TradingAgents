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
import traceback
import logging
from dotenv import load_dotenv

# Load environment variables first
load_dotenv()

# Add the parent directory to the path to import tradingagents
sys.path.append(str(Path(__file__).parent.parent))

try:
    from tradingagents.graph.trading_graph import TradingAgentsGraph
    from tradingagents.default_config import DEFAULT_CONFIG
    from tradingagents.storage.report_retrieval import ReportRetrievalService, ReportRetrievalError, ReportNotFoundError, SessionNotFoundError, DatabaseConnectionError
    from tradingagents.storage.neon_config import NeonConfig
    from tradingagents.storage.session_utils import generate_session_id, validate_session_id, get_session_ticker, get_session_date
    from tradingagents.storage.agent_validation import AgentValidationError
    from tradingagents.storage.schema import AgentReportSchema
except ImportError as e:
    print(f"❌ Import error: {e}")
    print("Make sure you're running from the TradingAgents root directory")
    sys.exit(1)

# Configure logging for debugging report retrieval issues
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Verify API keys are loaded
print(f"🔑 OpenAI API Key loaded: {'Yes' if os.getenv('OPENAI_API_KEY') else 'No'}")
print(f"🔑 Finnhub API Key loaded: {'Yes' if os.getenv('FINNHUB_API_KEY') else 'No'}")

# Initialize report retrieval service (required for database-only operation)
try:
    neon_config = NeonConfig()
    report_retrieval_service = ReportRetrievalService(neon_config)
    logger.info("✅ Report retrieval service initialized successfully")
except Exception as e:
    logger.error(f"❌ Failed to initialize report retrieval service: {e}")
    logger.error("Database connection is required for operation")
    report_retrieval_service = None

app = FastAPI(title="TradingAgents Web App", version="1.0.0")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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
    logger.error(f"Traceback: {traceback.format_exc()}")
    
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

# Mount static files
static_dir = Path(__file__).parent / "static"
app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

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

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def send_personal_message(self, message: str, websocket: WebSocket):
        try:
            await websocket.send_text(message)
        except Exception as e:
            print(f"Error sending personal message: {e}")
            self.disconnect(websocket)

    async def broadcast(self, message: str):
        disconnected = []
        for connection in self.active_connections:
            try:
                await connection.send_text(message)
            except Exception as e:
                print(f"Error broadcasting to connection: {e}")
                disconnected.append(connection)
        
        # Remove disconnected connections
        for conn in disconnected:
            self.disconnect(conn)

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
    if not report_retrieval_service or not session_id:
        logger.warning("Report retrieval service not available or no session ID provided")
        return "HOLD"
    
    try:
        # Get final analysis which includes recommendation
        result = report_retrieval_service.get_final_analysis_safe(session_id)
        
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
    if not report_retrieval_service:
        return None
    
    try:
        # Get recent sessions for the ticker
        sessions = report_retrieval_service.get_sessions_by_ticker(ticker.upper(), limit=100)
        
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
        result = report_retrieval_service.get_agent_report_safe(session_id, agent)
        
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
    """Health check endpoint"""
    health_status = {
        "status": "healthy", 
        "message": "TradingAgents Web App is running",
        "database": "not_configured"
    }
    
    # Check database health if available
    if report_retrieval_service:
        try:
            db_health = report_retrieval_service.health_check()
            health_status["database"] = "healthy" if db_health["healthy"] else "unhealthy"
            if not db_health["healthy"]:
                health_status["database_error"] = db_health.get("error", "Unknown database error")
        except Exception as e:
            health_status["database"] = "error"
            health_status["database_error"] = str(e)
    
    return health_status


@app.get("/api/database/health")
async def database_health_check():
    """Detailed database health check endpoint"""
    if not report_retrieval_service:
        raise HTTPException(
            status_code=503,
            detail="Database service not configured. Check environment variables."
        )
    
    try:
        health_status = report_retrieval_service.health_check()
        
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
    html_file = Path(__file__).parent / "static" / "index.html"
    if not html_file.exists():
        raise HTTPException(status_code=404, detail="Index file not found")
    return FileResponse(str(html_file))

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            try:
                data = await websocket.receive_text()
                # Keep connection alive
                await websocket.send_text(json.dumps({"type": "ping", "message": "pong"}))
            except Exception as e:
                print(f"WebSocket error: {e}")
                break
    except WebSocketDisconnect:
        pass
    finally:
        manager.disconnect(websocket)

@app.post("/api/analyze")
async def start_analysis(request: AnalysisRequest):
    """Start the trading analysis process"""
    try:
        print(f"📊 Starting analysis for {request.ticker}")
        
        # Check for API keys based on provider
        api_key_error = check_api_keys(request.llm_provider)
        if api_key_error:
            raise HTTPException(status_code=400, detail=api_key_error)
        
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
        graph = TradingAgentsGraph(
            request.analysts, config=config, debug=True
        )
        print("Graph initialized successfully")

        # Start analysis in background
        print("Starting background analysis...")
        asyncio.create_task(run_analysis_background(graph, request))

        return {"status": "started", "message": "Analysis started successfully"}

    except HTTPException:
        raise
    except Exception as e:
        error_msg = f"Error starting analysis: {str(e)}"
        print(f"❌ {error_msg}")
        print(f"Traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=error_msg)

async def run_analysis_background(graph: TradingAgentsGraph, request: AnalysisRequest):
    """Run the analysis in the background and send updates via WebSocket"""
    try:
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
            # Market Analyst
            await asyncio.sleep(2)
            await manager.broadcast(json.dumps({
                "type": "agent_status",
                "agent": "Market Analyst",
                "status": "in_progress"
            }))
            
            await asyncio.sleep(3)
            await manager.broadcast(json.dumps({
                "type": "agent_status",
                "agent": "Market Analyst",
                "status": "completed"
            }))
            
            # Social Analyst
            await manager.broadcast(json.dumps({
                "type": "agent_status",
                "agent": "Social Analyst",
                "status": "in_progress"
            }))
            
            await asyncio.sleep(2)
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
        
        # Run the actual analysis
        final_state, decision = graph.propagate(request.ticker, request.analysis_date)
        
        # Wait for progress updates to complete
        await progress_task

        # Convert to JSON-serializable format
        serializable_state = convert_to_serializable(final_state)
        serializable_decision = convert_to_serializable(decision)
        
        # Get recommendation from database using the session ID
        final_recommendation = get_recommendation_from_database(graph.current_session_id)

        # Send completion status with recommendation
        await manager.broadcast(json.dumps({
            "type": "analysis_complete",
            "final_state": serializable_state,
            "decision": serializable_decision,
            "recommendation": final_recommendation
        }))

        # Results are automatically saved to database by TradingAgentsGraph
        logger.info(f"Analysis completed for {request.ticker} - results saved to database")

    except Exception as e:
        error_message = f"Analysis failed: {str(e)}"
        print(f"Error in background analysis: {error_message}")
        print(f"Traceback: {traceback.format_exc()}")
        
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
        
        if not report_retrieval_service:
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
            available_reports = report_retrieval_service.get_available_reports(session_id)
            session_data = report_retrieval_service.get_session_reports_safe(session_id)
            
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
        
        if not report_retrieval_service:
            raise HTTPException(
                status_code=503,
                detail="Database service not available. Session information cannot be retrieved."
            )
        
        try:
            sessions = report_retrieval_service.get_sessions_by_ticker(ticker, limit)
            
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
        if not AgentReportSchema.is_valid_agent_type(agent):
            logger.warning(f"Unknown agent: {original_agent} -> {agent}")
            valid_agents = AgentReportSchema.get_all_agent_types()
            raise HTTPException(
                status_code=400, 
                detail=f"Unknown agent: {original_agent}. Valid agents: {valid_agents}"
            )
        
        logger.info(f"📊 Retrieving report for {agent} - {ticker}/{date}")
        
        # Database-only retrieval
        if not report_retrieval_service:
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
        logger.error(f"Traceback: {traceback.format_exc()}")
        
        # Log structured error information for debugging
        logger.error(f"Error context - Ticker: {ticker}, Date: {date}, Agent: {agent}")
        logger.error(f"Database service available: {report_retrieval_service is not None}")
        
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
        if not report_retrieval_service:
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
            result = report_retrieval_service.get_final_analysis_safe(session_id)
            
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
        logger.error(f"Traceback: {traceback.format_exc()}")
        
        # Log structured error information for debugging
        logger.error(f"Error context - Ticker: {ticker}, Date: {date}")
        logger.error(f"Database service available: {report_retrieval_service is not None}")
        
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
        
        if not report_retrieval_service:
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
            result = report_retrieval_service.get_session_reports_safe(session_id)
            
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
        logger.error(f"Traceback: {traceback.format_exc()}")
        
        # Log structured error information for debugging
        logger.error(f"Error context - Ticker: {ticker}, Date: {date}")
        logger.error(f"Database service available: {report_retrieval_service is not None}")
        
        raise HTTPException(status_code=500, detail=error_msg)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)