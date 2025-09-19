# TradingAgents Web App

A web-based interface for the TradingAgents multi-agent LLM financial trading framework. This web app provides the same functionality as the CLI (`python -m cli.main`) but with an intuitive web interface.

## Features

- **Interactive Configuration**: Easy-to-use web forms for all analysis parameters
- **Real-time Progress Tracking**: Live updates on agent status and progress
- **WebSocket Communication**: Real-time messaging and status updates
- **Responsive Design**: Works on desktop and mobile devices
- **Complete Analysis Pipeline**: Full workflow from analyst team to portfolio management

## Workflow

The web app follows the same 5-step workflow as the CLI:

1. **Analyst Team** → Market, Social, News, and Fundamentals analysis
2. **Research Team** → Bull/Bear research and management decisions
3. **Trading Team** → Trading strategy and execution plans
4. **Risk Management** → Risk assessment and mitigation strategies
5. **Portfolio Management** → Final trading decisions and portfolio allocation

## Installation

1. **Install Dependencies**:
   ```bash
   pip install -r webapp/requirements.txt
   ```

2. **Ensure Main Project Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Set up Environment Variables**:
   Copy `.env.example` to `.env` and configure your API keys:
   ```bash
   cp .env.example .env
   ```

## Usage

### Starting the Web App

```bash
# Option 1: Using the run script
python webapp/run.py

# Option 2: Using uvicorn directly
cd webapp
uvicorn app:app --host 0.0.0.0 --port 8000 --reload
```

### Accessing the App

Open your browser and navigate to: `http://localhost:8000`

### Configuration Steps

1. **Ticker Symbol**: Enter the stock ticker to analyze (e.g., SPY, AAPL, NVDA)
2. **Analysis Date**: Select the date for analysis (cannot be future date)
3. **Analyst Team**: Choose which analysts to include in the analysis
4. **Research Depth**: Select the depth of research and debate rounds
5. **LLM Provider**: Choose your preferred LLM service (OpenAI, Anthropic, Google)
6. **Thinking Agents**: Select models for quick and deep thinking tasks

### Running Analysis

1. Fill out all configuration options
2. Click "Start Analysis"
3. Monitor real-time progress in the Progress panel
4. View messages and tool calls in the Messages panel
5. See analysis results as they're generated in the Results panel

## API Endpoints

### REST Endpoints

- `GET /` - Main web interface
- `POST /api/analyze` - Start analysis with configuration
- `GET /api/analyst-options` - Get available analyst types
- `GET /api/llm-providers` - Get LLM providers and models
- `GET /api/research-depth-options` - Get research depth options

### WebSocket Endpoint

- `WS /ws` - Real-time communication for status updates and results

## Architecture

### Backend (FastAPI)

- **app.py**: Main FastAPI application with REST and WebSocket endpoints
- **Background Tasks**: Analysis runs asynchronously with real-time updates
- **Integration**: Direct integration with the existing TradingAgents framework

### Frontend (HTML/CSS/JavaScript)

- **index.html**: Main web interface with Bootstrap styling
- **style.css**: Custom styles and responsive design
- **app.js**: JavaScript application logic and WebSocket handling

### Key Components

1. **Configuration Manager**: Handles form data and validation
2. **WebSocket Manager**: Real-time communication with backend
3. **Progress Tracker**: Visual progress indicators for all agents
4. **Results Display**: Formatted display of analysis results
5. **Error Handling**: User-friendly error messages and recovery

## Supported LLM Providers

- **OpenAI**: GPT-4o, GPT-4o-mini, o1, o3, o4 series
- **Anthropic**: Claude 3.5 Haiku, Sonnet, Claude 4 series
- **Google**: Gemini 2.0 Flash, Gemini 2.5 Pro series

## File Structure

```
webapp/
├── app.py              # FastAPI backend application
├── run.py              # Application runner script
├── requirements.txt    # Web app dependencies
├── README.md          # This file
└── static/
    ├── index.html     # Main web interface
    ├── style.css      # Custom styles
    └── app.js         # Frontend JavaScript logic
```

## Development

### Running in Development Mode

```bash
python webapp/run.py
```

This starts the server with auto-reload enabled for development.

### Adding New Features

1. **Backend**: Add new endpoints in `app.py`
2. **Frontend**: Update `index.html`, `style.css`, and `app.js`
3. **Integration**: Modify the TradingAgents integration as needed

## Troubleshooting

### Common Issues

1. **Import Errors**: Ensure the parent directory is in Python path
2. **WebSocket Connection**: Check firewall settings and port availability
3. **API Key Issues**: Verify environment variables are set correctly
4. **Model Availability**: Ensure selected models are available for your API keys

### Logs and Debugging

- Check console output for backend logs
- Use browser developer tools for frontend debugging
- WebSocket messages are logged in the browser console

## Comparison with CLI

| Feature | CLI | Web App |
|---------|-----|---------|
| Configuration | Interactive prompts | Web forms |
| Progress Tracking | Rich terminal UI | Real-time web interface |
| Results Display | Terminal panels | Formatted web display |
| Multi-session | Single session | Multiple browser sessions |
| Accessibility | Terminal required | Any web browser |
| Real-time Updates | Terminal refresh | WebSocket updates |

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## License

Same license as the main TradingAgents project.