#!/usr/bin/env python3
"""
TradingAgents Main Entry Point

This is the main entry point for running TradingAgents analysis.
For interactive CLI, use: python -m cli.main
For web interface, use: python webapp/run.py
"""

from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

from tradingagents.graph.trading_graph import TradingAgentsGraph
from tradingagents.default_config import DEFAULT_CONFIG


def main():
    """Main function to run a sample analysis"""
    # Create a custom config
    config = DEFAULT_CONFIG.copy()
    config["llm_provider"] = "openai"
    config["backend_url"] = "https://api.openai.com/v1"
    config["deep_think_llm"] = "gpt-4o"
    config["quick_think_llm"] = "gpt-4o-mini"
    config["max_debate_rounds"] = 1
    config["online_tools"] = True

    # Initialize with custom config
    ta = TradingAgentsGraph(["market", "fundamentals"], config=config, debug=False)

    # Run analysis
    final_state, decision = ta.propagate("SPY", "2024-12-01")
    
    print("Analysis completed successfully!")
    print(f"Final recommendation: {decision}")
    
    return final_state, decision


if __name__ == "__main__":
    main()
