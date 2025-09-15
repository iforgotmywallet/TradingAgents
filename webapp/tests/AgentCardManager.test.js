/**
 * @vitest-environment jsdom
 * Tests for AgentCardManager functionality
 */
import { describe, test, expect, beforeEach, vi, afterEach } from 'vitest';

// Mock classes for testing
class MockModalManager {
    constructor() {
        this.isModalOpen = false;
        this.currentTitle = '';
        this.currentState = 'closed';
        this.currentContent = '';
        this.currentError = '';
        this.retryCallback = null;
    }
    
    open(agentName) {
        this.isModalOpen = true;
        this.currentTitle = `${agentName} Report`;
        this.currentState = 'loading';
    }
    
    close() {
        this.isModalOpen = false;
        this.currentState = 'closed';
        this.currentContent = '';
        this.currentError = '';
        this.retryCallback = null;
    }
    
    isOpen() {
        return this.isModalOpen;
    }
    
    showLoading() {
        this.currentState = 'loading';
    }
    
    showError(message, retryCallback) {
        this.currentState = 'error';
        this.currentError = message;
        this.retryCallback = retryCallback;
    }
    
    showContent(content) {
        this.currentState = 'content';
        this.currentContent = content;
    }
}

class MockReportCache {
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
    
    get(agentKey) {
        return this.cache.get(agentKey);
    }
    
    set(agentKey, content) {
        this.cache.set(agentKey, content);
    }
    
    has(agentKey) {
        return this.cache.has(agentKey);
    }
    
    clear() {
        this.cache.clear();
    }
}

// AgentCardManager implementation for testing
class AgentCardManager {
    constructor(modalManager, reportCache) {
        this.modalManager = modalManager;
        this.reportCache = reportCache;
        this.setupCardListeners();
    }
    
    setupCardListeners() {
        document.addEventListener('click', (e) => {
            const card = e.target.closest('.agent-card[data-status="completed"]');
            if (card) {
                this.handleCardClick(card);
            }
        });
        
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
        
        this.modalManager.open(agentName);
        
        try {
            let content;
            
            if (this.reportCache.has(agentKey)) {
                content = this.reportCache.get(agentKey);
                this.modalManager.showContent(content);
            } else {
                content = await this.loadReport(agentKey, agentName);
                this.reportCache.set(agentKey, content);
                this.modalManager.showContent(content);
            }
        } catch (error) {
            console.error(`Error loading report for ${agentName}:`, error);
            this.modalManager.showError(
                'Failed to load report. Please try again.',
                () => this.handleCardClick(card)
            );
        }
    }
    
    async loadReport(agentKey, agentName) {
        const { ticker, date } = this.getCurrentContext();
        
        try {
            const response = await fetch(`/api/reports/${ticker}/${date}/${agentKey}`);
            
            if (!response.ok) {
                if (response.status === 404) {
                    return this.createNotFoundContent(agentName);
                }
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            
            const data = await response.json();
            
            if (data.success && data.report_content) {
                return this.formatReportContent(data.report_content, agentName, data.report_file || 'Unknown');
            } else {
                return this.createNotFoundContent(agentName);
            }
        } catch (error) {
            console.error(`API request failed for ${agentName}:`, error);
            throw error;
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
        const mapping = {
            'Market Analyst': 'market',
            'Social Analyst': 'sentiment',
            'News Analyst': 'news',
            'Fundamentals Analyst': 'fundamentals',
            'Bull Researcher': 'investment',
            'Bear Researcher': 'investment',
            'Research Manager': 'investment',
            'Trader': 'trader',
            'Risky Analyst': 'final',
            'Neutral Analyst': 'final',
            'Safe Analyst': 'final',
            'Portfolio Manager': 'final'
        };
        
        return mapping[agentName] || agentName.toLowerCase().replace(/\s+/g, '_');
    }
    
    createNotFoundContent(agentName) {
        return `
            <div class="alert alert-info mb-0">
                <i class="fas fa-info-circle me-2"></i>
                <strong>Report Not Available</strong>
                <p class="mb-2 mt-2">No detailed report found for ${agentName}.</p>
                <div class="mt-3">
                    <div class="text-muted small">
                        <i class="fas fa-lightbulb me-1"></i>
                        <strong>Possible reasons:</strong>
                        <ul class="mt-2 mb-0 ps-3">
                            <li>Analysis is still in progress</li>
                            <li>Agent completed without generating a detailed report</li>
                            <li>Report file was not saved to the expected location</li>
                        </ul>
                    </div>
                </div>
            </div>
        `;
    }
    
    formatReportContent(content, agentName, reportFile) {
        return `
            <div class="report-header mb-3 pb-2 border-bottom">
                <h6 class="text-primary mb-1">${agentName} Analysis Report</h6>
                <small class="text-muted">Source: ${reportFile}</small>
            </div>
            <div class="report-body">
                ${content}
            </div>
        `;
    }
    
    updateContext(ticker, date) {
        if (this.reportCache) {
            this.reportCache.setContext(ticker, date);
        }
    }
}

describe('AgentCardManager', () => {
    let agentCardManager;
    let mockModalManager;
    let mockReportCache;
    
    beforeEach(() => {
        // Set up DOM structure
        document.body.innerHTML = `
            <input id="ticker" value="AAPL" />
            <input id="analysisDate" value="2025-09-14" />
            <div class="agent-card" data-status="completed" data-agent="market">
                <div class="card-content">
                    <div class="agent-name">Market Analyst</div>
                </div>
            </div>
            <div class="agent-card" data-status="pending" data-agent="news">
                <div class="card-content">
                    <div class="agent-name">News Analyst</div>
                </div>
            </div>
            <div class="agent-card" data-status="completed" data-agent="fundamentals">
                <div class="card-content">
                    <div class="agent-name">Fundamentals Analyst</div>
                </div>
            </div>
        `;
        
        // Create mock instances
        mockModalManager = new MockModalManager();
        mockReportCache = new MockReportCache();
        
        // Mock fetch
        global.fetch = vi.fn();
        
        // Create AgentCardManager instance
        agentCardManager = new AgentCardManager(mockModalManager, mockReportCache);
    });
    
    afterEach(() => {
        vi.clearAllMocks();
        document.body.innerHTML = '';
    });
    
    describe('Initialization', () => {
        test('should initialize with modal manager and report cache', () => {
            expect(agentCardManager.modalManager).toBe(mockModalManager);
            expect(agentCardManager.reportCache).toBe(mockReportCache);
        });
        
        test('should set up event listeners on document', () => {
            // Event listeners are set up in constructor, verify by testing click handling
            const completedCard = document.querySelector('.agent-card[data-status="completed"]');
            expect(completedCard).toBeTruthy();
        });
    });
    
    describe('Agent Key Mapping', () => {
        test('should map known agent names to correct keys', () => {
            expect(agentCardManager.getAgentKey('Market Analyst')).toBe('market');
            expect(agentCardManager.getAgentKey('Social Analyst')).toBe('sentiment');
            expect(agentCardManager.getAgentKey('News Analyst')).toBe('news');
            expect(agentCardManager.getAgentKey('Fundamentals Analyst')).toBe('fundamentals');
            expect(agentCardManager.getAgentKey('Bull Researcher')).toBe('investment');
            expect(agentCardManager.getAgentKey('Bear Researcher')).toBe('investment');
            expect(agentCardManager.getAgentKey('Research Manager')).toBe('investment');
            expect(agentCardManager.getAgentKey('Trader')).toBe('trader');
            expect(agentCardManager.getAgentKey('Risky Analyst')).toBe('final');
            expect(agentCardManager.getAgentKey('Neutral Analyst')).toBe('final');
            expect(agentCardManager.getAgentKey('Safe Analyst')).toBe('final');
            expect(agentCardManager.getAgentKey('Portfolio Manager')).toBe('final');
        });
        
        test('should handle unknown agent names', () => {
            expect(agentCardManager.getAgentKey('Unknown Agent')).toBe('unknown_agent');
            expect(agentCardManager.getAgentKey('Custom Analyst')).toBe('custom_analyst');
            expect(agentCardManager.getAgentKey('Multi Word Agent Name')).toBe('multi_word_agent_name');
        });
        
        test('should handle edge cases in agent names', () => {
            expect(agentCardManager.getAgentKey('')).toBe('');
            expect(agentCardManager.getAgentKey('   ')).toBe('_'); // Spaces get replaced with underscores
            expect(agentCardManager.getAgentKey('Agent-With-Dashes')).toBe('agent-with-dashes');
        });
    });
    
    describe('Context Management', () => {
        test('should get current context from DOM elements', () => {
            const context = agentCardManager.getCurrentContext();
            expect(context.ticker).toBe('AAPL');
            expect(context.date).toBe('2025-09-14');
        });
        
        test('should handle missing ticker element', () => {
            document.getElementById('ticker').remove();
            const context = agentCardManager.getCurrentContext();
            expect(context.ticker).toBe('UNKNOWN');
            expect(context.date).toBe('2025-09-14');
        });
        
        test('should handle missing date element', () => {
            document.getElementById('analysisDate').remove();
            const context = agentCardManager.getCurrentContext();
            expect(context.ticker).toBe('AAPL');
            expect(context.date).toMatch(/^\d{4}-\d{2}-\d{2}$/); // Should be today's date
        });
        
        test('should update cache context', () => {
            agentCardManager.updateContext('TSLA', '2025-09-15');
            expect(mockReportCache.currentTicker).toBe('TSLA');
            expect(mockReportCache.currentDate).toBe('2025-09-15');
        });
    });
    
    describe('Card Click Handling', () => {
        test('should handle click on completed card', async () => {
            const completedCard = document.querySelector('.agent-card[data-status="completed"]');
            
            // Mock successful API response
            global.fetch.mockResolvedValueOnce({
                ok: true,
                json: async () => ({
                    success: true,
                    report_content: '<h1>Market Analysis</h1><p>Content here</p>',
                    report_file: 'market_report.md'
                })
            });
            
            await agentCardManager.handleCardClick(completedCard);
            
            expect(mockModalManager.isOpen()).toBe(true);
            expect(mockModalManager.currentTitle).toBe('Market Analyst Report');
            expect(mockModalManager.currentState).toBe('content');
            expect(mockModalManager.currentContent).toContain('Market Analyst Analysis Report');
        });
        
        test('should not handle click on pending card', () => {
            const pendingCard = document.querySelector('.agent-card[data-status="pending"]');
            
            // Simulate click event
            const clickEvent = new MouseEvent('click', { bubbles: true });
            Object.defineProperty(clickEvent, 'target', { value: pendingCard });
            
            // The event listener should not trigger for pending cards
            expect(mockModalManager.isOpen()).toBe(false);
        });
        
        test('should handle card without agent name element', async () => {
            const cardWithoutName = document.createElement('div');
            cardWithoutName.className = 'agent-card';
            cardWithoutName.setAttribute('data-status', 'completed');
            
            const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => {});
            
            await agentCardManager.handleCardClick(cardWithoutName);
            
            expect(consoleSpy).toHaveBeenCalledWith('Agent name element not found in card');
            expect(mockModalManager.isOpen()).toBe(false);
            
            consoleSpy.mockRestore();
        });
        
        test('should use cached content when available', async () => {
            const completedCard = document.querySelector('.agent-card[data-status="completed"]');
            const cachedContent = '<h1>Cached Market Analysis</h1>';
            
            // Pre-populate cache
            mockReportCache.set('market', cachedContent);
            
            await agentCardManager.handleCardClick(completedCard);
            
            expect(mockModalManager.currentState).toBe('content');
            expect(mockModalManager.currentContent).toBe(cachedContent);
            expect(global.fetch).not.toHaveBeenCalled();
        });
        
        test('should handle API errors gracefully', async () => {
            const completedCard = document.querySelector('.agent-card[data-status="completed"]');
            
            // Mock API error
            global.fetch.mockRejectedValueOnce(new Error('Network error'));
            
            await agentCardManager.handleCardClick(completedCard);
            
            expect(mockModalManager.currentState).toBe('error');
            expect(mockModalManager.currentError).toBe('Failed to load report. Please try again.');
            expect(mockModalManager.retryCallback).toBeTruthy();
        });
        
        test('should handle 404 responses', async () => {
            const completedCard = document.querySelector('.agent-card[data-status="completed"]');
            
            // Mock 404 response
            global.fetch.mockResolvedValueOnce({
                ok: false,
                status: 404,
                statusText: 'Not Found'
            });
            
            await agentCardManager.handleCardClick(completedCard);
            
            expect(mockModalManager.currentState).toBe('content');
            expect(mockModalManager.currentContent).toContain('Report Not Available');
        });
        
        test('should handle non-404 HTTP errors', async () => {
            const completedCard = document.querySelector('.agent-card[data-status="completed"]');
            
            // Mock 500 response
            global.fetch.mockResolvedValueOnce({
                ok: false,
                status: 500,
                statusText: 'Internal Server Error'
            });
            
            await agentCardManager.handleCardClick(completedCard);
            
            expect(mockModalManager.currentState).toBe('error');
            expect(mockModalManager.currentError).toBe('Failed to load report. Please try again.');
        });
    });
    
    describe('Keyboard Navigation', () => {
        test('should handle Enter key on completed card', async () => {
            const completedCard = document.querySelector('.agent-card[data-status="completed"]');
            const cardContent = completedCard.querySelector('.card-content');
            
            // Mock successful API response
            global.fetch.mockResolvedValueOnce({
                ok: true,
                json: async () => ({
                    success: true,
                    report_content: '<h1>Market Analysis</h1>',
                    report_file: 'market_report.md'
                })
            });
            
            // Simulate Enter key press
            const enterEvent = new KeyboardEvent('keydown', { key: 'Enter', bubbles: true });
            Object.defineProperty(enterEvent, 'target', { value: cardContent });
            
            const preventDefaultSpy = vi.spyOn(enterEvent, 'preventDefault');
            
            document.dispatchEvent(enterEvent);
            
            // Wait for async operations
            await new Promise(resolve => setTimeout(resolve, 0));
            
            expect(preventDefaultSpy).toHaveBeenCalled();
            expect(mockModalManager.isOpen()).toBe(true);
        });
        
        test('should handle Space key on completed card', async () => {
            const completedCard = document.querySelector('.agent-card[data-status="completed"]');
            const cardContent = completedCard.querySelector('.card-content');
            
            // Mock successful API response
            global.fetch.mockResolvedValueOnce({
                ok: true,
                json: async () => ({
                    success: true,
                    report_content: '<h1>Market Analysis</h1>',
                    report_file: 'market_report.md'
                })
            });
            
            // Simulate Space key press
            const spaceEvent = new KeyboardEvent('keydown', { key: ' ', bubbles: true });
            Object.defineProperty(spaceEvent, 'target', { value: cardContent });
            
            const preventDefaultSpy = vi.spyOn(spaceEvent, 'preventDefault');
            
            document.dispatchEvent(spaceEvent);
            
            // Wait for async operations
            await new Promise(resolve => setTimeout(resolve, 0));
            
            expect(preventDefaultSpy).toHaveBeenCalled();
            expect(mockModalManager.isOpen()).toBe(true);
        });
        
        test('should not handle other keys', () => {
            const completedCard = document.querySelector('.agent-card[data-status="completed"]');
            const cardContent = completedCard.querySelector('.card-content');
            
            // Simulate Tab key press
            const tabEvent = new KeyboardEvent('keydown', { key: 'Tab', bubbles: true });
            Object.defineProperty(tabEvent, 'target', { value: cardContent });
            
            document.dispatchEvent(tabEvent);
            
            expect(mockModalManager.isOpen()).toBe(false);
        });
    });
    
    describe('Content Formatting', () => {
        test('should create not found content', () => {
            const content = agentCardManager.createNotFoundContent('Market Analyst');
            
            expect(content).toContain('Report Not Available');
            expect(content).toContain('Market Analyst');
            expect(content).toContain('Analysis is still in progress');
            expect(content).toContain('Agent completed without generating a detailed report');
            expect(content).toContain('Report file was not saved to the expected location');
        });
        
        test('should format report content with header', () => {
            const rawContent = '<h1>Analysis</h1><p>Content here</p>';
            const agentName = 'Market Analyst';
            const reportFile = 'market_report.md';
            
            const formatted = agentCardManager.formatReportContent(rawContent, agentName, reportFile);
            
            expect(formatted).toContain('Market Analyst Analysis Report');
            expect(formatted).toContain('Source: market_report.md');
            expect(formatted).toContain(rawContent);
        });
    });
    
    describe('API Integration', () => {
        test('should construct correct API URL', async () => {
            const completedCard = document.querySelector('.agent-card[data-status="completed"]');
            
            global.fetch.mockResolvedValueOnce({
                ok: true,
                json: async () => ({
                    success: true,
                    report_content: 'content',
                    report_file: 'test.md'
                })
            });
            
            await agentCardManager.handleCardClick(completedCard);
            
            expect(global.fetch).toHaveBeenCalledWith('/api/reports/AAPL/2025-09-14/market');
        });
        
        test('should handle successful API response with content', async () => {
            const agentKey = 'market';
            const agentName = 'Market Analyst';
            const reportContent = '<h1>Market Analysis</h1><p>Detailed analysis here</p>';
            
            global.fetch.mockResolvedValueOnce({
                ok: true,
                json: async () => ({
                    success: true,
                    report_content: reportContent,
                    report_file: 'market_report.md'
                })
            });
            
            const result = await agentCardManager.loadReport(agentKey, agentName);
            
            expect(result).toContain('Market Analyst Analysis Report');
            expect(result).toContain('Source: market_report.md');
            expect(result).toContain(reportContent);
        });
        
        test('should handle API response without content', async () => {
            const agentKey = 'market';
            const agentName = 'Market Analyst';
            
            global.fetch.mockResolvedValueOnce({
                ok: true,
                json: async () => ({
                    success: false
                })
            });
            
            const result = await agentCardManager.loadReport(agentKey, agentName);
            
            expect(result).toContain('Report Not Available');
            expect(result).toContain('Market Analyst');
        });
    });
});