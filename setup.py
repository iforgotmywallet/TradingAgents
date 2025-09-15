"""
Setup script for the TradingAgents package.
"""

from setuptools import setup, find_packages

setup(
    name="tradingagents",
    version="0.1.0",
    description="Multi-Agents LLM Financial Trading Framework",
    author="TradingAgents Team",
    author_email="yijia.xiao@cs.ucla.edu",
    url="https://github.com/TauricResearch",
    packages=find_packages(),
    install_requires=[
        "beautifulsoup4>=4.12.0",
        "finnhub-python>=2.4.23",
        "langchain-anthropic>=0.3.15",
        "langchain-core>=0.3.0",
        "langchain-experimental>=0.3.4",
        "langchain-google-genai>=2.1.5",
        "langchain-openai>=0.3.23",
        "langgraph>=0.4.8",
        "openai>=1.0.0",
        "pandas>=2.3.0",
        "python-dateutil>=2.8.0",
        "python-dotenv>=1.0.0",
        "pytz>=2025.2",
        "questionary>=2.1.0",
        "requests>=2.32.4",
        "rich>=14.0.0",
        "stockstats>=0.6.5",
        "tenacity>=8.0.0",
        "tqdm>=4.67.1",
        "typing-extensions>=4.14.0",
        "typer>=0.9.0",
        "yfinance>=0.2.63",
    ],
    python_requires=">=3.10",
    entry_points={
        "console_scripts": [
            "tradingagents=cli.main:app",
        ],
    },
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Financial and Trading Industry",
        "License :: OSI Approved :: Apache Software License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.10",
        "Topic :: Office/Business :: Financial :: Investment",
    ],
)
