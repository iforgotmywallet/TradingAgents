// TradingAgents Web App JavaScript

class TradingAgentsApp {
    constructor() {
        this.websocket = null;
        this.analysisInProgress = false;
        this.agentStatuses = {};
        this.messages = [];
        
        this.init();
    }

    async init() {
        this.setupEventListeners();
        this.setupWebSocket();
        await this.loadInitialData();
        this.setDefaultDate();
    }

    setupEventListeners() {
        document.getElementById('analysisForm').addEventListener('submit', (e) => {
            e.preventDefault();
            this.startAnalysis();
        });

        document.getElementById('llmProvider').addEventListener('change', (e) => {
            this.updateModelOptions(e.target.value);
        });
    }

    setupWebSocket() {
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const wsUrl = `${protocol}//${window.location.host}/ws`;
        
        console.log('Connecting to WebSocket:', wsUrl);
        this.websocket = new WebSocket(wsUrl);
        
        this.websocket.onopen = () => {
            console.log('WebSocket connected successfully');
        };
        
        this.websocket.onmessage = (event) => {
            try {
                const data = JSON.parse(event.data);
                this.handleWebSocketMessage(data);
            } catch (error) {
                console.error('Error parsing WebSocket message:', error);
            }
        };
        
        this.websocket.onclose = (event) => {
            console.log('WebSocket disconnected:', event.code, event.reason);
            // Attempt to reconnect after 3 seconds
            setTimeout(() => this.setupWebSocket(), 3000);
        };
        
        this.websocket.onerror = (error) => {
            console.error('WebSocket error:', error);
        };
    }

    handleWebSocketMessage(data) {
        switch (data.type) {
            case 'status':
                this.addMessage('System', data.message);
                break;
            case 'agent_status':
                this.updateAgentStatus(data.agent, data.status);
                break;
            case 'analysis_complete':
                this.handleAnalysisComplete(data);
                break;
            case 'error':
                this.handleError(data.message);
                break;
            case 'ping':
                // Keep-alive message, no action needed
                break;
        }
    }

    async loadInitialData() {
        try {
            // Load analyst options
            const analystsResponse = await fetch('/api/analyst-options');
            if (!analystsResponse.ok) {
                throw new Error(`HTTP ${analystsResponse.status}: ${analystsResponse.statusText}`);
            }
            const analystsData = await analystsResponse.json();
            this.populateAnalysts(analystsData.analysts);

            // Load LLM providers
            const providersResponse = await fetch('/api/llm-providers');
            if (!providersResponse.ok) {
                throw new Error(`HTTP ${providersResponse.status}: ${providersResponse.statusText}`);
            }
            const providersData = await providersResponse.json();
            this.populateLLMProviders(providersData.providers);

            // Load research depth options
            const depthResponse = await fetch('/api/research-depth-options');
            if (!depthResponse.ok) {
                throw new Error(`HTTP ${depthResponse.status}: ${depthResponse.statusText}`);
            }
            const depthData = await depthResponse.json();
            this.populateResearchDepth(depthData.options);

        } catch (error) {
            console.error('Error loading initial data:', error);
            this.showError(`Failed to load configuration options: ${error.message}`);
        }
    }

    setDefaultDate() {
        const today = new Date();
        const yesterday = new Date(today);
        yesterday.setDate(yesterday.getDate() - 1);
        
        const dateString = yesterday.toISOString().split('T')[0];
        document.getElementById('analysisDate').value = dateString;
    }

    populateAnalysts(analysts) {
        const container = document.getElementById('analystsCheckboxes');
        container.innerHTML = '';

        analysts.forEach(analyst => {
            const div = document.createElement('div');
            div.className = 'form-check';
            div.innerHTML = `
                <input class="form-check-input" type="checkbox" value="${analyst.value}" 
                       id="analyst_${analyst.value}" checked>
                <label class="form-check-label" for="analyst_${analyst.value}">
                    ${analyst.label}
                </label>
            `;
            container.appendChild(div);
        });
    }

    populateLLMProviders(providers) {
        const select = document.getElementById('llmProvider');
        select.innerHTML = '';

        Object.keys(providers).forEach(key => {
            const option = document.createElement('option');
            option.value = key;
            option.textContent = key.charAt(0).toUpperCase() + key.slice(1);
            select.appendChild(option);
        });

        // Set default to OpenAI and update models
        select.value = 'openai';
        this.updateModelOptions('openai');
    }

    populateResearchDepth(options) {
        const select = document.getElementById('researchDepth');
        select.innerHTML = '';

        options.forEach(option => {
            const optionElement = document.createElement('option');
            optionElement.value = option.value;
            optionElement.textContent = option.label;
            select.appendChild(optionElement);
        });

        // Set default to medium
        select.value = '3';
    }

    async updateModelOptions(provider) {
        try {
            const response = await fetch('/api/llm-providers');
            const data = await response.json();
            const providerData = data.providers[provider];

            if (!providerData) return;

            // Update shallow thinker options
            const shallowSelect = document.getElementById('shallowThinker');
            shallowSelect.innerHTML = '';
            providerData.shallow_models.forEach(model => {
                const option = document.createElement('option');
                option.value = model.value;
                option.textContent = model.label;
                shallowSelect.appendChild(option);
            });

            // Update deep thinker options
            const deepSelect = document.getElementById('deepThinker');
            deepSelect.innerHTML = '';
            providerData.deep_models.forEach(model => {
                const option = document.createElement('option');
                option.value = model.value;
                option.textContent = model.label;
                deepSelect.appendChild(option);
            });

            // Set defaults
            if (providerData.shallow_models.length > 0) {
                shallowSelect.value = providerData.shallow_models[0].value;
            }
            if (providerData.deep_models.length > 0) {
                deepSelect.value = providerData.deep_models[0].value;
            }

        } catch (error) {
            console.error('Error updating model options:', error);
        }
    }

    async startAnalysis() {
        if (this.analysisInProgress) {
            this.showError('Analysis is already in progress');
            return;
        }

        try {
            // Collect form data
            const formData = this.collectFormData();
            
            // Validate form data
            if (!this.validateFormData(formData)) {
                return;
            }

            this.analysisInProgress = true;
            this.updateUI(true);

            // Send analysis request
            const response = await fetch('/api/analyze', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(formData)
            });

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            const result = await response.json();
            this.addMessage('System', result.message);

        } catch (error) {
            console.error('Error starting analysis:', error);
            this.handleError(`Failed to start analysis: ${error.message}`);
            this.analysisInProgress = false;
            this.updateUI(false);
        }
    }

    collectFormData() {
        // Get selected analysts
        const selectedAnalysts = [];
        document.querySelectorAll('#analystsCheckboxes input[type="checkbox"]:checked').forEach(checkbox => {
            selectedAnalysts.push(checkbox.value);
        });

        // Get LLM provider data
        const provider = document.getElementById('llmProvider').value;
        
        // Get backend URL
        const providerUrls = {
            'openai': 'https://api.openai.com/v1',
            'anthropic': 'https://api.anthropic.com/',
            'google': 'https://generativelanguage.googleapis.com/v1'
        };

        return {
            ticker: document.getElementById('ticker').value.toUpperCase(),
            analysis_date: document.getElementById('analysisDate').value,
            analysts: selectedAnalysts,
            research_depth: parseInt(document.getElementById('researchDepth').value),
            llm_provider: provider,
            backend_url: providerUrls[provider] || providerUrls['openai'],
            shallow_thinker: document.getElementById('shallowThinker').value,
            deep_thinker: document.getElementById('deepThinker').value
        };
    }

    validateFormData(data) {
        if (!data.ticker) {
            this.showError('Please enter a ticker symbol');
            return false;
        }

        if (!data.analysis_date) {
            this.showError('Please select an analysis date');
            return false;
        }

        if (data.analysts.length === 0) {
            this.showError('Please select at least one analyst');
            return false;
        }

        if (!data.shallow_thinker || !data.deep_thinker) {
            this.showError('Please select both thinking agents');
            return false;
        }

        return true;
    }

    updateUI(analysisStarted) {
        const button = document.getElementById('startAnalysis');
        const form = document.getElementById('analysisForm');
        const recommendationCard = document.getElementById('recommendationCard');
        const resultsContainer = document.getElementById('resultsContainer');

        if (analysisStarted) {
            button.innerHTML = '<i class="fas fa-spinner fa-spin me-2"></i>Analysis Running...';
            button.disabled = true;
            form.style.opacity = '0.7';
            recommendationCard.style.display = 'none'; // Hide previous recommendation
            
            // Clear previous analysis results
            resultsContainer.innerHTML = `
                <div class="text-center text-muted">
                    <i class="fas fa-spinner fa-spin fa-2x mb-2"></i>
                    <p>Analysis in progress...</p>
                </div>
            `;
            
            this.initializeProgress();
        } else {
            button.innerHTML = '<i class="fas fa-play me-2"></i>Start Analysis';
            button.disabled = false;
            form.style.opacity = '1';
        }
    }

    initializeProgress() {
        const agents = [
            { team: 'Analyst Team', agents: ['Market Analyst', 'Social Analyst', 'News Analyst', 'Fundamentals Analyst'] },
            { team: 'Research Team', agents: ['Bull Researcher', 'Bear Researcher', 'Research Manager'] },
            { team: 'Trading Team', agents: ['Trader'] },
            { team: 'Risk Management', agents: ['Risky Analyst', 'Neutral Analyst', 'Safe Analyst'] },
            { team: 'Portfolio Management', agents: ['Portfolio Manager'] }
        ];

        const container = document.getElementById('progressContainer');
        container.innerHTML = '';

        agents.forEach(teamData => {
            const teamDiv = document.createElement('div');
            teamDiv.className = 'team-section';
            
            const teamTitle = document.createElement('div');
            teamTitle.className = 'team-title';
            teamTitle.textContent = teamData.team;
            teamDiv.appendChild(teamTitle);

            teamData.agents.forEach(agent => {
                const agentDiv = document.createElement('div');
                agentDiv.className = 'progress-item pending';
                agentDiv.id = `agent-${agent.replace(/\s+/g, '-').toLowerCase()}`;
                agentDiv.innerHTML = `
                    <span>${agent}</span>
                    <span class="status-badge status-pending">Pending</span>
                `;
                teamDiv.appendChild(agentDiv);
                this.agentStatuses[agent] = 'pending';
            });

            container.appendChild(teamDiv);
        });
    }

    updateAgentStatus(agent, status) {
        this.agentStatuses[agent] = status;
        const agentId = `agent-${agent.replace(/\s+/g, '-').toLowerCase()}`;
        const agentElement = document.getElementById(agentId);
        
        if (agentElement) {
            // Update classes
            agentElement.className = `progress-item ${status}`;
            
            // Update status badge
            const badge = agentElement.querySelector('.status-badge');
            if (badge) {
                badge.className = `status-badge status-${status}`;
                let statusText = '';
                switch (status) {
                    case 'pending':
                        statusText = 'PENDING';
                        break;
                    case 'in_progress':
                        statusText = 'IN PROGRESS';
                        break;
                    case 'completed':
                        statusText = 'DONE';
                        break;
                    case 'error':
                        statusText = 'ERROR';
                        break;
                    default:
                        statusText = status.toUpperCase();
                }
                badge.textContent = statusText;
            }
        }

        this.addMessage('Status', `${agent}: ${status}`);
    }

    addMessage(type, content) {
        const timestamp = new Date().toLocaleTimeString();
        this.messages.push({ timestamp, type, content });
        
        // Keep only last 50 messages
        if (this.messages.length > 50) {
            this.messages = this.messages.slice(-50);
        }
        
        this.updateMessagesDisplay();
    }

    updateMessagesDisplay() {
        const container = document.getElementById('messagesContainer');
        container.innerHTML = '';

        this.messages.slice(-20).forEach(message => {
            const messageDiv = document.createElement('div');
            messageDiv.className = 'message-item';
            messageDiv.innerHTML = `
                <div class="d-flex justify-content-between">
                    <span class="message-timestamp">${message.timestamp}</span>
                    <span class="message-type">${message.type}</span>
                </div>
                <div class="message-content">${message.content}</div>
            `;
            container.appendChild(messageDiv);
        });

        // Scroll to bottom
        container.scrollTop = container.scrollHeight;
    }

    handleAnalysisComplete(data) {
        this.analysisInProgress = false;
        this.updateUI(false);
        
        this.addMessage('System', 'Analysis completed successfully!');
        this.displayResults(data.final_state, data.decision);
        
        // Display final recommendation
        if (data.recommendation) {
            this.displayRecommendation(data.recommendation);
        }
    }

    displayResults(finalState, decision) {
        const container = document.getElementById('resultsContainer');
        container.innerHTML = '';

        // Create results sections
        const sections = [
            { title: 'I. Analyst Team Reports', key: 'analyst_reports' },
            { title: 'II. Research Team Decision', key: 'investment_plan' },
            { title: 'III. Trading Team Plan', key: 'trader_investment_plan' },
            { title: 'IV. Risk Management Decision', key: 'risk_decision' },
            { title: 'V. Portfolio Management Decision', key: 'final_trade_decision' }
        ];

        sections.forEach(section => {
            if (finalState[section.key]) {
                const sectionDiv = document.createElement('div');
                sectionDiv.className = 'analysis-section';
                sectionDiv.innerHTML = `
                    <div class="analysis-title">${section.title}</div>
                    <div class="analysis-content">${this.formatContent(finalState[section.key])}</div>
                `;
                container.appendChild(sectionDiv);
            }
        });

        // Add final decision
        if (decision) {
            const decisionDiv = document.createElement('div');
            decisionDiv.className = 'analysis-section';
            decisionDiv.style.borderLeftColor = '#28a745';
            decisionDiv.innerHTML = `
                <div class="analysis-title">Final Trading Decision</div>
                <div class="analysis-content">${this.formatContent(decision)}</div>
            `;
            container.appendChild(decisionDiv);
        }
    }

    formatContent(content) {
        if (typeof content === 'string') {
            // Convert markdown-like formatting to HTML
            return content
                .replace(/### (.*)/g, '<h3>$1</h3>')
                .replace(/## (.*)/g, '<h2>$1</h2>')
                .replace(/# (.*)/g, '<h1>$1</h1>')
                .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
                .replace(/\*(.*?)\*/g, '<em>$1</em>')
                .replace(/\n/g, '<br>');
        }
        return JSON.stringify(content, null, 2);
    }

    handleError(message) {
        this.analysisInProgress = false;
        this.updateUI(false);
        this.showError(message);
        this.addMessage('Error', message);
    }

    displayRecommendation(recommendation) {
        const recommendationCard = document.getElementById('recommendationCard');
        const recommendationHeader = document.getElementById('recommendationHeader');
        const recommendationContent = document.getElementById('recommendationContent');
        
        // Show the recommendation card
        recommendationCard.style.display = 'block';
        
        // Set colors and content based on recommendation
        let cardClass = '';
        let description = '';
        
        switch (recommendation.toUpperCase()) {
            case 'BUY':
                cardClass = 'recommendation-buy';
                description = 'Analysis suggests a positive outlook for this investment.';
                break;
            case 'SELL':
                cardClass = 'recommendation-sell';
                description = 'Analysis suggests it may be time to exit this position.';
                break;
            case 'HOLD':
                cardClass = 'recommendation-hold';
                description = 'Analysis suggests maintaining current position.';
                break;
            default:
                cardClass = 'recommendation-hold';
                description = 'Analysis complete. Review detailed results below.';
        }
        
        // Apply colored background to entire card
        recommendationCard.className = `card mb-3 ${cardClass}`;
        recommendationHeader.className = `card-header text-white`;
        
        // Get the card body and apply the colored background
        const cardBody = recommendationContent.parentElement;
        cardBody.className = `card-body text-center recommendation-card-body`;
        
        // Update content without icon - just centered text
        recommendationContent.innerHTML = `
            <div class="recommendation-display">
                ${recommendation.toUpperCase()}
            </div>
            <div class="recommendation-description">
                ${description}
            </div>
        `;
        
        // Scroll to recommendation
        recommendationCard.scrollIntoView({ behavior: 'smooth', block: 'center' });
    }

    showError(message) {
        // Create a toast-like error message
        const errorDiv = document.createElement('div');
        errorDiv.className = 'alert alert-danger alert-dismissible fade show position-fixed';
        errorDiv.style.cssText = 'top: 20px; right: 20px; z-index: 9999; max-width: 400px;';
        errorDiv.innerHTML = `
            <strong>Error:</strong> ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        `;
        document.body.appendChild(errorDiv);

        // Auto-remove after 5 seconds
        setTimeout(() => {
            if (errorDiv.parentNode) {
                errorDiv.parentNode.removeChild(errorDiv);
            }
        }, 5000);
    }
}

// Initialize the app when the DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    new TradingAgentsApp();
});