// Test setup file
import { vi } from 'vitest'

// Mock fetch globally
global.fetch = vi.fn()

// Mock DOM APIs that might not be available in jsdom
Object.defineProperty(window, 'scrollTo', {
  value: vi.fn(),
  writable: true
})

// Mock console methods to avoid noise in tests
global.console = {
  ...console,
  log: vi.fn(),
  warn: vi.fn(),
  error: vi.fn()
}

// Setup DOM helpers
global.createMockElement = (tag, attributes = {}) => {
  const element = document.createElement(tag)
  Object.entries(attributes).forEach(([key, value]) => {
    if (key === 'className') {
      element.className = value
    } else if (key === 'innerHTML') {
      element.innerHTML = value
    } else {
      element.setAttribute(key, value)
    }
  })
  return element
}

// Mock agent report mapping for tests
global.AGENT_REPORT_MAPPING = {
  'Market Analyst': 'market_report.md',
  'Social Analyst': 'sentiment_report.md', 
  'News Analyst': 'news_report.md',
  'Fundamentals Analyst': 'fundamentals_report.md',
  'Bull Researcher': 'investment_plan.md',
  'Bear Researcher': 'investment_plan.md',
  'Research Manager': 'investment_plan.md',
  'Trader': 'trader_investment_plan.md',
  'Risky Analyst': 'final_trade_decision.md',
  'Neutral Analyst': 'final_trade_decision.md', 
  'Safe Analyst': 'final_trade_decision.md',
  'Portfolio Manager': 'final_trade_decision.md'
}

// Reset all mocks before each test
beforeEach(() => {
  vi.clearAllMocks()
  fetch.mockClear()
  document.body.innerHTML = ''
})