# TradingAgents/graph/setup.py

import logging
from typing import Dict, Any, Callable
from langchain_openai import ChatOpenAI
from langgraph.graph import END, StateGraph, START
from langgraph.prebuilt import ToolNode

from tradingagents.agents import *
from tradingagents.agents.utils.agent_states import AgentState
from tradingagents.agents.utils.agent_utils import Toolkit
from tradingagents.storage.report_storage import ReportStorageError

from .conditional_logic import ConditionalLogic

logger = logging.getLogger(__name__)


class GraphSetup:
    """Handles the setup and configuration of the agent graph."""

    def __init__(
        self,
        quick_thinking_llm: ChatOpenAI,
        deep_thinking_llm: ChatOpenAI,
        toolkit: Toolkit,
        tool_nodes: Dict[str, ToolNode],
        bull_memory,
        bear_memory,
        trader_memory,
        invest_judge_memory,
        risk_manager_memory,
        conditional_logic: ConditionalLogic,
        storage_service=None,
    ):
        """Initialize with required components."""
        self.quick_thinking_llm = quick_thinking_llm
        self.deep_thinking_llm = deep_thinking_llm
        self.toolkit = toolkit
        self.tool_nodes = tool_nodes
        self.bull_memory = bull_memory
        self.bear_memory = bear_memory
        self.trader_memory = trader_memory
        self.invest_judge_memory = invest_judge_memory
        self.risk_manager_memory = risk_manager_memory
        self.conditional_logic = conditional_logic
        self.storage_service = storage_service
        self.current_session_id = None  # Will be set by TradingAgentsGraph

    def set_session_id(self, session_id: str):
        """Set the current session ID for storage operations."""
        self.current_session_id = session_id

    def _create_storage_wrapper(self, agent_node: Callable, agent_type: str, report_field: str) -> Callable:
        """
        Create a wrapper around an agent node that saves reports to storage.
        
        Args:
            agent_node: The original agent node function
            agent_type: The agent type for database storage (e.g., 'Market Analyst')
            report_field: The state field containing the report (e.g., 'market_report')
            
        Returns:
            Wrapped agent node function
        """
        def wrapped_agent_node(state):
            # Call the original agent node
            result = agent_node(state)
            
            # Save report to database if storage service is available
            if (self.storage_service and self.current_session_id and 
                report_field in result and result[report_field]):
                
                report_content = result[report_field].strip()
                if report_content:
                    try:
                        self.storage_service.save_agent_report_sync(
                            self.current_session_id, agent_type, report_content
                        )
                        logger.debug(f"Saved {agent_type} report to database")
                    except ReportStorageError as e:
                        logger.error(f"Failed to save {agent_type} report: {e}")
                    except Exception as e:
                        logger.error(f"Unexpected error saving {agent_type} report: {e}")
            
            return result
        
        return wrapped_agent_node

    def _create_debate_storage_wrapper(self, agent_node: Callable, agent_type: str, 
                                     debate_field: str, history_field: str) -> Callable:
        """
        Create a wrapper for debate agents that saves their contributions to storage.
        
        Args:
            agent_node: The original agent node function
            agent_type: The agent type for database storage
            debate_field: The state field containing the debate state
            history_field: The field within debate state containing agent's history
            
        Returns:
            Wrapped agent node function
        """
        def wrapped_debate_node(state):
            # Call the original agent node
            result = agent_node(state)
            
            # Save debate contribution to database if available
            if (self.storage_service and self.current_session_id and 
                debate_field in result and result[debate_field]):
                
                debate_state = result[debate_field]
                if history_field in debate_state and debate_state[history_field]:
                    history_content = debate_state[history_field].strip()
                    if history_content:
                        try:
                            self.storage_service.save_agent_report_sync(
                                self.current_session_id, agent_type, history_content
                            )
                            logger.debug(f"Saved {agent_type} debate contribution to database")
                        except ReportStorageError as e:
                            logger.error(f"Failed to save {agent_type} debate contribution: {e}")
                        except Exception as e:
                            logger.error(f"Unexpected error saving {agent_type} debate contribution: {e}")
            
            return result
        
        return wrapped_debate_node

    def setup_graph(
        self, selected_analysts=["market", "social", "news", "fundamentals"]
    ):
        """Set up and compile the agent workflow graph.

        Args:
            selected_analysts (list): List of analyst types to include. Options are:
                - "market": Market analyst
                - "social": Social media analyst
                - "news": News analyst
                - "fundamentals": Fundamentals analyst
        """
        if len(selected_analysts) == 0:
            raise ValueError("Trading Agents Graph Setup Error: no analysts selected!")

        # Create analyst nodes with storage wrappers
        analyst_nodes = {}
        delete_nodes = {}
        tool_nodes = {}

        if "market" in selected_analysts:
            base_market_analyst = create_market_analyst(
                self.quick_thinking_llm, self.toolkit
            )
            analyst_nodes["market"] = self._create_storage_wrapper(
                base_market_analyst, "Market Analyst", "market_report"
            )
            delete_nodes["market"] = create_msg_delete()
            tool_nodes["market"] = self.tool_nodes["market"]

        if "social" in selected_analysts:
            base_social_analyst = create_social_media_analyst(
                self.quick_thinking_llm, self.toolkit
            )
            analyst_nodes["social"] = self._create_storage_wrapper(
                base_social_analyst, "Social Analyst", "sentiment_report"
            )
            delete_nodes["social"] = create_msg_delete()
            tool_nodes["social"] = self.tool_nodes["social"]

        if "news" in selected_analysts:
            base_news_analyst = create_news_analyst(
                self.quick_thinking_llm, self.toolkit
            )
            analyst_nodes["news"] = self._create_storage_wrapper(
                base_news_analyst, "News Analyst", "news_report"
            )
            delete_nodes["news"] = create_msg_delete()
            tool_nodes["news"] = self.tool_nodes["news"]

        if "fundamentals" in selected_analysts:
            base_fundamentals_analyst = create_fundamentals_analyst(
                self.quick_thinking_llm, self.toolkit
            )
            analyst_nodes["fundamentals"] = self._create_storage_wrapper(
                base_fundamentals_analyst, "Fundamentals Analyst", "fundamentals_report"
            )
            delete_nodes["fundamentals"] = create_msg_delete()
            tool_nodes["fundamentals"] = self.tool_nodes["fundamentals"]

        # Create researcher and manager nodes with storage wrappers
        base_bull_researcher = create_bull_researcher(
            self.quick_thinking_llm, self.bull_memory
        )
        bull_researcher_node = self._create_debate_storage_wrapper(
            base_bull_researcher, "Bull Researcher", "investment_debate_state", "bull_history"
        )
        
        base_bear_researcher = create_bear_researcher(
            self.quick_thinking_llm, self.bear_memory
        )
        bear_researcher_node = self._create_debate_storage_wrapper(
            base_bear_researcher, "Bear Researcher", "investment_debate_state", "bear_history"
        )
        
        base_research_manager = create_research_manager(
            self.deep_thinking_llm, self.invest_judge_memory
        )
        research_manager_node = self._create_storage_wrapper(
            base_research_manager, "Research Manager", "investment_plan"
        )
        
        base_trader = create_trader(self.quick_thinking_llm, self.trader_memory)
        trader_node = self._create_storage_wrapper(
            base_trader, "Trader", "trader_investment_plan"
        )

        # Create risk analysis nodes with storage wrappers
        base_risky_analyst = create_risky_debator(self.quick_thinking_llm)
        risky_analyst = self._create_debate_storage_wrapper(
            base_risky_analyst, "Risky Analyst", "risk_debate_state", "risky_history"
        )
        
        base_neutral_analyst = create_neutral_debator(self.quick_thinking_llm)
        neutral_analyst = self._create_debate_storage_wrapper(
            base_neutral_analyst, "Neutral Analyst", "risk_debate_state", "neutral_history"
        )
        
        base_safe_analyst = create_safe_debator(self.quick_thinking_llm)
        safe_analyst = self._create_debate_storage_wrapper(
            base_safe_analyst, "Safe Analyst", "risk_debate_state", "safe_history"
        )
        
        base_risk_manager = create_risk_manager(
            self.deep_thinking_llm, self.risk_manager_memory
        )
        risk_manager_node = self._create_storage_wrapper(
            base_risk_manager, "Portfolio Manager", "final_trade_decision"
        )

        # Create workflow
        workflow = StateGraph(AgentState)

        # Add analyst nodes to the graph
        for analyst_type, node in analyst_nodes.items():
            workflow.add_node(f"{analyst_type.capitalize()} Analyst", node)
            workflow.add_node(
                f"Msg Clear {analyst_type.capitalize()}", delete_nodes[analyst_type]
            )
            workflow.add_node(f"tools_{analyst_type}", tool_nodes[analyst_type])

        # Add other nodes
        workflow.add_node("Bull Researcher", bull_researcher_node)
        workflow.add_node("Bear Researcher", bear_researcher_node)
        workflow.add_node("Research Manager", research_manager_node)
        workflow.add_node("Trader", trader_node)
        workflow.add_node("Risky Analyst", risky_analyst)
        workflow.add_node("Neutral Analyst", neutral_analyst)
        workflow.add_node("Safe Analyst", safe_analyst)
        workflow.add_node("Risk Judge", risk_manager_node)

        # Define edges
        # Start with the first analyst
        first_analyst = selected_analysts[0]
        workflow.add_edge(START, f"{first_analyst.capitalize()} Analyst")

        # Connect analysts in sequence
        for i, analyst_type in enumerate(selected_analysts):
            current_analyst = f"{analyst_type.capitalize()} Analyst"
            current_tools = f"tools_{analyst_type}"
            current_clear = f"Msg Clear {analyst_type.capitalize()}"

            # Add conditional edges for current analyst
            workflow.add_conditional_edges(
                current_analyst,
                getattr(self.conditional_logic, f"should_continue_{analyst_type}"),
                [current_tools, current_clear],
            )
            workflow.add_edge(current_tools, current_analyst)

            # Connect to next analyst or to Bull Researcher if this is the last analyst
            if i < len(selected_analysts) - 1:
                next_analyst = f"{selected_analysts[i+1].capitalize()} Analyst"
                workflow.add_edge(current_clear, next_analyst)
            else:
                workflow.add_edge(current_clear, "Bull Researcher")

        # Add remaining edges
        workflow.add_conditional_edges(
            "Bull Researcher",
            self.conditional_logic.should_continue_debate,
            {
                "Bear Researcher": "Bear Researcher",
                "Research Manager": "Research Manager",
            },
        )
        workflow.add_conditional_edges(
            "Bear Researcher",
            self.conditional_logic.should_continue_debate,
            {
                "Bull Researcher": "Bull Researcher",
                "Research Manager": "Research Manager",
            },
        )
        workflow.add_edge("Research Manager", "Trader")
        workflow.add_edge("Trader", "Risky Analyst")
        workflow.add_conditional_edges(
            "Risky Analyst",
            self.conditional_logic.should_continue_risk_analysis,
            {
                "Safe Analyst": "Safe Analyst",
                "Risk Judge": "Risk Judge",
            },
        )
        workflow.add_conditional_edges(
            "Safe Analyst",
            self.conditional_logic.should_continue_risk_analysis,
            {
                "Neutral Analyst": "Neutral Analyst",
                "Risk Judge": "Risk Judge",
            },
        )
        workflow.add_conditional_edges(
            "Neutral Analyst",
            self.conditional_logic.should_continue_risk_analysis,
            {
                "Risky Analyst": "Risky Analyst",
                "Risk Judge": "Risk Judge",
            },
        )

        workflow.add_edge("Risk Judge", END)

        # Compile and return
        return workflow.compile()
