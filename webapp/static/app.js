
// Modal Manager class for handling modal functionality
class ModalManager {
    constructor() {
        this.modal = document.getElementById('reportModal');
        this.modalTitle = this.modal.querySelector('.modal-title');
        this.loadingState = this.modal.querySelector('.loading-state');
        this.errorState = this.modal.querySelector('.error-state');
        this.reportContent = this.modal.querySelector('.report-content');
        this.closeButton = this.modal.querySelector('.modal-close');
        this.retryButton = this.modal.querySelector('.retry-button');
        this.errorMessage = this.modal.querySelector('.error-message');

        this.currentRetryCallback = null;
        this.isModalOpen = false;

        this.setupEventListeners();
    }

    setupEventListeners() {
        // Close modal on background click
        this.modal.addEventListener('click', (e) => {
            if (e.target === this.modal) {
                this.close();
            }
        });

        // Close modal on close button click
        this.closeButton.addEventListener('click', () => {
            this.close();
        });

        // Close modal on ESC key
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape' && this.isOpen()) {
                this.close();
            }
        });

        // Retry button functionality
        this.retryButton.addEventListener('click', () => {
            if (this.currentRetryCallback) {
                this.currentRetryCallback();
            }
        });

        // Prevent modal content clicks from closing modal
        this.modal.querySelector('.modal-container').addEventListener('click', (e) => {
            e.stopPropagation();
        });
    }

    open(agentName) {
        this.modalTitle.textContent = `${agentName} Report`;
        this.modal.style.display = 'flex';
        this.isModalOpen = true;

        // Prevent background scrolling
        document.body.style.overflow = 'hidden';

        // Show loading state by default
        this.showLoading();

        // Add modal-open class to body for additional styling if needed
        document.body.classList.add('modal-open');

        // Focus management for accessibility
        this.closeButton.focus();
    }

    close() {
        this.modal.style.display = 'none';
        this.isModalOpen = false;

        // Restore background scrolling
        document.body.style.overflow = '';

        // Remove modal-open class
        document.body.classList.remove('modal-open');

        // Clear retry callback
        this.currentRetryCallback = null;

        // Clear content to prevent stale data
        this.clearContent();
    }

    isOpen() {
        return this.isModalOpen;
    }

    showLoading() {
        this.loadingState.style.display = 'flex';
        this.errorState.style.display = 'none';
        this.reportContent.style.display = 'none';
    }

    showError(message, retryCallback = null) {
        this.loadingState.style.display = 'none';
        this.errorState.style.display = 'flex';
        this.reportContent.style.display = 'none';

        this.errorMessage.textContent = message;
        this.currentRetryCallback = retryCallback;

        // Show/hide retry button based on whether callback is provided
        if (retryCallback) {
            this.retryButton.style.display = 'inline-block';
        } else {
            this.retryButton.style.display = 'none';
        }
    }

    showContent(content) {
        this.loadingState.style.display = 'none';
        this.errorState.style.display = 'none';
        this.reportContent.style.display = 'block';

        this.reportContent.innerHTML = content;

        // Scroll to top of content
        this.reportContent.scrollTop = 0;
    }

    clearContent() {
        this.reportContent.innerHTML = '';
        this.errorMessage.textContent = '';
        this.currentRetryCallback = null;
    }

    updateTitle(title) {
        this.modalTitle.textContent = title;
    }

    // Utility method to check if modal is currently loading
    isLoading() {
        return this.loadingState.style.display === 'flex';
    }

    // Utility method to check if modal is showing error
    isShowingError() {
        return this.errorState.style.display === 'flex';
    }

    // Utility method to check if modal is showing content
    isShowingContent() {
        return this.reportContent.style.display === 'block';
    }
}

// Report content formatter class
class ReportFormatter {
    static formatMarkdown(content) {
        if (!content || typeof content !== 'string') {
            return '<p class="text-muted">No content available</p>';
        }

        try {
            // Handle tables first (before other formatting)
            let formatted = this.formatTables(content);

            // Format headers
            formatted = formatted
                .replace(/### (.*?)$/gm, '<h5 class="report-heading text-primary mt-3 mb-2">$1</h5>')
                .replace(/## (.*?)$/gm, '<h4 class="report-heading text-primary mt-3 mb-2">$1</h4>')
                .replace(/# (.*?)$/gm, '<h3 class="report-heading text-primary mt-4 mb-3">$1</h3>');

            // Format text styling
            formatted = formatted
                .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
                .replace(/\*(.*?)\*/g, '<em>$1</em>')
                .replace(/`([^`]+)`/g, '<code class="bg-light px-1 rounded">$1</code>');

            // Format lists
            formatted = this.formatLists(formatted);

            // Format paragraphs (handle line breaks)
            formatted = this.formatParagraphs(formatted);

            return formatted;

        } catch (error) {
            console.error('Error formatting markdown content:', error);
            return this.createErrorContent('Content formatting error', content);
        }
    }

    static formatTables(content) {
        // Match markdown tables
        const tableRegex = /(\|.*\|[\r\n]+\|[-\s|:]+\|[\r\n]+((\|.*\|[\r\n]*)+))/gm;

        return content.replace(tableRegex, (match) => {
            try {
                const lines = match.trim().split(/[\r\n]+/);
                if (lines.length < 3) return match; // Not a valid table

                const headerLine = lines[0];
                const separatorLine = lines[1];
                const dataLines = lines.slice(2);

                // Parse header
                const headers = this.parseTableRow(headerLine);
                if (headers.length === 0) return match;

                // Parse data rows
                const rows = dataLines
                    .map(line => this.parseTableRow(line))
                    .filter(row => row.length > 0);

                // Build HTML table
                let tableHtml = '<div class="table-responsive mt-2 mb-3">';
                tableHtml += '<table class="table table-sm table-striped table-hover">';

                // Header
                tableHtml += '<thead class="table-dark"><tr>';
                headers.forEach(header => {
                    tableHtml += `<th scope="col">${this.escapeHtml(header.trim())}</th>`;
                });
                tableHtml += '</tr></thead>';

                // Body
                tableHtml += '<tbody>';
                rows.forEach(row => {
                    tableHtml += '<tr>';
                    row.forEach((cell, index) => {
                        const cellContent = this.escapeHtml(cell.trim());
                        tableHtml += `<td>${cellContent}</td>`;
                    });
                    tableHtml += '</tr>';
                });
                tableHtml += '</tbody></table></div>';

                return tableHtml;

            } catch (error) {
                console.error('Error formatting table:', error);
                return `<div class="alert alert-warning">Table formatting error</div>`;
            }
        });
    }

    static parseTableRow(line) {
        if (!line || !line.includes('|')) return [];

        // Split by | and clean up
        const cells = line.split('|')
            .slice(1, -1) // Remove first and last empty elements
            .map(cell => cell.trim());

        return cells;
    }

    static formatLists(content) {
        // Handle unordered lists
        content = content.replace(/^[\s]*[-*+]\s+(.+)$/gm, '<li>$1</li>');

        // Handle ordered lists  
        content = content.replace(/^[\s]*\d+\.\s+(.+)$/gm, '<li>$1</li>');

        // Wrap consecutive list items in ul/ol tags
        content = content.replace(/(<li>.*<\/li>[\s\n]*)+/gs, (match) => {
            return `<ul class="mb-2">${match}</ul>`;
        });

        return content;
    }

    static formatParagraphs(content) {
        // Split content into blocks
        const blocks = content.split(/\n\s*\n/);

        return blocks.map(block => {
            block = block.trim();
            if (!block) return '';

            // Skip if already formatted as HTML element
            if (block.match(/^<(h[1-6]|div|table|ul|ol|li|blockquote)/i)) {
                return block;
            }

            // Convert single line breaks to <br> within paragraphs
            block = block.replace(/\n/g, '<br>');

            // Wrap in paragraph tags
            return `<p class="mb-2">${block}</p>`;
        }).join('\n');
    }

    static escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    static createErrorContent(errorType, originalContent = '') {
        return `
            <div class="alert alert-warning mb-3">
                <i class="fas fa-exclamation-triangle me-2"></i>
                <strong>${errorType}:</strong> Unable to properly format the report content.
                ${originalContent ? '<div class="mt-2"><small>Raw content available below.</small></div>' : ''}
            </div>
            ${originalContent ? `<pre class="bg-light p-2 rounded small">${this.escapeHtml(originalContent.substring(0, 500))}${originalContent.length > 500 ? '...' : ''}</pre>` : ''}
        `;
    }

    static createLoadingContent(agentName, loadingMessage = 'Fetching analysis results...') {
        return `
            <div class="d-flex align-items-center justify-content-center p-4 loading-container">
                <div class="spinner-border spinner-border-sm text-primary me-3" role="status">
                    <span class="visually-hidden">Loading...</span>
                </div>
                <div>
                    <div class="fw-semibold">Loading ${agentName} Report</div>
                    <small class="text-muted loading-message">${loadingMessage}</small>
                    <div class="progress mt-2" style="height: 4px; width: 200px;">
                        <div class="progress-bar progress-bar-striped progress-bar-animated" 
                             role="progressbar" style="width: 100%"></div>
                    </div>
                </div>
            </div>
        `;
    }

    static createNotFoundContent(agentName, reportFile) {
        return `
            <div class="alert alert-info mb-0">
                <i class="fas fa-info-circle me-2"></i>
                <strong>${agentName} Report Not Available</strong>
                <p class="mb-2 mt-2">No detailed report found for the ${agentName}.</p>
                <small class="text-muted">Expected file: ${reportFile}</small>
                <div class="mt-3">
                    <div class="text-muted small">
                        <i class="fas fa-lightbulb me-1"></i>
                        <strong>Possible reasons:</strong>
                        <ul class="mt-2 mb-0 ps-3">
                            <li>${agentName} analysis is still in progress</li>
                            <li>${agentName} completed without generating a detailed report</li>
                            <li>${agentName} report file was not saved to the expected location</li>
                        </ul>
                    </div>
                    <button class="btn btn-sm btn-outline-info mt-2" onclick="location.reload()">
                        <i class="fas fa-search me-1"></i>Refresh Page
                    </button>
                </div>
            </div>
        `;
    }

    static createNetworkErrorContent(agentName, errorMessage, retryCount = 0) {
        const maxRetries = 3;
        const canRetry = retryCount < maxRetries;

        return `
            <div class="alert alert-warning mb-0">
                <i class="fas fa-exclamation-triangle me-2"></i>
                <strong>Unable to Load ${agentName} Report</strong>
                <p class="mb-2 mt-2">Failed to load the ${agentName} report.</p>
                <small class="text-muted">Error: ${errorMessage}</small>
                ${retryCount > 0 ? `<small class="d-block text-muted mt-1">Retry attempt ${retryCount} of ${maxRetries} for ${agentName}</small>` : ''}
                <div class="mt-3">
                    ${canRetry ? `
                        <div class="text-muted small">
                            <i class="fas fa-info-circle me-1"></i>
                            Click the ${agentName} card to retry loading in modal.
                        </div>
                    ` : `
                        <div class="text-muted small">
                            <i class="fas fa-times-circle me-1"></i>
                            Maximum retry attempts reached for ${agentName}. Please try again later.
                        </div>
                        <div class="text-muted small mt-2">
                            <i class="fas fa-info-circle me-1"></i>
                            Click the ${agentName} card to try loading in modal.
                        </div>
                    `}
                </div>
            </div>
        `;
    }

    static formatReportContent(content, agentName, reportFile) {
        if (!content) {
            return this.createNotFoundContent(agentName, reportFile);
        }

        // Add report header
        const formattedContent = this.formatMarkdown(content);

        return `
            <div class="report-header mb-3 pb-2 border-bottom">
                <h6 class="text-primary mb-1">${agentName} Analysis Report</h6>
                <small class="text-muted">Source: ${reportFile}</small>
            </div>
            <div class="report-body">
                ${formattedContent}
            </div>
        `;
    }
}

// AgentCardManager class for handling card interactions
class AgentCardManager {
    constructor(modalManager) {
        this.modalManager = modalManager;
        this.setupCardListeners();
    }

    setupCardListeners() {
        // Use event delegation to handle clicks on agent cards
        document.addEventListener('click', (e) => {
            const card = e.target.closest('.agent-card[data-status="completed"]');
            if (card) {
                this.handleCardClick(card);
            }
        });

        // Add keyboard support for accessibility
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' || e.key === ' ') {
                const card = e.target.closest('.agent-card[data-status="completed"]');
                if (card && (e.target.matches('.card-content') || e.target.closest('.card-content'))) {
                    e.preventDefault();
                    this.handleCardClick(card);
                }
            }
        });
    }

    async handleCardClick(card) {
        const agentNameElement = card.querySelector('.agent-name');
        if (!agentNameElement) {
            console.error('Agent name element not found in card');
            return;
        }

        const agentName = agentNameElement.textContent.trim();
        const agentKey = this.getAgentKey(agentName);

        // Open modal with loading state
        this.modalManager.open(agentName);

        try {
            // Load report from API directly (no caching)
            const content = await this.loadReport(agentKey, agentName);
            this.modalManager.showContent(content);
        } catch (error) {
            console.error(`Error loading report for ${agentName}:`, error);
            this.modalManager.showError(
                `Failed to load ${agentName} report. Please try again.`,
                () => this.handleCardClick(card)
            );
        }
    }

    async loadReport(agentKey, agentName) {
        const { ticker, date } = this.getCurrentContext();

        try {
            // Use agent key directly (already in lowercase underscore format)
            const response = await fetch(`/api/reports/${ticker}/${date}/${agentKey}`);

            if (!response.ok) {
                if (response.status === 404) {
                    return this.createNotFoundContent(agentName);
                }

                // Try to get detailed error message from response
                let errorDetail = `HTTP ${response.status}: ${response.statusText}`;
                try {
                    const errorData = await response.json();
                    if (errorData.detail) {
                        errorDetail = errorData.detail;
                    } else if (errorData.error && errorData.error.message) {
                        errorDetail = errorData.error.message;
                    }
                } catch (e) {
                    // Use default error if JSON parsing fails
                }

                throw new Error(errorDetail);
            }

            const data = await response.json();

            if (data.success && data.report_content) {
                return ReportFormatter.formatReportContent(data.report_content, agentName, data.report_file || 'Unknown');
            } else {
                // Handle unsuccessful response with agent-specific error message
                const errorMessage = data.message || data.error || `${agentName} report not available`;
                return ReportFormatter.createNetworkErrorContent(agentName, errorMessage);
            }
        } catch (error) {
            console.error(`API request failed for ${agentName}:`, error);
            // Enhance error with agent-specific context
            const enhancedError = new Error(`Failed to retrieve ${agentName} report: ${error.message}`);
            enhancedError.agentName = agentName;
            enhancedError.originalError = error;
            throw enhancedError;
        }
    }

    getCurrentContext() {
        const tickerElement = document.getElementById('ticker');
        const dateElement = document.getElementById('analysisDate');

        const ticker = tickerElement ? tickerElement.value.toUpperCase().trim() : 'UNKNOWN';
        const date = dateElement ? dateElement.value : new Date().toISOString().split('T')[0];

        return { ticker, date };
    }

    getAgentKey(agentName) {
        // Convert agent name to lowercase with underscores for URL-friendly format
        // This avoids URL encoding issues with spaces
        return agentName.toLowerCase().replace(/\s+/g, '_');
    }

    createNotFoundContent(agentName) {
        return `
            <div class="alert alert-info mb-0">
                <i class="fas fa-info-circle me-2"></i>
                <strong>${agentName} Report Not Available</strong>
                <p class="mb-2 mt-2">No detailed report found for the ${agentName}.</p>
                <div class="mt-3">
                    <div class="text-muted small">
                        <i class="fas fa-lightbulb me-1"></i>
                        <strong>Possible reasons:</strong>
                        <ul class="mt-2 mb-0 ps-3">
                            <li>${agentName} analysis is still in progress</li>
                            <li>${agentName} completed without generating a detailed report</li>
                            <li>${agentName} report file was not saved to the expected location</li>
                        </ul>
                    </div>
                </div>
            </div>
        `;
    }

    // Update context when ticker/date changes (cache removed)
    updateContext(ticker, date) {
        // No cache to update - reports are loaded fresh each time
    }
}

// Agent name to database column mapping - using consistent agent names as keys
// This mapping aligns with the direct agent name approach and database schema
const AGENT_REPORT_MAPPING = {
    'Market Analyst': 'market_analyst_report',
    'Social Analyst': 'social_analyst_report',
    'News Analyst': 'news_analyst_report',
    'Fundamentals Analyst': 'fundamentals_analyst_report',
    'Bull Researcher': 'bull_researcher_report',
    'Bear Researcher': 'bear_researcher_report',
    'Research Manager': 'research_manager_report',
    'Trader': 'trader_report',
    'Risky Analyst': 'risky_analyst_report',
    'Neutral Analyst': 'neutral_analyst_report',
    'Safe Analyst': 'safe_analyst_report',
    'Portfolio Manager': 'portfolio_manager_report'
};

// AgentCard class for state management
class AgentCard {
    constructor(agentName, teamName, element) {
        this.agentName = agentName;
        this.teamName = teamName;
        this.element = element;
        this.status = 'pending';

        this.initializeElement();
        this.setupEventListeners();
    }

    initializeElement() {
        if (this.element) {
            this.element.setAttribute('data-agent', this.agentName);
            this.element.setAttribute('data-status', this.status);
            this.element.className = `agent-card mb-2 agent-card-${this.status}`;
        }
    }

    setupEventListeners() {
        // Event listeners will be handled by AgentCardManager for modal functionality
        // No card-specific event listeners needed for the simplified card approach
    }

    updateStatus(newStatus) {
        if (this.status === newStatus) return;

        const previousStatus = this.status;
        this.status = newStatus;
        this.updateUI();

        // Handle status-specific logic
        this.handleStatusChange(previousStatus, newStatus);
    }

    handleStatusChange(previousStatus, newStatus) {
        // Status change handling is simplified - no expansion logic needed
        // Modal functionality will be handled by AgentCardManager
    }

    updateUI() {
        if (!this.element) return;

        // Update data-status attribute
        this.element.setAttribute('data-status', this.status);

        // Update card classes based on status
        this.element.className = `agent-card mb-2 agent-card-${this.status}`;

        // Update status badge
        const badge = this.element.querySelector('.status-badge');
        if (badge) {
            badge.className = `status-badge status-${this.status} ms-2`;
            badge.textContent = this.getStatusText();
        }

        // Add loading spinner for in-progress status
        this.updateLoadingIndicator();
    }

    updateLoadingIndicator() {
        const statusIndicator = this.element.querySelector('.status-indicator');
        const existingSpinner = statusIndicator ? statusIndicator.querySelector('.loading-spinner') : null;

        if (this.status === 'in_progress') {
            if (!existingSpinner && statusIndicator) {
                const spinner = document.createElement('div');
                spinner.className = 'loading-spinner';
                statusIndicator.appendChild(spinner);
            }
        } else {
            if (existingSpinner) {
                existingSpinner.remove();
            }
        }
    }

    getStatusText() {
        switch (this.status) {
            case 'pending':
                return 'PENDING';
            case 'in_progress':
                return 'IN PROGRESS';
            case 'completed':
                return 'COMPLETED';
            case 'error':
                return 'ERROR';
            default:
                return this.status.toUpperCase();
        }
    }

    // Static method to create AgentCard instances from existing DOM elements
    static fromElement(element) {
        const agentName = element.getAttribute('data-agent');
        const teamSection = element.closest('.team-section');
        const teamName = teamSection ? teamSection.querySelector('.team-header h5').textContent.replace(/.*\s/, '') : 'Unknown Team';

        const card = new AgentCard(agentName, teamName, element);

        // Store reference on the element for easy access
        element.agentCard = card;

        return card;
    }

    // Clear cache (removed - no caching functionality)
    static clearCache() {
        // Cache functionality has been removed
        // Reports are now loaded fresh each time
    }

    // Check if the user is online
    static isOnline() {
        return navigator.onLine;
    }

    // Add connection status monitoring
    static initializeConnectionMonitoring() {
        window.addEventListener('online', () => {
            console.log('Connection restored');
            // Show notification to user
            AgentCard.showGlobalMessage('Connection restored.', 'success');
        });

        window.addEventListener('offline', () => {
            console.log('Connection lost');
            // Show notification to user
            AgentCard.showGlobalMessage('Connection lost. Some features may not be available.', 'warning');
        });
    }

    // Show global message to user
    static showGlobalMessage(message, type = 'info') {
        // Create or update global message container
        let messageContainer = document.getElementById('global-message-container');
        if (!messageContainer) {
            messageContainer = document.createElement('div');
            messageContainer.id = 'global-message-container';
            messageContainer.style.cssText = `
                position: fixed;
                top: 20px;
                right: 20px;
                z-index: 9999;
                max-width: 400px;
            `;
            document.body.appendChild(messageContainer);
        }

        const alertClass = type === 'success' ? 'alert-success' :
            type === 'warning' ? 'alert-warning' :
                type === 'error' ? 'alert-danger' : 'alert-info';

        const messageElement = document.createElement('div');
        messageElement.className = `alert ${alertClass} alert-dismissible fade show`;
        messageElement.innerHTML = `
            <i class="fas fa-${type === 'success' ? 'check-circle' : type === 'warning' ? 'exclamation-triangle' : type === 'error' ? 'times-circle' : 'info-circle'} me-2"></i>
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        `;

        messageContainer.appendChild(messageElement);

        // Auto-remove after 5 seconds
        setTimeout(() => {
            if (messageElement.parentNode) {
                messageElement.remove();
            }
        }, 5000);
    }
}

class TradingAgentsApp {
    constructor() {
        this.websocket = null;
        this.analysisInProgress = false;
        this.agentStatuses = {};
        this.agentCards = new Map();
        this.messages = [];

        this.init();
    }

    async init() {
        this.setupEventListeners();
        this.setupWebSocket();
        await this.loadInitialData();
        this.setDefaultDate();

        // Initialize agent cards and check for completed analysis
        this.initializeProgress();

        // Initialize connection monitoring for better error handling
        AgentCard.initializeConnectionMonitoring();
    }

    setupEventListeners() {
        document.getElementById('analysisForm').addEventListener('submit', (e) => {
            e.preventDefault();
            this.startAnalysis();
        });

        document.getElementById('llmProvider').addEventListener('change', (e) => {
            this.updateModelOptions(e.target.value);
        });

        // Note: Removed automatic report checking listeners for ticker and date inputs
        // Reports are now only loaded on demand when users click agent cards or start analysis
    }



    setupWebSocket() {
        // Enhanced WebSocket setup with Railway proxy support
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const host = window.location.host;
        const wsUrl = `${protocol}//${host}/ws`;
      
        console.log('Connecting to WebSocket:', wsUrl);
        console.log('Connection details:', {
            protocol: window.location.protocol,
            host: window.location.host,
            pathname: window.location.pathname,
            origin: window.location.origin
        });
        
        // Close existing connection if any
        if (this.websocket && this.websocket.readyState !== WebSocket.CLOSED) {
            this.websocket.close();
        }
        
        this.websocket = new WebSocket(wsUrl);
        
        // Set connection timeout
        const connectionTimeout = setTimeout(() => {
            if (this.websocket.readyState === WebSocket.CONNECTING) {
                console.warn('WebSocket connection timeout, closing...');
                this.websocket.close();
            }
        }, 10000); // 10 second timeout
        

        this.websocket.onopen = () => {
            clearTimeout(connectionTimeout);
            console.log('WebSocket connected successfully');
            console.log('WebSocket ready state:', this.websocket.readyState);
            
            // Send initial ping to test connection
            this.sendWebSocketMessage({
                type: 'ping',
                message: 'connection_test',
                timestamp: new Date().toISOString()
            });
            
            // Ensure agent cards are properly initialized when WebSocket connects
            this.ensureAgentCardsInitialized();
        };

        this.websocket.onmessage = (event) => {
            try {
                const data = JSON.parse(event.data);
                console.log('WebSocket message received:', data.type, data);
                this.handleWebSocketMessage(data);
            } catch (error) {
                console.error('Error parsing WebSocket message:', error, event.data);
            }
        };

        this.websocket.onclose = (event) => {
            clearTimeout(connectionTimeout);
            console.log('WebSocket disconnected:', {
                code: event.code,
                reason: event.reason,
                wasClean: event.wasClean
            });
            
            // Don't reconnect if it was a clean close (server shutdown)
            if (event.code === 1001) {
                console.log('Server shutdown detected, not reconnecting');
                return;
            }
            
            // Attempt to reconnect after delay with exponential backoff
            const reconnectDelay = Math.min(3000 * Math.pow(1.5, this.reconnectAttempts || 0), 30000);
            console.log(`Attempting to reconnect in ${reconnectDelay}ms...`);
            
            setTimeout(() => {
                this.reconnectAttempts = (this.reconnectAttempts || 0) + 1;
                this.setupWebSocket();
            }, reconnectDelay);
        };

        this.websocket.onerror = (error) => {
            clearTimeout(connectionTimeout);
            console.error('WebSocket error:', error);
            console.error('WebSocket state:', this.websocket.readyState);
        };
    }
    
    sendWebSocketMessage(message) {
        /**
         * Send a message through WebSocket with connection state checking
         * @param {Object} message - The message object to send
         */
        if (this.websocket && this.websocket.readyState === WebSocket.OPEN) {
            try {
                this.websocket.send(JSON.stringify(message));
                console.log('WebSocket message sent:', message.type);
            } catch (error) {
                console.error('Error sending WebSocket message:', error);
            }
        } else {
            console.warn('WebSocket not connected, cannot send message:', message);
        }
    }

    ensureAgentCardsInitialized() {
        // Ensure agent cards are initialized when WebSocket connects
        // This handles cases where WebSocket reconnects during an active session
        const progressContainer = document.getElementById('progressContainer');
        if (progressContainer && progressContainer.children.length === 0) {
            // No progress display exists, initialize it
            this.initializeProgress();
        } else if (progressContainer && progressContainer.children.length > 0) {
            // Progress display exists, ensure AgentCard instances are properly connected
            this.reconnectExistingAgentCards();
        }
    }

    reconnectExistingAgentCards() {
        // Reconnect existing DOM elements to AgentCard instances
        // This is useful when WebSocket reconnects and we need to ensure proper integration
        const agentCardElements = document.querySelectorAll('.agent-card');

        if (!this.agentCards) {
            this.agentCards = new Map();
        }

        agentCardElements.forEach(element => {
            const agentName = element.getAttribute('data-agent');
            if (agentName && !this.agentCards.has(agentName)) {
                // Create AgentCard instance for existing DOM element
                const agentCard = AgentCard.fromElement(element);
                this.agentCards.set(agentName, agentCard);

                // Sync status from DOM
                const currentStatus = element.getAttribute('data-status') || 'pending';
                this.agentStatuses[agentName] = currentStatus;

                console.log(`Reconnected agent card: ${agentName} with status: ${currentStatus}`);
            }
        });

        console.log(`Reconnected ${this.agentCards.size} existing agent cards`);
    }

    // Debug method to check WebSocket integration status
    debugWebSocketIntegration() {
        console.log('=== WebSocket Integration Debug Info ===');
        console.log(`WebSocket connected: ${this.websocket && this.websocket.readyState === WebSocket.OPEN}`);
        console.log(`Analysis in progress: ${this.analysisInProgress}`);
        console.log(`Agent cards initialized: ${this.agentCards ? this.agentCards.size : 0}`);

        // Debug agent card clickability
        if (this.agentCards) {
            console.log('Agent card statuses:');
            this.agentCards.forEach((agentCard, agentName) => {
                const isClickable = agentCard.element && agentCard.element.style.cursor === 'pointer';
                console.log(`  ${agentName}: ${agentCard.status} (clickable: ${isClickable})`);
            });
        }

        if (this.agentCards) {
            console.log('Agent card statuses:');
            this.agentCards.forEach((agentCard, agentName) => {
                console.log(`  ${agentName}: ${agentCard.status}`);
            });
        }

        console.log('Agent status tracking:');
        Object.entries(this.agentStatuses).forEach(([agent, status]) => {
            console.log(`  ${agent}: ${status}`);
        });

        console.log('=== End Debug Info ===');
    }

    handleWebSocketMessage(data) {
        switch (data.type) {
            case 'connection_established':
                console.log('WebSocket connection confirmed:', data.message);
                if (data.railway_proxy) {
                    console.log('Railway proxy detected and handled');
                }
                // Reset reconnection attempts on successful connection
                this.reconnectAttempts = 0;
                this.showNotification('success', 'WebSocket connected successfully');
                break;
                
            case 'pong':
                console.log('WebSocket pong received:', data.message);
                break;
                
            case 'echo':
                console.log('WebSocket echo received:', data);
                break;
                
            case 'status':
                this.addMessage('System', data.message);
                break;
                
            case 'agent_status':
                // Validate agent status data before processing
                if (this.validateAgentStatusData(data)) {
                    this.updateAgentStatus(data.agent, data.status);
                } else {
                    console.warn('Invalid agent status data received:', data);
                }
                break;
                
            case 'analysis_start':
                this.handleAnalysisStart(data);
                break;
                
            case 'analysis_complete':
                this.handleAnalysisComplete(data);
                break;
                
            case 'context_change':
                // Handle ticker/date context changes
                this.handleContextChange(data);
                break;
                
            case 'error':
                // Check if error is agent-specific
                const agentName = data.agent || null;
                this.handleError(data.message, agentName);
                break;
                
            case 'server_shutdown':
                console.warn('Server shutdown notification:', data.message);
                this.showNotification('warning', data.message);
                break;
                
            case 'ping':
                // Respond to server ping
                this.sendWebSocketMessage({
                    type: 'pong', 
                    message: 'pong',
                    timestamp: new Date().toISOString()
                });
                break;
                
            default:
                console.warn('Unknown WebSocket message type:', data.type, data);
        }
    }

    validateAgentStatusData(data) {
        // Validate that we have the required fields
        if (!data.agent || !data.status) {
            return false;
        }

        // Validate that the agent exists in our system
        const validAgents = [
            'Market Analyst', 'Social Analyst', 'News Analyst', 'Fundamentals Analyst',
            'Bull Researcher', 'Bear Researcher', 'Research Manager',
            'Trader',
            'Risky Analyst', 'Neutral Analyst', 'Safe Analyst',
            'Portfolio Manager'
        ];

        if (!validAgents.includes(data.agent)) {
            console.warn(`Unknown agent received in status update: ${data.agent}`);
            return false;
        }

        // Validate status values
        const validStatuses = ['pending', 'in_progress', 'completed', 'error'];
        if (!validStatuses.includes(data.status)) {
            console.warn(`Invalid status received: ${data.status} for agent: ${data.agent}`);
            return false;
        }

        return true;
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

            // Cache functionality removed - no context to update

            this.analysisInProgress = true;
            this.clearAgentCards();
            this.resetAgentCardsForNewAnalysis();
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
            this.showError('Please select at least one analyst agent');
            return false;
        }

        if (!data.shallow_thinker || !data.deep_thinker) {
            this.showError('Please select both shallow and deep thinking agent models');
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

        // Clear existing content and state
        container.innerHTML = '';
        this.clearAgentCards();

        // Reset agent statuses
        this.agentStatuses = {};

        // Initialize agent cards map
        this.agentCards = new Map();

        agents.forEach(teamData => {
            // Create team section container
            const teamSection = document.createElement('div');
            teamSection.className = 'team-section mb-4';

            // Create team header
            const teamHeader = document.createElement('div');
            teamHeader.className = 'team-header mb-3';
            teamHeader.innerHTML = `<h5 class="text-primary mb-0"><i class="fas fa-users me-2"></i>${teamData.team}</h5>`;
            teamSection.appendChild(teamHeader);

            // Create team cards container
            const teamCards = document.createElement('div');
            teamCards.className = 'team-cards';

            teamData.agents.forEach(agent => {
                // Create agent card element with proper structure
                const agentCardElement = document.createElement('div');
                agentCardElement.className = 'agent-card mb-2 agent-card-pending';
                agentCardElement.id = `agent-${agent.replace(/\s+/g, '-').toLowerCase()}`;
                agentCardElement.setAttribute('data-agent', agent);
                agentCardElement.setAttribute('data-status', 'pending');

                agentCardElement.innerHTML = `
                    <div class="card-content">
                        <div class="agent-info">
                            <span class="agent-name">${agent}</span>
                            <div class="status-indicator">
                                <span class="status-badge status-pending">PENDING</span>
                            </div>
                        </div>
                    </div>
                `;

                teamCards.appendChild(agentCardElement);

                // Create AgentCard instance and store reference
                const agentCard = new AgentCard(agent, teamData.team, agentCardElement);
                this.agentCards.set(agent, agentCard);
                this.agentStatuses[agent] = 'pending';

                // Ensure proper initial state
                agentCard.updateStatus('pending');
            });

            teamSection.appendChild(teamCards);
            container.appendChild(teamSection);
        });

        // Log initialization for debugging
        console.log(`Initialized ${this.agentCards.size} agent cards for WebSocket status updates`);
    }

    async checkAndLoadCompletedAnalysisStatus() {
        // Get current ticker and date from form
        const tickerElement = document.getElementById('ticker');
        const dateElement = document.getElementById('analysisDate');

        if (!tickerElement || !dateElement) return;

        const ticker = tickerElement.value.toUpperCase().trim();
        const date = dateElement.value;

        if (!ticker || !date) return;

        console.log(`🔍 Checking for completed analysis: ${ticker} on ${date}`);

        // Check each agent to see if reports are available
        const agentNames = Array.from(this.agentCards.keys());
        console.log(`📋 Checking ${agentNames.length} agents:`, agentNames);

        for (const agentName of agentNames) {
            try {
                // Convert agent name to lowercase underscore format
                const agentKey = agentName.toLowerCase().replace(/\s+/g, '_');
                const apiUrl = `/api/reports/${ticker}/${date}/${agentKey}`;
                console.log(`🌐 Checking ${agentName}: ${apiUrl}`);

                const response = await fetch(apiUrl, {
                    method: 'GET',
                    headers: {
                        'Accept': 'application/json',
                        'Content-Type': 'application/json'
                    },
                    timeout: 15000
                });

                console.log(`📡 ${agentName} response: ${response.status} ${response.statusText}`);

                if (response.ok) {
                    const data = await response.json();
                    console.log(`📄 ${agentName} data:`, {
                        success: data.success,
                        hasContent: !!(data.report_content && data.report_content.trim().length > 0),
                        contentLength: data.report_content ? data.report_content.length : 0,
                        error: data.error,
                        message: data.message
                    });

                    if (data.success && data.report_content && data.report_content.trim().length > 0) {
                        // Report exists, set agent to completed status
                        console.log(`✅ Found completed report for ${agentName} (${data.report_content.length} chars)`);
                        this.updateAgentStatus(agentName, 'completed');
                    } else {
                        console.log(`❌ No valid report for ${agentName}: ${data.message || 'Unknown reason'}`);
                    }
                } else {
                    console.log(`❌ HTTP error for ${agentName}: ${response.status} ${response.statusText}`);
                }
            } catch (error) {
                // Log errors for debugging
                console.error(`❌ Error checking ${agentName}:`, error);
            }
        }

        // Also check if there's a final analysis available
        try {
            const response = await fetch(`/api/final-analysis/${ticker}/${date}`);
            if (response.ok) {
                const data = await response.json();
                if (data.success && data.final_analysis) {
                    console.log('Found completed final analysis');
                    // Update the results display if we have final results
                    this.displayFinalResults(data);
                }
            }
        } catch (error) {
            console.debug('Could not check final analysis:', error);
        }
    }



    displayFinalResults(data) {
        // Display final results in the results container
        const resultsContainer = document.getElementById('resultsContainer');
        if (!resultsContainer) return;

        // Clear loading message
        resultsContainer.innerHTML = '';

        // Create final results display
        const finalResultsDiv = document.createElement('div');
        finalResultsDiv.className = 'final-results mt-4';

        // Removed final_decision display - now using final_analysis only

        if (data.final_analysis) {
            const analysisDiv = document.createElement('div');
            analysisDiv.className = 'analysis-section mt-3';
            analysisDiv.innerHTML = `
                <div class="analysis-title">Final Analysis Summary</div>
                <div class="analysis-content">${this.formatContent(data.final_analysis)}</div>
            `;
            finalResultsDiv.appendChild(analysisDiv);
        }

        if (data.recommendation) {
            const recommendationDiv = document.createElement('div');
            recommendationDiv.className = 'analysis-section mt-3';
            recommendationDiv.style.borderLeftColor = data.recommendation === 'BUY' ? '#28a745' :
                data.recommendation === 'SELL' ? '#dc3545' : '#ffc107';
            recommendationDiv.innerHTML = `
                <div class="analysis-title">Recommendation</div>
                <div class="analysis-content">
                    <span class="badge bg-${data.recommendation === 'BUY' ? 'success' :
                    data.recommendation === 'SELL' ? 'danger' : 'warning'} fs-6">
                        ${data.recommendation}
                    </span>
                </div>
            `;
            finalResultsDiv.appendChild(recommendationDiv);
        }

        resultsContainer.appendChild(finalResultsDiv);
    }

    updateAgentStatus(agent, status) {
        this.agentStatuses[agent] = status;

        // Use AgentCard class if available
        if (this.agentCards && this.agentCards.has(agent)) {
            const agentCard = this.agentCards.get(agent);
            agentCard.updateStatus(status);

            // Handle status-specific WebSocket integration logic
            this.handleAgentStatusChange(agent, status, agentCard);
        } else {
            // Fallback to direct DOM manipulation for backward compatibility
            const agentId = `agent-${agent.replace(/\s+/g, '-').toLowerCase()}`;
            const agentElement = document.getElementById(agentId);

            if (agentElement) {
                // Create AgentCard instance if it doesn't exist
                const agentCard = AgentCard.fromElement(agentElement);
                if (!this.agentCards) {
                    this.agentCards = new Map();
                }
                this.agentCards.set(agent, agentCard);
                agentCard.updateStatus(status);

                // Handle status-specific WebSocket integration logic
                this.handleAgentStatusChange(agent, status, agentCard);
            }
        }

        // Cache functionality removed

        this.addMessage('Status', `${agent}: ${status}`);
    }

    handleAgentStatusChange(agent, status, agentCard) {
        // Handle status-specific logic for WebSocket integration with modal system
        try {
            switch (status) {
                case 'pending':
                    // Card is in pending state - ensure it's not clickable
                    this.updateCardClickability(agentCard, false);
                    console.log(`Agent ${agent} is pending - card not clickable`);
                    break;

                case 'in_progress':
                    // Card is processing - ensure it's not clickable
                    this.updateCardClickability(agentCard, false);
                    console.log(`Agent ${agent} is in progress - card not clickable`);
                    break;

                case 'completed':
                    // Card is completed - make it clickable for modal display
                    this.updateCardClickability(agentCard, true);
                    console.log(`Agent ${agent} completed - card ready for modal interaction`);
                    break;

                case 'error':
                    // Card has error - ensure it's not clickable
                    this.updateCardClickability(agentCard, false);
                    console.error(`${agent} encountered an error - card not clickable`);

                    // Show agent-specific error notification
                    this.showError(`${agent} analysis failed. Please check the logs for details.`, agent);
                    break;

                default:
                    console.warn(`Unknown status received for agent ${agent}: ${status}`);
                    this.updateCardClickability(agentCard, false);
            }

            // Update UI to reflect the new status
            agentCard.updateUI();

            // Log status change for debugging
            console.log(`Agent status updated: ${agent} -> ${status}`);

        } catch (error) {
            console.error(`Error handling status change for agent ${agent}:`, error);
            // Ensure UI is still updated even if there's an error
            agentCard.updateUI();
        }
    }

    handleAnalysisStart(data) {
        // Handle analysis start message from WebSocket
        console.log('Analysis started via WebSocket:', data);

        // Update analysis state
        this.analysisInProgress = true;
        this.updateUI(true);

        // Reset all agent statuses to pending
        if (this.agentCards) {
            this.agentCards.forEach((agentCard, agentName) => {
                this.updateAgentStatus(agentName, 'pending');
            });
        }

        this.addMessage('System', `Analysis started for ${data.ticker || 'unknown ticker'} on ${data.date || 'unknown date'}`);
    }

    handleContextChange(data) {
        // Handle ticker/date context changes from WebSocket
        console.log('Context change received via WebSocket:', data);

        if (data.ticker && data.date) {
            // Update form fields if they exist
            const tickerElement = document.getElementById('ticker');
            const dateElement = document.getElementById('analysisDate');

            if (tickerElement && tickerElement.value !== data.ticker) {
                tickerElement.value = data.ticker;
            }

            if (dateElement && dateElement.value !== data.date) {
                dateElement.value = data.date;
            }

            // Cache functionality removed

            this.addMessage('System', `Context updated to ${data.ticker} on ${data.date}`);
        }
    }

    updateCardClickability(agentCard, isClickable) {
        // Update card clickability based on status
        if (!agentCard || !agentCard.element) return;

        const cardElement = agentCard.element;

        if (isClickable) {
            // Make card clickable - add tabindex for keyboard accessibility
            cardElement.style.cursor = 'pointer';
            cardElement.setAttribute('tabindex', '0');
            cardElement.setAttribute('role', 'button');
            cardElement.setAttribute('aria-label', `View ${agentCard.agentName} report`);
        } else {
            // Make card not clickable
            cardElement.style.cursor = 'default';
            cardElement.removeAttribute('tabindex');
            cardElement.removeAttribute('role');
            cardElement.removeAttribute('aria-label');
        }
    }

    // Cache functionality removed - these methods are no longer needed

    // Cache functionality removed - these methods are no longer needed

    getCurrentContext() {
        // Get current ticker and date from form elements
        const tickerElement = document.getElementById('ticker');
        const dateElement = document.getElementById('analysisDate');

        const ticker = tickerElement ? tickerElement.value.toUpperCase().trim() : 'UNKNOWN';
        const date = dateElement ? dateElement.value : new Date().toISOString().split('T')[0];

        return { ticker, date };
    }

    clearAgentCards() {
        // Clear the agent cards map
        if (this.agentCards) {
            // Clean up each agent card instance
            this.agentCards.forEach((agentCard, agentName) => {
                if (agentCard && agentCard.element) {
                    // Remove event listeners and clean up references
                    agentCard.element.agentCard = null;
                }
            });
            this.agentCards.clear();
        }

        // Reset agent statuses
        this.agentStatuses = {};
    }

    resetAgentCardsForNewAnalysis() {
        // Reset all agent cards to pending state
        if (this.agentCards) {
            this.agentCards.forEach((agentCard, agentName) => {
                // Reset card state
                agentCard.updateStatus('pending');

                // Card state is now simplified - no report loading state to manage
                const reportContent = agentCard.element.querySelector('.report-content');
                if (reportContent) {
                    reportContent.innerHTML = '<!-- Report content will be loaded dynamically -->';
                    reportContent.dataset.loaded = 'false';
                }

                // Update agent status tracking
                this.agentStatuses[agentName] = 'pending';
            });
        }

        console.log('Reset all agent cards for new analysis');
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

    async handleAnalysisComplete(data) {
        this.analysisInProgress = false;
        this.updateUI(false);

        this.addMessage('System', 'Analysis completed successfully!');

        // Populate agent cards with final results - simplified for modal system
        await this.populateAgentCardsWithResults(data.final_state);

        // Display results in the traditional results container (complementary to cards)
        this.displayResults(data.final_state, data.decision);

        // Display final recommendation
        if (data.recommendation) {
            this.displayRecommendation(data.recommendation);
        }

        // Cache functionality removed

        // Ensure all completed agents are properly clickable for modal interaction
        this.updateAllCardClickability();
    }

    async populateAgentCardsWithResults(finalState) {
        // Handle missing final state gracefully
        if (!finalState) {
            console.warn('No final state data provided to populate agent cards');
            return;
        }

        console.log('🔄 Checking agent report availability via database...');

        // Get current ticker and date from the form
        const ticker = document.getElementById('ticker')?.value || 'AAPL';
        const date = document.getElementById('analysisDate')?.value || new Date().toISOString().split('T')[0];

        // All agents that should be checked
        const allAgents = [
            'Market Analyst', 'Social Analyst', 'News Analyst', 'Fundamentals Analyst',
            'Bull Researcher', 'Bear Researcher', 'Research Manager',
            'Trader',
            'Risky Analyst', 'Neutral Analyst', 'Safe Analyst',
            'Portfolio Manager'
        ];

        // Check each agent's report availability via API
        const checkPromises = allAgents.map(async (agentName) => {
            try {
                // Convert agent name to lowercase underscore format
                const agentKey = agentName.toLowerCase().replace(/\s+/g, '_');
                const response = await fetch(`/api/reports/${ticker}/${date}/${agentKey}`);

                if (response.ok) {
                    const data = await response.json();
                    if (data.success && data.report_content && data.report_content.trim().length > 0) {
                        // Report available - mark as completed
                        this.updateAgentStatus(agentName, 'completed');
                        console.log(`✅ ${agentName} marked as completed - report available via database`);
                        return { agent: agentName, available: true };
                    }
                }

                // Report not available or empty
                console.log(`⚠️ ${agentName} - no report data available in database`);
                return { agent: agentName, available: false };

            } catch (error) {
                console.error(`❌ Error checking ${agentName} report:`, error);
                return { agent: agentName, available: false, error: error.message };
            }
        });

        // Wait for all checks to complete
        try {
            const results = await Promise.all(checkPromises);

            // Log summary
            const availableCount = results.filter(r => r.available).length;
            const totalCount = results.length;
            console.log(`📊 Agent report availability: ${availableCount}/${totalCount} agents have reports`);

            // Log details for debugging
            results.forEach(result => {
                if (result.available) {
                    console.log(`  ✅ ${result.agent}: Available`);
                } else if (result.error) {
                    console.log(`  ❌ ${result.agent}: Error - ${result.error}`);
                } else {
                    console.log(`  ⚠️ ${result.agent}: Not available`);
                }
            });

        } catch (error) {
            console.error('❌ Error checking agent report availability:', error);
        }
    }

    updateAllCardClickability() {
        // Update clickability for all agent cards based on their current status
        if (this.agentCards) {
            this.agentCards.forEach((agentCard, agentName) => {
                const isClickable = agentCard.status === 'completed';
                this.updateCardClickability(agentCard, isClickable);
                console.log(`Card clickability updated: ${agentName} -> ${isClickable ? 'clickable' : 'not clickable'}`);
            });
        }
    }

    findAgentCard(agentName) {
        // Find the AgentCard instance by agent name from the stored Map
        return this.agentCards && this.agentCards.has(agentName) ? this.agentCards.get(agentName) : null;
    }



    displayResults(finalState, decision) {
        const container = document.getElementById('resultsContainer');

        // Update the results container to complement rather than replace card content
        container.innerHTML = `
            <div class="alert alert-info mb-3">
                <i class="fas fa-info-circle me-2"></i>
                <strong>Analysis Complete!</strong> 
                Detailed reports are now available by clicking on completed agent cards above. 
                This section provides a summary of the key findings.
            </div>
        `;

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
            // Use the ReportFormatter for consistent formatting
            return ReportFormatter.formatMarkdown(content);
        }
        return `<pre class="bg-light p-2 rounded small">${JSON.stringify(content, null, 2)}</pre>`;
    }

    handleError(message, agentName = null) {
        this.analysisInProgress = false;
        this.updateUI(false);
        this.showError(message, agentName);

        // Include agent name in the message log if provided
        const logMessage = agentName ? `${agentName}: ${message}` : message;
        this.addMessage('Error', logMessage);
    }

    showNotification(type, message) {
        /**
         * Show a notification to the user
         * @param {string} type - The notification type (success, error, warning, info)
         * @param {string} message - The notification message
         */
        console.log(`Notification [${type.toUpperCase()}]: ${message}`);
        
        // Create notification element
        const notification = document.createElement('div');
        notification.className = `alert alert-${type === 'error' ? 'danger' : type} alert-dismissible fade show position-fixed`;
        notification.style.cssText = 'top: 20px; right: 20px; z-index: 9999; max-width: 400px;';
        notification.innerHTML = `
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
        `;
        
        // Add to page
        document.body.appendChild(notification);
        
        // Auto-remove after 5 seconds
        setTimeout(() => {
            if (notification.parentNode) {
                notification.parentNode.removeChild(notification);
            }
        }, 5000);
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
        setTimeout(() => {
            recommendationCard.scrollIntoView({ behavior: 'smooth', block: 'center' });
        }, 300);
    }

    showError(message, agentName = null) {
        // Create a toast-like error message
        const errorDiv = document.createElement('div');
        errorDiv.className = 'alert alert-danger alert-dismissible fade show position-fixed';
        errorDiv.style.cssText = 'top: 20px; right: 20px; z-index: 9999; max-width: 400px;';

        // Include agent name in error message if provided
        const errorTitle = agentName ? `${agentName} Error:` : 'Error:';
        errorDiv.innerHTML = `
            <strong>${errorTitle}</strong> ${message}
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
    // Initialize modal manager
    window.modalManager = new ModalManager();

    // Initialize agent card manager (cache functionality removed)
    window.agentCardManager = new AgentCardManager(window.modalManager);

    // Initialize main app
    new TradingAgentsApp();
});