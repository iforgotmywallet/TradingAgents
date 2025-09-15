import { describe, it, expect, beforeEach, vi } from 'vitest'

// Simplified AgentCard class for modal-based testing
class AgentCard {
  constructor(agentName, teamName, element) {
    this.agentName = agentName
    this.teamName = teamName
    this.element = element
    this.status = 'pending'
    
    this.initializeElement()
    this.setupEventListeners()
  }
  
  initializeElement() {
    if (this.element) {
      this.element.setAttribute('data-agent', this.agentName)
      this.element.setAttribute('data-status', this.status)
      this.element.className = `agent-card mb-2 agent-card-${this.status}`
    }
  }
  
  setupEventListeners() {
    if (!this.element) return
    
    const cardHeader = this.element.querySelector('.card-header')
    if (cardHeader) {
      cardHeader.addEventListener('click', (e) => {
        e.preventDefault()
        e.stopPropagation()
        
        // Modal functionality will be handled by AgentCardManager
        if (this.status === 'completed') {
          // Trigger modal opening event
          this.element.dispatchEvent(new CustomEvent('openModal', {
            detail: { agentName: this.agentName }
          }))
        }
      })
    }
  }
  
  updateStatus(newStatus) {
    if (this.status === newStatus) return
    
    this.status = newStatus
    this.updateUI()
  }
  
  updateUI() {
    if (!this.element) return
    
    this.element.setAttribute('data-status', this.status)
    this.element.className = `agent-card mb-2 agent-card-${this.status}`
    
    const badge = this.element.querySelector('.status-badge')
    if (badge) {
      badge.className = `status-badge status-${this.status} ms-2`
      badge.textContent = this.getStatusText()
    }
    
    this.updateClickability()
    this.updateLoadingIndicator()
  }
  
  updateClickability() {
    const cardHeader = this.element?.querySelector('.card-header')
    
    if (this.status === 'completed') {
      if (cardHeader) {
        cardHeader.style.cursor = 'pointer'
        cardHeader.title = 'Click to view report'
        this.element.classList.add('clickable')
      }
    } else {
      if (cardHeader) {
        cardHeader.style.cursor = 'default'
        cardHeader.title = ''
        this.element.classList.remove('clickable')
      }
    }
  }
  
  updateLoadingIndicator() {
    const cardHeader = this.element.querySelector('.card-header')
    const existingSpinner = cardHeader?.querySelector('.loading-spinner')
    
    if (this.status === 'in_progress') {
      if (!existingSpinner && cardHeader) {
        const spinner = document.createElement('div')
        spinner.className = 'loading-spinner ms-2'
        const agentInfo = cardHeader.querySelector('.agent-info')
        if (agentInfo) {
          agentInfo.appendChild(spinner)
        }
      }
    } else {
      if (existingSpinner) {
        existingSpinner.remove()
      }
    }
  }
  
  getStatusText() {
    switch (this.status) {
      case 'pending': return 'PENDING'
      case 'in_progress': return 'IN PROGRESS'
      case 'completed': return 'COMPLETED'
      case 'error': return 'ERROR'
      default: return this.status.toUpperCase()
    }
  }
}

// Mock DOM element creation helper
function createMockElement(tagName, options = {}) {
  const mockCardHeader = {
    style: {},
    title: '',
    setAttribute: vi.fn(),
    getAttribute: vi.fn(),
    removeAttribute: vi.fn(),
    hasAttribute: vi.fn(),
    addEventListener: vi.fn(),
    click: vi.fn(),
    querySelector: vi.fn((sel) => {
      if (sel === '.agent-info') {
        return {
          appendChild: vi.fn()
        }
      }
      if (sel === '.loading-spinner') {
        return null // Initially no spinner
      }
      return null
    })
  }

  const mockStatusBadge = {
    className: '',
    textContent: ''
  }

  const element = {
    tagName: tagName.toUpperCase(),
    className: options.className || '',
    innerHTML: options.innerHTML || '',
    style: {},
    classList: {
      add: vi.fn(function(className) { 
        if (!this.contains(className)) {
          this._classes = this._classes || []
          this._classes.push(className)
        }
      }),
      remove: vi.fn(function(className) {
        this._classes = (this._classes || []).filter(c => c !== className)
      }),
      contains: vi.fn(function(className) {
        return (this._classes || []).includes(className)
      }),
      toggle: vi.fn(function(className, force) {
        if (force !== undefined) {
          if (force) this.add(className)
          else this.remove(className)
        } else {
          if (this.contains(className)) this.remove(className)
          else this.add(className)
        }
      }),
      _classes: []
    },
    setAttribute: vi.fn(),
    getAttribute: vi.fn(),
    removeAttribute: vi.fn(),
    hasAttribute: vi.fn(),
    querySelector: vi.fn(),
    querySelectorAll: vi.fn(),
    addEventListener: vi.fn(),
    removeEventListener: vi.fn(),
    dispatchEvent: vi.fn(),
    appendChild: vi.fn(),
    removeChild: vi.fn(),
    remove: vi.fn()
  }
  
  // Mock querySelector to return mock child elements
  element.querySelector.mockImplementation((selector) => {
    if (selector === '.card-header') {
      return mockCardHeader
    }
    if (selector === '.status-badge') {
      return mockStatusBadge
    }
    if (selector === '.loading-spinner') {
      return null // Initially no spinner
    }
    return null
  })
  
  return element
}

describe('AgentCard', () => {
  let mockElement
  let agentCard
  
  beforeEach(() => {
    // Create mock DOM element with simplified structure for modal approach
    mockElement = createMockElement('div', {
      className: 'agent-card',
      innerHTML: `
        <div class="card-header">
          <div class="agent-info">
            <span class="agent-name">Test Agent</span>
            <span class="status-badge">PENDING</span>
          </div>
        </div>
      `
    })
    
    agentCard = new AgentCard('Market Analyst', 'Analyst Team', mockElement)
  })

  describe('constructor', () => {
    it('should initialize with correct default values', () => {
      expect(agentCard.agentName).toBe('Market Analyst')
      expect(agentCard.teamName).toBe('Analyst Team')
      expect(agentCard.status).toBe('pending')
    })

    it('should initialize element attributes', () => {
      expect(mockElement.setAttribute).toHaveBeenCalledWith('data-agent', 'Market Analyst')
      expect(mockElement.setAttribute).toHaveBeenCalledWith('data-status', 'pending')
      expect(mockElement.className).toContain('agent-card-pending')
    })

    it('should handle null element gracefully', () => {
      const cardWithoutElement = new AgentCard('Test Agent', 'Test Team', null)
      expect(cardWithoutElement.element).toBe(null)
      expect(cardWithoutElement.agentName).toBe('Test Agent')
    })
  })

  describe('updateStatus', () => {
    it('should update status and UI', () => {
      agentCard.updateStatus('in_progress')
      
      expect(agentCard.status).toBe('in_progress')
      expect(mockElement.setAttribute).toHaveBeenCalledWith('data-status', 'in_progress')
      expect(mockElement.className).toContain('agent-card-in_progress')
    })

    it('should not update if status is the same', () => {
      const initialSetAttributeCalls = mockElement.setAttribute.mock.calls.length
      agentCard.updateStatus('pending')
      
      // Should not have made additional setAttribute calls
      expect(mockElement.setAttribute.mock.calls.length).toBe(initialSetAttributeCalls)
    })

    it('should enable clickability when status becomes completed', () => {
      const mockCardHeader = mockElement.querySelector('.card-header')
      
      agentCard.updateStatus('completed')
      
      expect(mockCardHeader.style.cursor).toBe('pointer')
      expect(mockCardHeader.title).toBe('Click to view report')
      expect(mockElement.classList.add).toHaveBeenCalledWith('clickable')
    })

    it('should disable clickability for non-completed status', () => {
      const mockCardHeader = mockElement.querySelector('.card-header')
      
      // First set to completed
      agentCard.updateStatus('completed')
      
      // Then change to error
      agentCard.updateStatus('error')
      
      expect(mockCardHeader.style.cursor).toBe('default')
      expect(mockCardHeader.title).toBe('')
      expect(mockElement.classList.remove).toHaveBeenCalledWith('clickable')
    })
  })

  describe('getStatusText', () => {
    it('should return correct status text for all statuses', () => {
      expect(agentCard.getStatusText()).toBe('PENDING')
      
      agentCard.status = 'in_progress'
      expect(agentCard.getStatusText()).toBe('IN PROGRESS')
      
      agentCard.status = 'completed'
      expect(agentCard.getStatusText()).toBe('COMPLETED')
      
      agentCard.status = 'error'
      expect(agentCard.getStatusText()).toBe('ERROR')
      
      agentCard.status = 'custom'
      expect(agentCard.getStatusText()).toBe('CUSTOM')
    })
  })

  describe('updateClickability', () => {
    it('should make completed cards clickable', () => {
      const mockCardHeader = mockElement.querySelector('.card-header')
      agentCard.status = 'completed'
      
      agentCard.updateClickability()
      
      expect(mockCardHeader.style.cursor).toBe('pointer')
      expect(mockCardHeader.title).toBe('Click to view report')
      expect(mockElement.classList.add).toHaveBeenCalledWith('clickable')
    })

    it('should make non-completed cards non-clickable', () => {
      const mockCardHeader = mockElement.querySelector('.card-header')
      agentCard.status = 'pending'
      
      agentCard.updateClickability()
      
      expect(mockCardHeader.style.cursor).toBe('default')
      expect(mockCardHeader.title).toBe('')
      expect(mockElement.classList.remove).toHaveBeenCalledWith('clickable')
    })
  })

  describe('updateLoadingIndicator', () => {
    it('should add loading spinner for in_progress status', () => {
      const mockCardHeader = mockElement.querySelector('.card-header')
      const mockAgentInfo = mockCardHeader.querySelector('.agent-info')
      
      // Ensure no existing spinner
      mockCardHeader.querySelector.mockImplementation((selector) => {
        if (selector === '.loading-spinner') return null // No existing spinner
        if (selector === '.agent-info') return mockAgentInfo
        return null
      })
      
      agentCard.status = 'in_progress'
      agentCard.updateLoadingIndicator()
      
      expect(mockAgentInfo.appendChild).toHaveBeenCalled()
    })

    it('should remove loading spinner for non-in_progress status', () => {
      // Mock existing spinner
      const mockSpinner = { remove: vi.fn() }
      const mockCardHeader = mockElement.querySelector('.card-header')
      
      // Update the mock to return the spinner when queried
      mockCardHeader.querySelector.mockImplementation((selector) => {
        if (selector === '.loading-spinner') return mockSpinner
        if (selector === '.agent-info') return { appendChild: vi.fn() }
        return null
      })
      
      agentCard.status = 'completed'
      agentCard.updateLoadingIndicator()
      
      expect(mockSpinner.remove).toHaveBeenCalled()
    })
  })

  describe('event listeners', () => {
    it('should dispatch openModal event on card header click when completed', () => {
      agentCard.status = 'completed'
      const mockCardHeader = mockElement.querySelector('.card-header')
      
      // Get the click handler that was registered during construction
      const addEventListenerCalls = mockCardHeader.addEventListener.mock.calls
      const clickCall = addEventListenerCalls.find(call => call[0] === 'click')
      expect(clickCall).toBeDefined()
      
      const clickHandler = clickCall[1]
      
      const mockEvent = {
        preventDefault: vi.fn(),
        stopPropagation: vi.fn()
      }
      
      clickHandler(mockEvent)
      
      expect(mockEvent.preventDefault).toHaveBeenCalled()
      expect(mockEvent.stopPropagation).toHaveBeenCalled()
      expect(mockElement.dispatchEvent).toHaveBeenCalledWith(
        expect.objectContaining({
          detail: { agentName: 'Market Analyst' }
        })
      )
    })

    it('should not dispatch openModal event when not completed', () => {
      agentCard.status = 'pending'
      const mockCardHeader = mockElement.querySelector('.card-header')
      
      // Get the click handler that was registered during construction
      const addEventListenerCalls = mockCardHeader.addEventListener.mock.calls
      const clickCall = addEventListenerCalls.find(call => call[0] === 'click')
      expect(clickCall).toBeDefined()
      
      const clickHandler = clickCall[1]
      
      const mockEvent = {
        preventDefault: vi.fn(),
        stopPropagation: vi.fn()
      }
      
      clickHandler(mockEvent)
      
      expect(mockEvent.preventDefault).toHaveBeenCalled()
      expect(mockEvent.stopPropagation).toHaveBeenCalled()
      expect(mockElement.dispatchEvent).not.toHaveBeenCalled()
    })
  })
})