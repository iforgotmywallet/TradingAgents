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
from dotenv import load_dotenv

# Load environment variables first
from dotenv import load_dotenv
load_dotenv()

# Add the parent directory to the path to import tradingagents
sys.path.append(str(Path(__file__).parent.parent))

try:
    from tradingagents.graph.trading_graph import TradingAgentsGraph
    from tradingagents.default_config import DEFAULT_CONFIG
    from cli.models import AnalystType
except ImportError as e:
    print(f"❌ Import error: {e}")
    print("Make sure you're running from the TradingAgents root directory")
    sys.exit(1)

# Verify API keys are loaded
print(f"🔑 OpenAI API Key loaded: {'Yes' if os.getenv('OPENAI_API_KEY') else 'No'}")
print(f"🔑 Finnhub API Key loaded: {'Yes' if os.getenv('FINNHUB_API_KEY') else 'No'}")

app = FastAPI(title="TradingAgents Web App", version="1.0.0")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
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

def extract_recommendation(decision_text: str) -> str:
    """Extract BUY/SELL/HOLD recommendation from decision text"""
    if not decision_text:
        return "HOLD"
    
    decision_upper = str(decision_text).upper()
    
    # Look for explicit recommendations
    if "BUY" in decision_upper and "SELL" not in decision_upper:
        return "BUY"
    elif "SELL" in decision_upper:
        return "SELL"
    elif "HOLD" in decision_upper:
        return "HOLD"
    
    # Look for other positive/negative indicators
    positive_indicators = ["BULLISH", "POSITIVE", "UPWARD", "LONG", "INVEST", "PURCHASE"]
    negative_indicators = ["BEARISH", "NEGATIVE", "DOWNWARD", "SHORT", "AVOID", "DECLINE"]
    
    positive_count = sum(1 for indicator in positive_indicators if indicator in decision_upper)
    negative_count = sum(1 for indicator in negative_indicators if indicator in decision_upper)
    
    if positive_count > negative_count:
        return "BUY"
    elif negative_count > positive_count:
        return "SELL"
    else:
        return "HOLD"

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "message": "TradingAgents Web App is running"}

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

        # Create results directory
        results_dir = Path(config["results_dir"]) / request.ticker / request.analysis_date
        results_dir.mkdir(parents=True, exist_ok=True)

        # Initialize the graph
        print("Initializing TradingAgentsGraph...")
        graph = TradingAgentsGraph(
            request.analysts, config=config, debug=True
        )
        print("Graph initialized successfully")

        # Start analysis in background
        print("Starting background analysis...")
        asyncio.create_task(run_analysis_background(graph, request, results_dir))

        return {"status": "started", "message": "Analysis started successfully"}

    except HTTPException:
        raise
    except Exception as e:
        error_msg = f"Error starting analysis: {str(e)}"
        print(f"❌ {error_msg}")
        print(f"Traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=error_msg)

async def run_analysis_background(graph: TradingAgentsGraph, request: AnalysisRequest, results_dir: Path):
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
        
        # Extract final recommendation from decision
        final_recommendation = extract_recommendation(serializable_decision)

        # Send completion status with recommendation
        await manager.broadcast(json.dumps({
            "type": "analysis_complete",
            "final_state": serializable_state,
            "decision": serializable_decision,
            "recommendation": final_recommendation
        }))

        # Save results
        with open(results_dir / "final_decision.json", "w") as f:
            json.dump({
                "final_state": serializable_state, 
                "decision": serializable_decision,
                "recommendation": final_recommendation
            }, f, indent=2, default=str)

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

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)