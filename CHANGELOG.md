# Changelog

All notable changes to TradingAgents will be documented in this file.

## [Unreleased]

### Added
- **Web Interface**: Complete web application with real-time progress tracking
  - Modern FastAPI backend with WebSocket support
  - Interactive HTML/CSS/JavaScript frontend
  - Real-time agent status updates (PENDING → IN PROGRESS → DONE)
  - Dynamic BUY/SELL/HOLD recommendation display with color coding
  - Responsive design for desktop and mobile
  - WebSocket-based live communication
  - Comprehensive error handling and recovery

### Enhanced
- **Multi-Interface Support**: Both CLI and Web interfaces now available
- **Real-Time Feedback**: Live progress tracking across all 12 agents and 5 teams
- **User Experience**: Intuitive configuration forms and visual progress indicators
- **Documentation**: Updated README with web interface instructions
- **Setup Scripts**: Automated setup and launch scripts for easy deployment

### Technical Improvements
- FastAPI backend with CORS support
- WebSocket connection management
- JSON serialization for complex analysis results
- Virtual environment management scripts
- Comprehensive .gitignore for clean repository
- Environment configuration templates

### Files Added
- `webapp/app.py` - FastAPI backend application
- `webapp/static/index.html` - Web interface frontend
- `webapp/static/style.css` - Custom styling and responsive design
- `webapp/static/app.js` - Frontend JavaScript logic
- `webapp/requirements.txt` - Web app specific dependencies
- `webapp/run.py` - Web app launcher
- `launch_webapp.py` - Simple web app launcher
- `test_webapp.py` - Web app testing utilities
- `.env.example` - Environment configuration template

## [1.0.0] - 2024-12-XX

### Added
- Initial release of TradingAgents framework
- Multi-agent architecture with 5 specialized teams
- CLI interface for interactive trading analysis
- Support for multiple LLM providers (OpenAI, Anthropic, Google)
- Comprehensive market analysis pipeline
- Real-time data integration with Finnhub API
- Configurable research depth and debate rounds