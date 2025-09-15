/**
 * WebSocket Integration Tests for Modal Agent Reports
 * Tests the integration between WebSocket updates and the modal system
 */

import { describe, it, expect, beforeEach, vi } from 'vitest';
import { JSDOM } from 'jsdom';

// Mock WebSocket
global.WebSocket = vi.fn(() => ({
    readyState: 1, // OPEN
    onopen: null,
    onmessage: null,
    onclose: null,
    onerror: null,
    send: vi.fn(),
    close: vi.fn()
}));

describe('WebSocket Integration with Modal System', () => {
    let dom, document, window, app;

    beforeEach(() => {
        // Setup DOM
        dom = new JSDOM(`
            <!DOCTYPE html>
            <html>
            <head><title>Test</title></head>
            <body>
                <input id="ticker" value="AAPL" />
                <input id="analysisDate" value="2025-09-14" />
                <div id="progressContainer"></div>
                <div id="reportModal" class="modal-overlay" style="display: none;">
                    <div class="modal-container">
                        <div class="modal-header">
                            <h3 class="modal-title">Agent Report</h3>
                            <button class="modal-close">×</button>
                        </div>
                        <div class="modal-body">
                            <div class="loading-state" style="display: none;">Loading...</div>
                            <div class="error-state" style="display: none;">
                                <p class="error-message"></p>
                                <button class="retry-button">Retry</button>
                            </div>
                            <div class="report-content" style="display: none;"></div>
                        </div>
                    </div>
                </div>
            </body>
            </html>
        `, { url: 'http://localhost' });

        document = dom.window.document;
        window = dom.window;
        global.document = document;
        global.window = window;
        global.navigator = { onLine: true };

        // Mock fetch
        global.fetch = vi.fn();

        // Load the app classes (simplified versions for testing)
        const { ReportCache, ModalManager, AgentCardManager, TradingAgentsApp } = loadAppClasses();
        
        // Initialize the app
        app = new TradingAgentsApp();
        app.agentCards = new Map();
    });

    function loadAppClasses() {
        // Simplified versions of the classes for testing
        class ReportCache {
            constructor() {
                this.cache = new Map();
                this.currentTicker = null;
                this.currentDate = null;
            }
            
            setContext(ticker, date) {
                if (this.currentTicker !== ticker || this.currentDate !== date) {
                    this.cache.clear();
                    this.currentTicker = ticker;
                    this.currentDate = date;
                }
            }
            
            getContext() {
                return { ticker: this.currentTicker, date: this.currentDate };
            }
            
            getStats() {
                return {
                    size: this.cache.size,
                    ticker: this.currentTicker,
                    date: this.currentDate,
                    keys: Array.from(this.cache.keys())
                };
            }
        }

        class ModalManager {
            constructor() {
                this.modal = document.getElementById('reportModal');
                this.isModalOpen = false;
            }
            
            open(agentName) {
                this.modal.style.display = 'flex';
                this.isModalOpen = true;
            }
            
            close() {
                this.modal.style.display = 'none';
                this.isModalOpen = false;
            }
            
            isOpen() {
                return this.isModalOpen;
            }
        }

        class AgentCardManager {
            constructor(modalManager, reportCache) {
                this.modalManager = modalManager;
                this.reportCache = reportCache;
            }
            
            updateContext(ticker, date) {
                this.reportCache.setContext(ticker, date);
            }
        }

        class AgentCard {
            constructor(agentName, teamName, element) {
                this.agentName = agentName;
                this.teamName = teamName;
                this.element = element;
                this.status = 'pending';
            }
            
            updateStatus(status) {
                this.status = status;
                this.updateUI();
            }
            
            updateUI() {
                if (this.element) {
                    this.element.setAttribute('data-status', this.status);
                }
            }
        }

        class TradingAgentsApp {
            constructor() {
                this.websocket = null;
                this.analysisInProgress = false;
                this.agentStatuses = {};
                this.agentCards = new Map();
            }

            updateReportCacheContextWithData(ticker, date) {
                if (window.agentCardManager && window.agentCardManager.reportCache) {
                    window.agentCardManager.reportCache.setContext(ticker, date);
                }
            }

            getCurrentContext() {
                const tickerElement = document.getElementById('ticker');
                const dateElement = document.getElementById('analysisDate');
                
                const ticker = tickerElement ? tickerElement.value.toUpperCase().trim() : 'UNKNOWN';
                const date = dateElement ? dateElement.value : new Date().toISOString().split('T')[0];
                
                return { ticker, date };
            }

            updateReportCacheContext() {
                const { ticker, date } = this.getCurrentContext();
                this.updateReportCacheContextWithData(ticker, date);
            }

            handleWebSocketMessage(data) {
                switch (data.type) {
                    case 'agent_status':
                        this.updateAgentStatus(data.agent, data.status);
                        break;
                    case 'analysis_start':
                        this.handleAnalysisStart(data);
                        break;
                    case 'context_change':
                        this.handleContextChange(data);
                        break;
                }
            }

            handleAnalysisStart(data) {
                this.analysisInProgress = true;
                if (data.ticker && data.date) {
                    this.updateReportCacheContextWithData(data.ticker, data.date);
                }
            }

            handleContextChange(data) {
                if (data.ticker && data.date) {
                    const tickerElement = document.getElementById('ticker');
                    const dateElement = document.getElementById('analysisDate');
                    
                    if (tickerElement) tickerElement.value = data.ticker;
                    if (dateElement) dateElement.value = data.date;
                    
                    this.updateReportCacheContextWithData(data.ticker, data.date);
                }
            }

            updateAgentStatus(agent, status) {
                this.agentStatuses[agent] = status;
                
                if (this.agentCards && this.agentCards.has(agent)) {
                    const agentCard = this.agentCards.get(agent);
                    agentCard.updateStatus(status);
                    this.handleAgentStatusChange(agent, status, agentCard);
                }
                
                this.updateReportCacheContext();
            }

            handleAgentStatusChange(agent, status, agentCard) {
                this.updateCardClickability(agentCard, status === 'completed');
            }

            updateCardClickability(agentCard, isClickable) {
                if (!agentCard || !agentCard.element) return;
                
                const cardElement = agentCard.element;
                
                if (isClickable) {
                    cardElement.style.cursor = 'pointer';
                    cardElement.setAttribute('tabindex', '0');
                } else {
                    cardElement.style.cursor = 'default';
                    cardElement.removeAttribute('tabindex');
                }
            }
        }

        return { ReportCache, ModalManager, AgentCardManager, AgentCard, TradingAgentsApp };
    }

    it('should update ReportCache context when WebSocket receives analysis_start message', () => {
        // Setup
        const reportCache = new (loadAppClasses().ReportCache)();
        const modalManager = new (loadAppClasses().ModalManager)();
        window.agentCardManager = new (loadAppClasses().AgentCardManager)(modalManager, reportCache);
        
        // Initial context
        expect(reportCache.getContext()).toEqual({ ticker: null, date: null });
        
        // Simulate WebSocket message
        const message = {
            type: 'analysis_start',
            ticker: 'TSLA',
            date: '2025-09-15'
        };
        
        app.handleWebSocketMessage(message);
        
        // Verify context was updated
        expect(reportCache.getContext()).toEqual({ ticker: 'TSLA', date: '2025-09-15' });
        expect(app.analysisInProgress).toBe(true);
    });

    it('should update form fields and ReportCache when WebSocket receives context_change message', () => {
        // Setup
        const reportCache = new (loadAppClasses().ReportCache)();
        const modalManager = new (loadAppClasses().ModalManager)();
        window.agentCardManager = new (loadAppClasses().AgentCardManager)(modalManager, reportCache);
        
        // Simulate WebSocket message
        const message = {
            type: 'context_change',
            ticker: 'NVDA',
            date: '2025-09-16'
        };
        
        app.handleWebSocketMessage(message);
        
        // Verify form fields were updated
        expect(document.getElementById('ticker').value).toBe('NVDA');
        expect(document.getElementById('analysisDate').value).toBe('2025-09-16');
        
        // Verify ReportCache context was updated
        expect(reportCache.getContext()).toEqual({ ticker: 'NVDA', date: '2025-09-16' });
    });

    it('should make cards clickable when status is completed', () => {
        // Setup agent card
        const cardElement = document.createElement('div');
        cardElement.className = 'agent-card';
        document.body.appendChild(cardElement);
        
        const AgentCard = loadAppClasses().AgentCard;
        const agentCard = new AgentCard('Market Analyst', 'Analyst Team', cardElement);
        app.agentCards.set('Market Analyst', agentCard);
        
        // Simulate WebSocket status update
        const message = {
            type: 'agent_status',
            agent: 'Market Analyst',
            status: 'completed'
        };
        
        app.handleWebSocketMessage(message);
        
        // Verify card is clickable
        expect(cardElement.style.cursor).toBe('pointer');
        expect(cardElement.getAttribute('tabindex')).toBe('0');
        expect(agentCard.status).toBe('completed');
    });

    it('should make cards non-clickable when status is not completed', () => {
        // Setup agent card
        const cardElement = document.createElement('div');
        cardElement.className = 'agent-card';
        document.body.appendChild(cardElement);
        
        const AgentCard = loadAppClasses().AgentCard;
        const agentCard = new AgentCard('Market Analyst', 'Analyst Team', cardElement);
        app.agentCards.set('Market Analyst', agentCard);
        
        // Test different non-completed statuses
        const statuses = ['pending', 'in_progress', 'error'];
        
        statuses.forEach(status => {
            const message = {
                type: 'agent_status',
                agent: 'Market Analyst',
                status: status
            };
            
            app.handleWebSocketMessage(message);
            
            // Verify card is not clickable
            expect(cardElement.style.cursor).toBe('default');
            expect(cardElement.hasAttribute('tabindex')).toBe(false);
            expect(agentCard.status).toBe(status);
        });
    });

    it('should update ReportCache context when agent status changes', () => {
        // Setup
        const reportCache = new (loadAppClasses().ReportCache)();
        const modalManager = new (loadAppClasses().ModalManager)();
        window.agentCardManager = new (loadAppClasses().AgentCardManager)(modalManager, reportCache);
        
        // Set initial context
        document.getElementById('ticker').value = 'AAPL';
        document.getElementById('analysisDate').value = '2025-09-14';
        
        // Setup agent card
        const cardElement = document.createElement('div');
        const AgentCard = loadAppClasses().AgentCard;
        const agentCard = new AgentCard('Market Analyst', 'Analyst Team', cardElement);
        app.agentCards.set('Market Analyst', agentCard);
        
        // Simulate WebSocket status update
        const message = {
            type: 'agent_status',
            agent: 'Market Analyst',
            status: 'completed'
        };
        
        app.handleWebSocketMessage(message);
        
        // Verify ReportCache context was updated
        expect(reportCache.getContext()).toEqual({ ticker: 'AAPL', date: '2025-09-14' });
    });
});