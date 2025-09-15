/**
 * @vitest-environment jsdom
 */

import { vi } from 'vitest';

// Mock HTML structure for testing
const mockModalHTML = `
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

// Import ModalManager class (we'll need to extract it to a separate file or mock it)
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

describe('ModalManager', () => {
    let modalManager;
    
    beforeEach(() => {
        // Set up DOM
        document.body.innerHTML = mockModalHTML;
        modalManager = new ModalManager();
    });
    
    afterEach(() => {
        // Clean up
        document.body.innerHTML = '';
        document.body.style.overflow = '';
        document.body.classList.remove('modal-open');
    });
    
    describe('Initialization', () => {
        test('should initialize with modal closed', () => {
            expect(modalManager.isOpen()).toBe(false);
            expect(modalManager.modal.style.display).toBe('none');
        });
        
        test('should find all required DOM elements', () => {
            expect(modalManager.modal).toBeTruthy();
            expect(modalManager.modalTitle).toBeTruthy();
            expect(modalManager.loadingState).toBeTruthy();
            expect(modalManager.errorState).toBeTruthy();
            expect(modalManager.reportContent).toBeTruthy();
            expect(modalManager.closeButton).toBeTruthy();
            expect(modalManager.retryButton).toBeTruthy();
            expect(modalManager.errorMessage).toBeTruthy();
        });
    });
    
    describe('Open/Close functionality', () => {
        test('should open modal with agent name', () => {
            modalManager.open('Market Analyst');
            
            expect(modalManager.isOpen()).toBe(true);
            expect(modalManager.modal.style.display).toBe('flex');
            expect(modalManager.modalTitle.textContent).toBe('Market Analyst Report');
            expect(document.body.style.overflow).toBe('hidden');
            expect(document.body.classList.contains('modal-open')).toBe(true);
        });
        
        test('should close modal and restore body state', () => {
            modalManager.open('Market Analyst');
            modalManager.close();
            
            expect(modalManager.isOpen()).toBe(false);
            expect(modalManager.modal.style.display).toBe('none');
            expect(document.body.style.overflow).toBe('');
            expect(document.body.classList.contains('modal-open')).toBe(false);
        });
        
        test('should show loading state when opened', () => {
            modalManager.open('Market Analyst');
            
            expect(modalManager.isLoading()).toBe(true);
            expect(modalManager.loadingState.style.display).toBe('flex');
            expect(modalManager.errorState.style.display).toBe('none');
            expect(modalManager.reportContent.style.display).toBe('none');
        });
    });
    
    describe('State management', () => {
        beforeEach(() => {
            modalManager.open('Test Agent');
        });
        
        test('should show loading state', () => {
            modalManager.showLoading();
            
            expect(modalManager.isLoading()).toBe(true);
            expect(modalManager.loadingState.style.display).toBe('flex');
            expect(modalManager.errorState.style.display).toBe('none');
            expect(modalManager.reportContent.style.display).toBe('none');
        });
        
        test('should show error state with message', () => {
            const errorMessage = 'Failed to load report';
            modalManager.showError(errorMessage);
            
            expect(modalManager.isShowingError()).toBe(true);
            expect(modalManager.errorState.style.display).toBe('flex');
            expect(modalManager.loadingState.style.display).toBe('none');
            expect(modalManager.reportContent.style.display).toBe('none');
            expect(modalManager.errorMessage.textContent).toBe(errorMessage);
        });
        
        test('should show error state with retry callback', () => {
            const retryCallback = vi.fn();
            modalManager.showError('Error message', retryCallback);
            
            expect(modalManager.currentRetryCallback).toBe(retryCallback);
            expect(modalManager.retryButton.style.display).toBe('inline-block');
        });
        
        test('should show error state without retry callback', () => {
            modalManager.showError('Error message');
            
            expect(modalManager.currentRetryCallback).toBe(null);
            expect(modalManager.retryButton.style.display).toBe('none');
        });
        
        test('should show content', () => {
            const content = '<h1>Test Report</h1><p>Report content</p>';
            modalManager.showContent(content);
            
            expect(modalManager.isShowingContent()).toBe(true);
            expect(modalManager.reportContent.style.display).toBe('block');
            expect(modalManager.loadingState.style.display).toBe('none');
            expect(modalManager.errorState.style.display).toBe('none');
            expect(modalManager.reportContent.innerHTML).toBe(content);
        });
        
        test('should clear content', () => {
            modalManager.showContent('<h1>Test</h1>');
            modalManager.showError('Error', vi.fn());
            modalManager.clearContent();
            
            expect(modalManager.reportContent.innerHTML).toBe('');
            expect(modalManager.errorMessage.textContent).toBe('');
            expect(modalManager.currentRetryCallback).toBe(null);
        });
    });
    
    describe('Event handling', () => {
        beforeEach(() => {
            modalManager.open('Test Agent');
        });
        
        test('should close modal on close button click', () => {
            modalManager.closeButton.click();
            expect(modalManager.isOpen()).toBe(false);
        });
        
        test('should close modal on background click', () => {
            modalManager.modal.click();
            expect(modalManager.isOpen()).toBe(false);
        });
        
        test('should not close modal on content click', () => {
            const modalContainer = modalManager.modal.querySelector('.modal-container');
            modalContainer.click();
            expect(modalManager.isOpen()).toBe(true);
        });
        
        test('should close modal on ESC key', () => {
            const escEvent = new KeyboardEvent('keydown', { key: 'Escape' });
            document.dispatchEvent(escEvent);
            expect(modalManager.isOpen()).toBe(false);
        });
        
        test('should not close modal on other keys', () => {
            const enterEvent = new KeyboardEvent('keydown', { key: 'Enter' });
            document.dispatchEvent(enterEvent);
            expect(modalManager.isOpen()).toBe(true);
        });
        
        test('should call retry callback on retry button click', () => {
            const retryCallback = vi.fn();
            modalManager.showError('Error', retryCallback);
            modalManager.retryButton.click();
            
            expect(retryCallback).toHaveBeenCalledTimes(1);
        });
    });
    
    describe('Utility methods', () => {
        test('should update title', () => {
            modalManager.updateTitle('New Title');
            expect(modalManager.modalTitle.textContent).toBe('New Title');
        });
        
        test('should correctly report loading state', () => {
            modalManager.showLoading();
            expect(modalManager.isLoading()).toBe(true);
            
            modalManager.showContent('<p>Content</p>');
            expect(modalManager.isLoading()).toBe(false);
        });
        
        test('should correctly report error state', () => {
            modalManager.showError('Error');
            expect(modalManager.isShowingError()).toBe(true);
            
            modalManager.showContent('<p>Content</p>');
            expect(modalManager.isShowingError()).toBe(false);
        });
        
        test('should correctly report content state', () => {
            modalManager.showContent('<p>Content</p>');
            expect(modalManager.isShowingContent()).toBe(true);
            
            modalManager.showLoading();
            expect(modalManager.isShowingContent()).toBe(false);
        });
    });
});