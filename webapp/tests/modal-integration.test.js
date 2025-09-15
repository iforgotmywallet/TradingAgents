/**
 * @vitest-environment jsdom
 * Integration tests for complete modal workflow
 */
import { describe, test, expect, beforeEach, vi, afterEach } from 'vitest';

// Mock the complete modal HTML structure
const createModalHTML = () => `
<div id="reportModal" class="modal-overlay" style="display: none;">
    <div class="modal-container">
        <div class="modal-header">
            <h3 class="modal-title">Agent Report</h3>
            <button class="modal-close" aria-label="Close modal">
                <i class="fas fa-times"></i>
            </button>
        </div>
        <div class="modal-body">
            <div class="loading-state" style="display: none;">
                <div class="modal-spinner"></div>
                <p>Loading report...</p>
            </div>
            <div class="error-state" style="display: none;">
                <p class="error-message"></p>
                <button class="retry-button btn btn-outline-primary btn-sm">
                    <i class="fas fa-redo me-1"></i>Retry
                </button>
            </div>
            <div class="report-content" style="display: none;">
                <!-- Report content loaded dynamically -->
            </div>
        </div>
    </div>
</div>
`;

const createAgentCardsHTML = () => `
<input id="ticker" value="AAPL" />
<input id="analysisDate" value="2025-09-14" />

<div class="team-section">
    <div class="team-header">
        <h5>Analysis Team</h5>
    </div>
    <div class="agent-card" data-status="completed" data-agent="market">
        <div class="card-content">
            <div class="agent-info">
                <span class="agent-name">Market Analyst</span>
                <div class="status-indicator">
                    <span class="status-badge status-completed">COMPLETED</span>
                </div>
            </div>
        </div>
    </div>
    <div class="agent-card" data-status="in_progress" data-agent="news">
        <div class="card-content">
            <div class="agent-info">
                <span class="agent-name">News Analyst</span>
                <div class="status-indicator">
                    <span class="status-badge status-in_progress">IN PROGRESS</span>
                    <div class="loading-spinner"></div>
                </div>
            </div>
        </div>
    </div>
    <div class="agent-card" data-status="completed" data-agent="fundamentals">
        <div class="card-content">
            <div class="agent-info">
                <span class="agent-name">Fundamentals Analyst</span>
                <div class="status-indicator">
                    <span class="status-badge status-completed">COMPLETED</span>
                </div>
            </div>
        </div>
    </div>
    <div class="agent-card" data-status="error" data-agent="sentiment">
        <div class="card-content">
            <div class="agent-info">
                <span class="agent-name">Social Analyst</span>
                <div class="status-indicator">
                    <span class="status-badge status-error">ERROR</span>
                </div>
            </div>
        </div>
    </div>
</div>

<div class="team-section">
    <div class="team-header">
        <h5>Research Team</h5>
    </div>
    <div class="agent-card" data-status="pending" data-agent="investment">
        <div class="card-content">
            <div class="agent-info">
                <span class="agent-name">Bull Researcher</span>
                <div class="status-indicator">
                    <span class="status-badge status-pending">PENDING</span>
                </div>
            </div>
        </div>
    </div>
</div>
`;

// Import the classes (in real implementation these would be from app.js)
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
        this.modal.addEventListener('click', (e) => {
            if (e.target === this.modal) {
                this.close();
            }
        });
        
        this.closeButton.addEventListener('click', () => {
            this.close();
        });
        
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape' && this.isOpen()) {
                this.close();
            }
        });
        
        this.retryButton.addEventListener('click', () => {
            if (this.currentRetryCallback) {
                this.currentRetryCallback();
            }
        });
        
        this.modal.querySelector('.modal-container').addEventListener('click', (e) => {
            e.stopPropagation();
        });
    }
    
    open(agentName) {
        this.modalTitle.textContent = `${agentName} Report`;
        this.modal.style.display = 'flex';
        this.isModalOpen = true;
        document.body.style.overflow = 'hidden';
        this.showLoading();
        document.body.classList.add('modal-open');
        this.closeButton.focus();
    }
    
    close() {
        this.modal.style.display = 'none';
        this.isModalOpen = false;
        document.body.style.overflow = '';
        document.body.classList.remove('modal-open');
        this.currentRetryCallback = null;
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
        this.reportContent.scrollTop = 0;
    }
    
    clearContent() {
        this.reportContent.innerHTML = '';
        this.errorMessage.textContent = '';
        this.currentRetryCallback = null;
    }
}

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
    }
    
    async handleCardClick(card) {
        const agentNameElement = card.querySelector('.agent-name');
        if (!agentNameElement) return;
        
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
            this.modalManager.showError(
                'Failed to load report. Please try again.',
                () => this.handleCardClick(card)
            );
        }
    }
    
    async loadReport(agentKey, agentName) {
        const { ticker, date } = this.getCurrentContext();
        
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

describe('Modal Integration Tests', () => {
    let modalManager;
    let reportCache;
    let agentCardManager;
    
    beforeEach(() => {
        // Set up complete DOM structure
        document.body.innerHTML = createModalHTML() + createAgentCardsHTML();
        
        // Mock fetch
        global.fetch = vi.fn();
        
        // Initialize components
        reportCache = new ReportCache();
        modalManager = new ModalManager();
        agentCardManager = new AgentCardManager(modalManager, reportCache);
        
        // Set initial context
        reportCache.setContext('AAPL', '2025-09-14');
    });
    
    afterEach(() => {
        vi.clearAllMocks();
        document.body.innerHTML = '';
        document.body.style.overflow = '';
        document.body.classList.remove('modal-open');
    });
    
    describe('Complete User Workflow', () => {
        test('should complete full workflow: click card -> load report -> display in modal', async () => {
            const marketCard = document.querySelector('.agent-card[data-agent="market"]');
            const reportContent = '<h1>Market Analysis Report</h1><p>Detailed market analysis content here.</p>';
            
            // Mock successful API response
            global.fetch.mockResolvedValueOnce({
                ok: true,
                json: async () => ({
                    success: true,
                    report_content: reportContent,
                    report_file: 'market_report.md'
                })
            });
            
            // Simulate user clicking on completed card
            marketCard.click();
            
            // Wait for async operations
            await new Promise(resolve => setTimeout(resolve, 0));
            
            // Verify modal opened
            expect(modalManager.isOpen()).toBe(true);
            expect(modalManager.modalTitle.textContent).toBe('Market Analyst Report');
            
            // Verify body scroll is prevented
            expect(document.body.style.overflow).toBe('hidden');
            expect(document.body.classList.contains('modal-open')).toBe(true);
            
            // Verify content is displayed
            expect(modalManager.reportContent.style.display).toBe('block');
            expect(modalManager.reportContent.innerHTML).toContain('Market Analyst Analysis Report');
            expect(modalManager.reportContent.innerHTML).toContain('Source: market_report.md');
            expect(modalManager.reportContent.innerHTML).toContain(reportContent);
            
            // Verify API was called correctly
            expect(global.fetch).toHaveBeenCalledWith('/api/reports/AAPL/2025-09-14/market');
            
            // Verify content is cached
            expect(reportCache.has('market')).toBe(true);
        });
        
        test('should use cached content on second click', async () => {
            const marketCard = document.querySelector('.agent-card[data-agent="market"]');
            const cachedContent = '<div>Cached market report content</div>';
            
            // Pre-populate cache
            reportCache.set('market', cachedContent);
            
            // Simulate user clicking on completed card
            marketCard.click();
            
            // Wait for async operations
            await new Promise(resolve => setTimeout(resolve, 0));
            
            // Verify modal opened with cached content
            expect(modalManager.isOpen()).toBe(true);
            expect(modalManager.reportContent.innerHTML).toBe(cachedContent);
            
            // Verify API was not called
            expect(global.fetch).not.toHaveBeenCalled();
        });
        
        test('should handle error and retry workflow', async () => {
            const marketCard = document.querySelector('.agent-card[data-agent="market"]');
            
            // Mock API error on first call
            global.fetch.mockRejectedValueOnce(new Error('Network error'));
            
            // Simulate user clicking on completed card
            marketCard.click();
            
            // Wait for async operations
            await new Promise(resolve => setTimeout(resolve, 0));
            
            // Verify error state
            expect(modalManager.isOpen()).toBe(true);
            expect(modalManager.errorState.style.display).toBe('flex');
            expect(modalManager.errorMessage.textContent).toBe('Failed to load report. Please try again.');
            expect(modalManager.retryButton.style.display).toBe('inline-block');
            
            // Mock successful response for retry
            const reportContent = '<h1>Market Analysis</h1>';
            global.fetch.mockResolvedValueOnce({
                ok: true,
                json: async () => ({
                    success: true,
                    report_content: reportContent,
                    report_file: 'market_report.md'
                })
            });
            
            // Simulate user clicking retry
            modalManager.retryButton.click();
            
            // Wait for async operations
            await new Promise(resolve => setTimeout(resolve, 0));
            
            // Verify successful retry
            expect(modalManager.reportContent.style.display).toBe('block');
            expect(modalManager.reportContent.innerHTML).toContain(reportContent);
            expect(global.fetch).toHaveBeenCalledTimes(2);
        });
        
        test('should close modal with ESC key', async () => {
            const marketCard = document.querySelector('.agent-card[data-agent="market"]');
            
            global.fetch.mockResolvedValueOnce({
                ok: true,
                json: async () => ({
                    success: true,
                    report_content: '<h1>Test</h1>',
                    report_file: 'test.md'
                })
            });
            
            // Open modal
            marketCard.click();
            await new Promise(resolve => setTimeout(resolve, 0));
            
            expect(modalManager.isOpen()).toBe(true);
            
            // Press ESC key
            const escEvent = new KeyboardEvent('keydown', { key: 'Escape' });
            document.dispatchEvent(escEvent);
            
            // Verify modal closed
            expect(modalManager.isOpen()).toBe(false);
            expect(document.body.style.overflow).toBe('');
            expect(document.body.classList.contains('modal-open')).toBe(false);
        });
        
        test('should close modal on background click', async () => {
            const marketCard = document.querySelector('.agent-card[data-agent="market"]');
            
            global.fetch.mockResolvedValueOnce({
                ok: true,
                json: async () => ({
                    success: true,
                    report_content: '<h1>Test</h1>',
                    report_file: 'test.md'
                })
            });
            
            // Open modal
            marketCard.click();
            await new Promise(resolve => setTimeout(resolve, 0));
            
            expect(modalManager.isOpen()).toBe(true);
            
            // Click on modal background
            modalManager.modal.click();
            
            // Verify modal closed
            expect(modalManager.isOpen()).toBe(false);
        });
        
        test('should not close modal on content click', async () => {
            const marketCard = document.querySelector('.agent-card[data-agent="market"]');
            
            global.fetch.mockResolvedValueOnce({
                ok: true,
                json: async () => ({
                    success: true,
                    report_content: '<h1>Test</h1>',
                    report_file: 'test.md'
                })
            });
            
            // Open modal
            marketCard.click();
            await new Promise(resolve => setTimeout(resolve, 0));
            
            expect(modalManager.isOpen()).toBe(true);
            
            // Click on modal content
            const modalContainer = modalManager.modal.querySelector('.modal-container');
            modalContainer.click();
            
            // Verify modal remains open
            expect(modalManager.isOpen()).toBe(true);
        });
    });
    
    describe('Multiple Agent Workflow', () => {
        test('should handle multiple agents with different states', async () => {
            const marketCard = document.querySelector('.agent-card[data-agent="market"]');
            const fundamentalsCard = document.querySelector('.agent-card[data-agent="fundamentals"]');
            const newsCard = document.querySelector('.agent-card[data-agent="news"]'); // in_progress
            const sentimentCard = document.querySelector('.agent-card[data-agent="sentiment"]'); // error
            
            // Mock responses for different agents
            global.fetch
                .mockResolvedValueOnce({
                    ok: true,
                    json: async () => ({
                        success: true,
                        report_content: '<h1>Market Report</h1>',
                        report_file: 'market_report.md'
                    })
                })
                .mockResolvedValueOnce({
                    ok: true,
                    json: async () => ({
                        success: true,
                        report_content: '<h1>Fundamentals Report</h1>',
                        report_file: 'fundamentals_report.md'
                    })
                });
            
            // Test first completed card
            await agentCardManager.handleCardClick(marketCard);
            expect(modalManager.isOpen()).toBe(true);
            expect(modalManager.modalTitle.textContent).toBe('Market Analyst Report');
            modalManager.close();
            
            // Test second completed card
            await agentCardManager.handleCardClick(fundamentalsCard);
            expect(modalManager.isOpen()).toBe(true);
            expect(modalManager.modalTitle.textContent).toBe('Fundamentals Analyst Report');
            modalManager.close();
            
            // Test non-completed cards don't work (they don't have the right data-status)
            newsCard.click();
            expect(modalManager.isOpen()).toBe(false);
            
            sentimentCard.click();
            expect(modalManager.isOpen()).toBe(false);
            
            // Verify both reports are cached
            expect(reportCache.has('market')).toBe(true);
            expect(reportCache.has('fundamentals')).toBe(true);
        });
        
        test('should clear cache when context changes', async () => {
            const marketCard = document.querySelector('.agent-card[data-agent="market"]');
            
            // Load and cache a report
            global.fetch.mockResolvedValueOnce({
                ok: true,
                json: async () => ({
                    success: true,
                    report_content: '<h1>Market Report</h1>',
                    report_file: 'market_report.md'
                })
            });
            
            marketCard.click();
            await new Promise(resolve => setTimeout(resolve, 0));
            modalManager.close();
            
            expect(reportCache.has('market')).toBe(true);
            
            // Change context (simulate switching to different stock)
            document.getElementById('ticker').value = 'TSLA';
            agentCardManager.updateContext('TSLA', '2025-09-14');
            
            // Verify cache was cleared
            expect(reportCache.has('market')).toBe(false);
            expect(reportCache.currentTicker).toBe('TSLA');
        });
    });
    
    describe('Error Scenarios', () => {
        test('should handle 404 responses gracefully', async () => {
            const marketCard = document.querySelector('.agent-card[data-agent="market"]');
            
            global.fetch.mockResolvedValueOnce({
                ok: false,
                status: 404,
                statusText: 'Not Found'
            });
            
            await agentCardManager.handleCardClick(marketCard);
            
            expect(modalManager.isOpen()).toBe(true);
            expect(modalManager.reportContent.style.display).toBe('block');
            expect(modalManager.reportContent.innerHTML).toContain('Report Not Available');
            expect(modalManager.reportContent.innerHTML).toContain('Market Analyst');
        });
        
        test('should handle network errors with retry', async () => {
            const marketCard = document.querySelector('.agent-card[data-agent="market"]');
            
            // First call fails
            global.fetch.mockRejectedValueOnce(new Error('Network error'));
            
            marketCard.click();
            await new Promise(resolve => setTimeout(resolve, 0));
            
            expect(modalManager.errorState.style.display).toBe('flex');
            expect(modalManager.currentRetryCallback).toBeTruthy();
            
            // Retry succeeds
            global.fetch.mockResolvedValueOnce({
                ok: true,
                json: async () => ({
                    success: true,
                    report_content: '<h1>Success</h1>',
                    report_file: 'test.md'
                })
            });
            
            modalManager.retryButton.click();
            await new Promise(resolve => setTimeout(resolve, 0));
            
            expect(modalManager.reportContent.style.display).toBe('block');
            expect(modalManager.reportContent.innerHTML).toContain('Success');
        });
        
        test('should handle malformed API responses', async () => {
            const marketCard = document.querySelector('.agent-card[data-agent="market"]');
            
            global.fetch.mockResolvedValueOnce({
                ok: true,
                json: async () => ({
                    success: false,
                    error: 'Invalid request'
                })
            });
            
            await agentCardManager.handleCardClick(marketCard);
            
            expect(modalManager.isOpen()).toBe(true);
            expect(modalManager.reportContent.innerHTML).toContain('Report Not Available');
        });
    });
    
    describe('Accessibility and UX', () => {
        test('should focus close button when modal opens', async () => {
            const marketCard = document.querySelector('.agent-card[data-agent="market"]');
            
            global.fetch.mockResolvedValueOnce({
                ok: true,
                json: async () => ({
                    success: true,
                    report_content: '<h1>Test</h1>',
                    report_file: 'test.md'
                })
            });
            
            const focusSpy = vi.spyOn(modalManager.closeButton, 'focus');
            
            marketCard.click();
            await new Promise(resolve => setTimeout(resolve, 0));
            
            expect(focusSpy).toHaveBeenCalled();
        });
        
        test('should scroll content to top when showing new content', async () => {
            const marketCard = document.querySelector('.agent-card[data-agent="market"]');
            
            global.fetch.mockResolvedValueOnce({
                ok: true,
                json: async () => ({
                    success: true,
                    report_content: '<h1>Test</h1>',
                    report_file: 'test.md'
                })
            });
            
            marketCard.click();
            await new Promise(resolve => setTimeout(resolve, 10));
            
            // Set scroll position after content is loaded
            modalManager.reportContent.scrollTop = 100;
            
            // Trigger showContent again to test scroll reset
            modalManager.showContent('<h1>Test Content</h1>');
            
            expect(modalManager.reportContent.scrollTop).toBe(0);
        });
        
        test('should prevent body scroll when modal is open', async () => {
            const marketCard = document.querySelector('.agent-card[data-agent="market"]');
            
            global.fetch.mockResolvedValueOnce({
                ok: true,
                json: async () => ({
                    success: true,
                    report_content: '<h1>Test</h1>',
                    report_file: 'test.md'
                })
            });
            
            expect(document.body.style.overflow).toBe('');
            
            marketCard.click();
            await new Promise(resolve => setTimeout(resolve, 0));
            
            expect(document.body.style.overflow).toBe('hidden');
            expect(document.body.classList.contains('modal-open')).toBe(true);
            
            modalManager.close();
            
            expect(document.body.style.overflow).toBe('');
            expect(document.body.classList.contains('modal-open')).toBe(false);
        });
    });
});