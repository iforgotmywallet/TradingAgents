# TradingAgents/graph/trading_graph.py

import os
from pathlib import Path
import json
import logging
from datetime import date
from typing import Dict, Any, Tuple, List, Optional

from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic
from langchain_google_genai import ChatGoogleGenerativeAI

from langgraph.prebuilt import ToolNode

from tradingagents.agents import *
from tradingagents.default_config import DEFAULT_CONFIG
from tradingagents.agents.utils.memory import FinancialSituationMemory
from tradingagents.agents.utils.agent_states import (
    AgentState,
    InvestDebateState,
    RiskDebateState,
)
from tradingagents.dataflows.interface import set_config
from tradingagents.storage.report_storage import ReportStorageService, ReportStorageError
from tradingagents.storage.neon_config import NeonConfig

from .conditional_logic import ConditionalLogic
from .setup import GraphSetup
from .propagation import Propagator
from .reflection import Reflector
from .signal_processing import SignalProcessor

logger = logging.getLogger(__name__)


class TradingAgentsGraph:
    """Main class that orchestrates the trading agents framework."""

    def __init__(
        self,
        selected_analysts=["market", "social", "news", "fundamentals"],
        debug=False,
        config: Dict[str, Any] = None,
    ):
        """Initialize the trading agents graph and components.

        Args:
            selected_analysts: List of analyst types to include
            debug: Whether to run in debug mode
            config: Configuration dictionary. If None, uses default config
        """
        self.debug = debug
        self.config = config or DEFAULT_CONFIG

        # Update the interface's config
        set_config(self.config)

        # Create necessary directories
        os.makedirs(
            os.path.join(self.config["project_dir"], "dataflows/data_cache"),
            exist_ok=True,
        )

        # Initialize storage service
        try:
            self.storage_service = ReportStorageService()
            logger.info("Initialized report storage service")
        except Exception as e:
            logger.warning(f"Failed to initialize storage service: {e}. Reports will not be saved to database.")
            self.storage_service = None

        # Initialize LLMs
        if self.config["llm_provider"].lower() == "openai" or self.config["llm_provider"] == "ollama" or self.config["llm_provider"] == "openrouter":
            self.deep_thinking_llm = ChatOpenAI(model=self.config["deep_think_llm"], base_url=self.config["backend_url"])
            self.quick_thinking_llm = ChatOpenAI(model=self.config["quick_think_llm"], base_url=self.config["backend_url"])
        elif self.config["llm_provider"].lower() == "anthropic":
            self.deep_thinking_llm = ChatAnthropic(model=self.config["deep_think_llm"], base_url=self.config["backend_url"])
            self.quick_thinking_llm = ChatAnthropic(model=self.config["quick_think_llm"], base_url=self.config["backend_url"])
        elif self.config["llm_provider"].lower() == "google":
            self.deep_thinking_llm = ChatGoogleGenerativeAI(model=self.config["deep_think_llm"])
            self.quick_thinking_llm = ChatGoogleGenerativeAI(model=self.config["quick_think_llm"])
        else:
            raise ValueError(f"Unsupported LLM provider: {self.config['llm_provider']}")
        
        self.toolkit = Toolkit(config=self.config)

        # Initialize memories
        self.bull_memory = FinancialSituationMemory("bull_memory", self.config)
        self.bear_memory = FinancialSituationMemory("bear_memory", self.config)
        self.trader_memory = FinancialSituationMemory("trader_memory", self.config)
        self.invest_judge_memory = FinancialSituationMemory("invest_judge_memory", self.config)
        self.risk_manager_memory = FinancialSituationMemory("risk_manager_memory", self.config)

        # Create tool nodes
        self.tool_nodes = self._create_tool_nodes()

        # Initialize components
        self.conditional_logic = ConditionalLogic()
        self.graph_setup = GraphSetup(
            self.quick_thinking_llm,
            self.deep_thinking_llm,
            self.toolkit,
            self.tool_nodes,
            self.bull_memory,
            self.bear_memory,
            self.trader_memory,
            self.invest_judge_memory,
            self.risk_manager_memory,
            self.conditional_logic,
            storage_service=self.storage_service,  # Pass storage service to graph setup
        )

        self.propagator = Propagator()
        self.reflector = Reflector(self.quick_thinking_llm)
        self.signal_processor = SignalProcessor(self.quick_thinking_llm)

        # State tracking
        self.curr_state = None
        self.ticker = None
        self.current_session_id = None  # Track current analysis session
        self.log_states_dict = {}  # date to full state dict

        # Set up the graph
        self.graph = self.graph_setup.setup_graph(selected_analysts)

    def _create_tool_nodes(self) -> Dict[str, ToolNode]:
        """Create tool nodes for different data sources."""
        return {
            "market": ToolNode(
                [
                    # online tools
                    self.toolkit.get_YFin_data_online,
                    self.toolkit.get_stockstats_indicators_report_online,
                    # offline tools
                    self.toolkit.get_YFin_data,
                    self.toolkit.get_stockstats_indicators_report,
                ]
            ),
            "social": ToolNode(
                [
                    # online tools
                    self.toolkit.get_stock_news_openai,
                    # offline tools
                    self.toolkit.get_reddit_stock_info,
                ]
            ),
            "news": ToolNode(
                [
                    # online tools
                    self.toolkit.get_global_news_openai,
                    self.toolkit.get_google_news,
                    # offline tools
                    self.toolkit.get_finnhub_news,
                    self.toolkit.get_reddit_news,
                ]
            ),
            "fundamentals": ToolNode(
                [
                    # online tools
                    self.toolkit.get_fundamentals_openai,
                    # offline tools
                    self.toolkit.get_finnhub_company_insider_sentiment,
                    self.toolkit.get_finnhub_company_insider_transactions,
                    self.toolkit.get_simfin_balance_sheet,
                    self.toolkit.get_simfin_cashflow,
                    self.toolkit.get_simfin_income_stmt,
                ]
            ),
        }

    def propagate(self, company_name, trade_date):
        """Run the trading agents graph for a company on a specific date."""

        self.ticker = company_name

        # Create database session at the start of analysis
        if self.storage_service:
            try:
                self.current_session_id = self.storage_service.create_session_sync(
                    company_name, str(trade_date)
                )
                # Pass session ID to graph setup for storage hooks
                self.graph_setup.set_session_id(self.current_session_id)
                logger.info(f"Created analysis session: {self.current_session_id}")
            except ReportStorageError as e:
                logger.error(f"Failed to create session: {e}")
                self.current_session_id = None

        # Initialize state
        init_agent_state = self.propagator.create_initial_state(
            company_name, trade_date
        )
        args = self.propagator.get_graph_args()

        if self.debug:
            # Debug mode with tracing
            trace = []
            for chunk in self.graph.stream(init_agent_state, **args):
                if len(chunk["messages"]) == 0:
                    pass
                else:
                    chunk["messages"][-1].pretty_print()
                    trace.append(chunk)
                            # Save reports after each agent completes (debug mode only)
                    # Note: In normal mode, reports are saved via storage hooks in agent wrappers
                    if self.storage_service:
                        self._save_agent_reports_from_state(chunk)

            final_state = trace[-1]
        else:
            # Standard mode without tracing
            final_state = self.graph.invoke(init_agent_state, **args)

        # Store current state for reflection
        self.curr_state = final_state

        # Save all final reports to database
        self._save_final_reports(final_state)

        # Log state
        self._log_state(trade_date, final_state)

        # Return decision and processed signal
        return final_state, self.process_signal(final_state["final_trade_decision"])

    def _log_state(self, trade_date, final_state):
        """Log the final state to a JSON file."""
        self.log_states_dict[str(trade_date)] = {
            "company_of_interest": final_state["company_of_interest"],
            "trade_date": final_state["trade_date"],
            "market_report": final_state["market_report"],
            "sentiment_report": final_state["sentiment_report"],
            "news_report": final_state["news_report"],
            "fundamentals_report": final_state["fundamentals_report"],
            "investment_debate_state": {
                "bull_history": final_state["investment_debate_state"]["bull_history"],
                "bear_history": final_state["investment_debate_state"]["bear_history"],
                "history": final_state["investment_debate_state"]["history"],
                "current_response": final_state["investment_debate_state"][
                    "current_response"
                ],
                "judge_decision": final_state["investment_debate_state"][
                    "judge_decision"
                ],
            },
            "trader_investment_decision": final_state["trader_investment_plan"],
            "risk_debate_state": {
                "risky_history": final_state["risk_debate_state"]["risky_history"],
                "safe_history": final_state["risk_debate_state"]["safe_history"],
                "neutral_history": final_state["risk_debate_state"]["neutral_history"],
                "history": final_state["risk_debate_state"]["history"],
                "judge_decision": final_state["risk_debate_state"]["judge_decision"],
            },
            "investment_plan": final_state["investment_plan"],
            "final_trade_decision": final_state["final_trade_decision"],
        }

        # Save to file
        directory = Path(f"eval_results/{self.ticker}/TradingAgentsStrategy_logs/")
        directory.mkdir(parents=True, exist_ok=True)

        with open(
            f"eval_results/{self.ticker}/TradingAgentsStrategy_logs/full_states_log_{trade_date}.json",
            "w",
        ) as f:
            json.dump(self.log_states_dict, f, indent=4)

    def reflect_and_remember(self, returns_losses):
        """Reflect on decisions and update memory based on returns."""
        self.reflector.reflect_bull_researcher(
            self.curr_state, returns_losses, self.bull_memory
        )
        self.reflector.reflect_bear_researcher(
            self.curr_state, returns_losses, self.bear_memory
        )
        self.reflector.reflect_trader(
            self.curr_state, returns_losses, self.trader_memory
        )
        self.reflector.reflect_invest_judge(
            self.curr_state, returns_losses, self.invest_judge_memory
        )
        self.reflector.reflect_risk_manager(
            self.curr_state, returns_losses, self.risk_manager_memory
        )

    def process_signal(self, full_signal):
        """Process a signal to extract the core decision."""
        return self.signal_processor.process_signal(full_signal)

    def _save_agent_reports_from_state(self, state_chunk):
        """Save individual agent reports from state chunk to database."""
        if not self.storage_service or not self.current_session_id:
            return

        try:
            # Map state fields to agent types for database storage
            report_mappings = {
                'market_report': 'Market Analyst',
                'sentiment_report': 'Social Analyst', 
                'news_report': 'News Analyst',
                'fundamentals_report': 'Fundamentals Analyst',
                'investment_plan': 'Research Manager',
                'trader_investment_plan': 'Trader'
            }

            # Save individual agent reports if they exist and are not empty
            for state_field, agent_type in report_mappings.items():
                if state_field in state_chunk and state_chunk[state_field]:
                    report_content = state_chunk[state_field].strip()
                    if report_content:
                        try:
                            self.storage_service.save_agent_report_sync(
                                self.current_session_id, agent_type, report_content
                            )
                            logger.debug(f"Saved {agent_type} report to database")
                        except ReportStorageError as e:
                            logger.error(f"Failed to save {agent_type} report: {e}")

            # Handle debate states with multiple agents
            if 'investment_debate_state' in state_chunk:
                debate_state = state_chunk['investment_debate_state']
                
                # Save bull and bear researcher reports from debate history
                if 'bull_history' in debate_state and debate_state['bull_history']:
                    try:
                        self.storage_service.save_agent_report_sync(
                            self.current_session_id, 'Bull Researcher', debate_state['bull_history']
                        )
                        logger.debug("Saved Bull Researcher report to database")
                    except ReportStorageError as e:
                        logger.error(f"Failed to save Bull Researcher report: {e}")

                if 'bear_history' in debate_state and debate_state['bear_history']:
                    try:
                        self.storage_service.save_agent_report_sync(
                            self.current_session_id, 'Bear Researcher', debate_state['bear_history']
                        )
                        logger.debug("Saved Bear Researcher report to database")
                    except ReportStorageError as e:
                        logger.error(f"Failed to save Bear Researcher report: {e}")

            # Handle risk debate states
            if 'risk_debate_state' in state_chunk:
                risk_state = state_chunk['risk_debate_state']
                
                risk_mappings = {
                    'risky_history': 'Risky Analyst',
                    'safe_history': 'Safe Analyst', 
                    'neutral_history': 'Neutral Analyst'
                }
                
                for history_field, agent_type in risk_mappings.items():
                    if history_field in risk_state and risk_state[history_field]:
                        try:
                            self.storage_service.save_agent_report_sync(
                                self.current_session_id, agent_type, risk_state[history_field]
                            )
                            logger.debug(f"Saved {agent_type} report to database")
                        except ReportStorageError as e:
                            logger.error(f"Failed to save {agent_type} report: {e}")

        except Exception as e:
            logger.error(f"Error saving agent reports from state: {e}")

    def _save_final_reports(self, final_state):
        """Save final decision and analysis to database."""
        if not self.storage_service or not self.current_session_id:
            return

        try:
            # Save all individual agent reports from final state
            self._save_agent_reports_from_state(final_state)

            # Save final analysis and recommendation
            final_analysis = final_state.get('final_trade_decision', '')
            if final_analysis:
                # Extract recommendation from final analysis (BUY/SELL/HOLD)
                recommendation = self._extract_recommendation(final_analysis)
                
                try:
                    self.storage_service.save_final_analysis_sync(
                        self.current_session_id,
                        final_analysis,
                        recommendation
                    )
                    logger.info(f"Saved final analysis to database for session {self.current_session_id}")
                except ReportStorageError as e:
                    logger.error(f"Failed to save final analysis: {e}")

        except Exception as e:
            logger.error(f"Error saving final reports: {e}")

    def _extract_recommendation(self, final_analysis: str) -> str:
        """Extract BUY/SELL/HOLD recommendation from final analysis text with optimized precision focusing on summary section."""
        if not final_analysis:
            return 'HOLD'
        
        analysis_upper = final_analysis.upper()
        
        # Import regex for pattern matching
        import re
        
        # PRIORITY 1: Look for "In summary" section (highest priority)
        # This is where the final recommendation is typically stated
        summary_patterns = [
            r'\*\*IN\s+SUMMARY:\*\*\s*\*\*(\w+)\*\*',        # **In summary:** **HOLD**
            r'\*\*IN\s+SUMMARY[:\s]*\*\*\s*\*\*(\w+)\*\*',   # **In summary:** **HOLD** (flexible spacing)
            r'\*\*IN\s+SUMMARY[:\s]*\*\*[^*]*\*\*(\w+)\*\*', # **In summary:** ... **HOLD** (with text between)
            r'IN\s+SUMMARY[:\s]*\*\*(\w+)\*\*',              # In summary: **HOLD** (without bold summary)
            r'SUMMARY[:\s]*\*\*(\w+)\*\*',                   # Summary: **HOLD**
        ]
        
        for pattern in summary_patterns:
            matches = re.findall(pattern, analysis_upper)
            for match in matches:
                if match in ['BUY', 'SELL', 'HOLD']:
                    return match
        
        # PRIORITY 2: Look for explicit recommendation statements in the last portion of text
        # Focus on the last 500 characters where final recommendations are typically made
        last_section = analysis_upper[-500:] if len(analysis_upper) > 500 else analysis_upper
        
        final_recommendation_patterns = [
            r'MY\s+RECOMMENDATION\s+IS\s+TO\s+(\w+)',
            r'RECOMMENDATION\s+IS\s+TO\s+(\w+)',
            r'RECOMMEND\s+(\w+)',
            r'FINAL\s+RECOMMENDATION[:\s]*(\w+)',
            r'CONCLUSION[:\s]*(\w+)',
        ]
        
        for pattern in final_recommendation_patterns:
            matches = re.findall(pattern, last_section)
            for match in matches:
                if match in ['BUY', 'SELL', 'HOLD']:
                    return match
        
        # PRIORITY 3: Look for bolded recommendations in the last section
        bolded_matches = re.findall(r'\*\*(\w+)\*\*', last_section)
        for match in bolded_matches:
            if match in ['BUY', 'SELL', 'HOLD']:
                return match
        
        # PRIORITY 4: Look for contextual recommendations in the entire text
        buy_contexts = len(re.findall(r'(?:RECOMMEND|SUGGESTION|DECISION).*?BUY', analysis_upper))
        sell_contexts = len(re.findall(r'(?:RECOMMEND|SUGGESTION|DECISION).*?SELL', analysis_upper))
        hold_contexts = len(re.findall(r'(?:RECOMMEND|SUGGESTION|DECISION).*?HOLD', analysis_upper))
        
        # Return the most contextually relevant recommendation
        if hold_contexts > max(buy_contexts, sell_contexts):
            return 'HOLD'
        elif buy_contexts > sell_contexts:
            return 'BUY'
        elif sell_contexts > buy_contexts:
            return 'SELL'
        
        # PRIORITY 5: Fallback to careful word counting (standalone words only)
        buy_count = len(re.findall(r'\bBUY\b', analysis_upper))
        sell_count = len(re.findall(r'\bSELL\b', analysis_upper))
        hold_count = len(re.findall(r'\bHOLD\b', analysis_upper))
        
        # PRIORITY 6: Look for sentiment indicators only if no clear recommendation
        if max(buy_count, sell_count, hold_count) == 0:
            positive_indicators = ["BULLISH", "POSITIVE", "UPWARD", "LONG", "INVEST", "PURCHASE"]
            negative_indicators = ["BEARISH", "NEGATIVE", "DOWNWARD", "SHORT", "AVOID", "DECLINE"]
            
            positive_count = sum(1 for indicator in positive_indicators if indicator in analysis_upper)
            negative_count = sum(1 for indicator in negative_indicators if indicator in analysis_upper)
            
            if positive_count > negative_count:
                return 'BUY'
            elif negative_count > positive_count:
                return 'SELL'
        
        # Return the most frequent explicit recommendation
        if hold_count >= max(buy_count, sell_count):
            return 'HOLD'
        elif buy_count > sell_count:
            return 'BUY'
        else:
            return 'SELL'
