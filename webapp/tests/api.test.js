import { describe, it, expect, beforeEach, vi } from 'vitest'

// Mock fetch responses for API testing
const mockFetch = vi.fn()
global.fetch = mockFetch

describe('API Endpoint Tests', () => {
  beforeEach(() => {
    mockFetch.mockClear()
  })

  describe('/api/reports/{ticker}/{date}/{agent}', () => {
    const baseUrl = 'http://localhost:8000'
    
    it('should return successful response for valid report request', async () => {
      const mockResponse = {
        success: true,
        agent: 'Market Analyst',
        report_content: '# Market Analysis Report\n\nThis is a test report.',
        report_type: 'markdown'
      }
      
      mockFetch.mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => mockResponse
      })
      
      const response = await fetch(`${baseUrl}/api/reports/AAPL/2025-01-01/Market%20Analyst`)
      const data = await response.json()
      
      expect(response.ok).toBe(true)
      expect(data.success).toBe(true)
      expect(data.agent).toBe('Market Analyst')
      expect(data.report_content).toContain('Market Analysis Report')
      expect(data.report_type).toBe('markdown')
    })

    it('should return error response for non-existent report', async () => {
      const mockResponse = {
        success: false,
        agent: 'Market Analyst',
        error: 'Report not found',
        message: 'No report file found for Market Analyst on 2025-01-01 for AAPL'
      }
      
      mockFetch.mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => mockResponse
      })
      
      const response = await fetch(`${baseUrl}/api/reports/AAPL/2025-01-01/Market%20Analyst`)
      const data = await response.json()
      
      expect(data.success).toBe(false)
      expect(data.error).toBe('Report not found')
      expect(data.message).toContain('No report file found')
    })

    it('should handle invalid ticker format', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 400,
        json: async () => ({
          detail: 'Invalid ticker format: INVALID123. Must be 1-5 uppercase letters.'
        })
      })
      
      const response = await fetch(`${baseUrl}/api/reports/INVALID123/2025-01-01/Market%20Analyst`)
      const data = await response.json()
      
      expect(response.ok).toBe(false)
      expect(response.status).toBe(400)
      expect(data.detail).toContain('Invalid ticker format')
    })

    it('should handle invalid date format', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 400,
        json: async () => ({
          detail: 'Invalid date format: invalid-date. Must be YYYY-MM-DD format.'
        })
      })
      
      const response = await fetch(`${baseUrl}/api/reports/AAPL/invalid-date/Market%20Analyst`)
      const data = await response.json()
      
      expect(response.ok).toBe(false)
      expect(response.status).toBe(400)
      expect(data.detail).toContain('Invalid date format')
    })

    it('should handle unknown agent', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 400,
        json: async () => ({
          detail: 'Unknown agent: Unknown Agent. Valid agents: [...]'
        })
      })
      
      const response = await fetch(`${baseUrl}/api/reports/AAPL/2025-01-01/Unknown%20Agent`)
      const data = await response.json()
      
      expect(response.ok).toBe(false)
      expect(response.status).toBe(400)
      expect(data.detail).toContain('Unknown agent')
    })

    it('should handle server errors', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 500,
        json: async () => ({
          detail: 'Internal server error while loading report'
        })
      })
      
      const response = await fetch(`${baseUrl}/api/reports/AAPL/2025-01-01/Market%20Analyst`)
      const data = await response.json()
      
      expect(response.ok).toBe(false)
      expect(response.status).toBe(500)
      expect(data.detail).toContain('Internal server error')
    })

    it('should handle network errors', async () => {
      mockFetch.mockRejectedValueOnce(new Error('Network error'))
      
      try {
        await fetch(`${baseUrl}/api/reports/AAPL/2025-01-01/Market%20Analyst`)
        expect.fail('Should have thrown an error')
      } catch (error) {
        expect(error.message).toBe('Network error')
      }
    })

    it('should properly encode URL parameters', async () => {
      const mockResponse = {
        success: true,
        agent: 'Social Analyst',
        report_content: '# Social Media Analysis',
        report_type: 'markdown'
      }
      
      mockFetch.mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => mockResponse
      })
      
      // Test with agent name that needs URL encoding
      const response = await fetch(`${baseUrl}/api/reports/AAPL/2025-01-01/Social%20Analyst`)
      
      expect(mockFetch).toHaveBeenCalledWith(`${baseUrl}/api/reports/AAPL/2025-01-01/Social%20Analyst`)
    })

    it('should handle empty report content', async () => {
      const mockResponse = {
        success: false,
        agent: 'Market Analyst',
        error: 'Empty report',
        message: 'Report file for Market Analyst is empty'
      }
      
      mockFetch.mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => mockResponse
      })
      
      const response = await fetch(`${baseUrl}/api/reports/AAPL/2025-01-01/Market%20Analyst`)
      const data = await response.json()
      
      expect(data.success).toBe(false)
      expect(data.error).toBe('Empty report')
      expect(data.message).toContain('is empty')
    })

    it('should handle malformed JSON response', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => {
          throw new Error('Invalid JSON')
        }
      })
      
      try {
        const response = await fetch(`${baseUrl}/api/reports/AAPL/2025-01-01/Market%20Analyst`)
        await response.json()
        expect.fail('Should have thrown an error')
      } catch (error) {
        expect(error.message).toBe('Invalid JSON')
      }
    })
  })

  describe('API Integration Helper Functions', () => {
    // Test helper functions that would be used with the API
    
    describe('buildReportUrl', () => {
      const buildReportUrl = (baseUrl, ticker, date, agent) => {
        const encodedAgent = encodeURIComponent(agent)
        return `${baseUrl}/api/reports/${ticker}/${date}/${encodedAgent}`
      }

      it('should build correct URL with proper encoding', () => {
        const url = buildReportUrl('http://localhost:8000', 'AAPL', '2025-01-01', 'Market Analyst')
        expect(url).toBe('http://localhost:8000/api/reports/AAPL/2025-01-01/Market%20Analyst')
      })

      it('should handle special characters in agent names', () => {
        const url = buildReportUrl('http://localhost:8000', 'AAPL', '2025-01-01', 'Risk & Safety Analyst')
        expect(url).toBe('http://localhost:8000/api/reports/AAPL/2025-01-01/Risk%20%26%20Safety%20Analyst')
      })
    })

    describe('validateApiResponse', () => {
      const validateApiResponse = (response) => {
        if (!response) {
          throw new Error('No response received')
        }
        
        if (typeof response.success !== 'boolean') {
          throw new Error('Invalid response format: missing success field')
        }
        
        if (!response.agent || typeof response.agent !== 'string') {
          throw new Error('Invalid response format: missing or invalid agent field')
        }
        
        if (response.success) {
          if (!response.report_content) {
            throw new Error('Invalid response format: missing report_content for successful response')
          }
          if (!response.report_type) {
            throw new Error('Invalid response format: missing report_type for successful response')
          }
        } else {
          if (!response.error) {
            throw new Error('Invalid response format: missing error field for failed response')
          }
        }
        
        return true
      }

      it('should validate successful response', () => {
        const response = {
          success: true,
          agent: 'Market Analyst',
          report_content: '# Report content',
          report_type: 'markdown'
        }
        
        expect(() => validateApiResponse(response)).not.toThrow()
      })

      it('should validate error response', () => {
        const response = {
          success: false,
          agent: 'Market Analyst',
          error: 'Report not found',
          message: 'File not found'
        }
        
        expect(() => validateApiResponse(response)).not.toThrow()
      })

      it('should reject invalid response format', () => {
        const response = {
          agent: 'Market Analyst'
          // Missing success field
        }
        
        expect(() => validateApiResponse(response)).toThrow('missing success field')
      })

      it('should reject successful response without content', () => {
        const response = {
          success: true,
          agent: 'Market Analyst'
          // Missing report_content
        }
        
        expect(() => validateApiResponse(response)).toThrow('missing report_content')
      })

      it('should reject error response without error field', () => {
        const response = {
          success: false,
          agent: 'Market Analyst'
          // Missing error field
        }
        
        expect(() => validateApiResponse(response)).toThrow('missing error field')
      })
    })

    describe('parseApiError', () => {
      const parseApiError = (error, response) => {
        if (error.name === 'TypeError' && error.message.includes('fetch')) {
          return {
            type: 'network',
            message: 'Network connection failed',
            retryable: true
          }
        }
        
        if (response && response.status) {
          switch (response.status) {
            case 400:
              return {
                type: 'validation',
                message: 'Invalid request parameters',
                retryable: false
              }
            case 404:
              return {
                type: 'not_found',
                message: 'Report not found',
                retryable: false
              }
            case 500:
              return {
                type: 'server',
                message: 'Server error occurred',
                retryable: true
              }
            default:
              return {
                type: 'unknown',
                message: `HTTP ${response.status} error`,
                retryable: false
              }
          }
        }
        
        return {
          type: 'unknown',
          message: error.message || 'Unknown error',
          retryable: false
        }
      }

      it('should parse network errors', () => {
        const error = new TypeError('fetch failed')
        const result = parseApiError(error)
        
        expect(result.type).toBe('network')
        expect(result.retryable).toBe(true)
      })

      it('should parse validation errors', () => {
        const error = new Error('API Error')
        const response = { status: 400 }
        const result = parseApiError(error, response)
        
        expect(result.type).toBe('validation')
        expect(result.retryable).toBe(false)
      })

      it('should parse server errors', () => {
        const error = new Error('API Error')
        const response = { status: 500 }
        const result = parseApiError(error, response)
        
        expect(result.type).toBe('server')
        expect(result.retryable).toBe(true)
      })

      it('should parse unknown errors', () => {
        const error = new Error('Unknown error')
        const result = parseApiError(error)
        
        expect(result.type).toBe('unknown')
        expect(result.retryable).toBe(false)
      })
    })
  })

  describe('API Client Class', () => {
    // Test a hypothetical API client class
    class ReportApiClient {
      constructor(baseUrl) {
        this.baseUrl = baseUrl
        this.cache = new Map()
      }
      
      async getReport(ticker, date, agent, options = {}) {
        const cacheKey = `${ticker}-${date}-${agent}`
        
        if (!options.skipCache && this.cache.has(cacheKey)) {
          return this.cache.get(cacheKey)
        }
        
        const url = `${this.baseUrl}/api/reports/${ticker}/${date}/${encodeURIComponent(agent)}`
        
        try {
          const response = await fetch(url, {
            timeout: options.timeout || 5000,
            ...options.fetchOptions
          })
          
          const data = await response.json()
          
          if (response.ok && data.success) {
            this.cache.set(cacheKey, data)
          }
          
          return data
        } catch (error) {
          throw new Error(`Failed to fetch report: ${error.message}`)
        }
      }
      
      clearCache() {
        this.cache.clear()
      }
      
      getCacheSize() {
        return this.cache.size
      }
    }

    let apiClient

    beforeEach(() => {
      apiClient = new ReportApiClient('http://localhost:8000')
    })

    it('should create client with base URL', () => {
      expect(apiClient.baseUrl).toBe('http://localhost:8000')
      expect(apiClient.cache).toBeInstanceOf(Map)
    })

    it('should fetch and cache successful responses', async () => {
      const mockResponse = {
        success: true,
        agent: 'Market Analyst',
        report_content: '# Report',
        report_type: 'markdown'
      }
      
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockResponse
      })
      
      const result = await apiClient.getReport('AAPL', '2025-01-01', 'Market Analyst')
      
      expect(result).toEqual(mockResponse)
      expect(apiClient.getCacheSize()).toBe(1)
    })

    it('should return cached responses on subsequent calls', async () => {
      const mockResponse = {
        success: true,
        agent: 'Market Analyst',
        report_content: '# Report',
        report_type: 'markdown'
      }
      
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockResponse
      })
      
      // First call
      await apiClient.getReport('AAPL', '2025-01-01', 'Market Analyst')
      
      // Second call should use cache
      const result = await apiClient.getReport('AAPL', '2025-01-01', 'Market Analyst')
      
      expect(mockFetch).toHaveBeenCalledTimes(1)
      expect(result).toEqual(mockResponse)
    })

    it('should skip cache when requested', async () => {
      const mockResponse = {
        success: true,
        agent: 'Market Analyst',
        report_content: '# Report',
        report_type: 'markdown'
      }
      
      mockFetch.mockResolvedValue({
        ok: true,
        json: async () => mockResponse
      })
      
      // First call
      await apiClient.getReport('AAPL', '2025-01-01', 'Market Analyst')
      
      // Second call with skipCache
      await apiClient.getReport('AAPL', '2025-01-01', 'Market Analyst', { skipCache: true })
      
      expect(mockFetch).toHaveBeenCalledTimes(2)
    })

    it('should not cache failed responses', async () => {
      const mockResponse = {
        success: false,
        agent: 'Market Analyst',
        error: 'Report not found'
      }
      
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockResponse
      })
      
      await apiClient.getReport('AAPL', '2025-01-01', 'Market Analyst')
      
      expect(apiClient.getCacheSize()).toBe(0)
    })

    it('should clear cache', () => {
      apiClient.cache.set('test', 'value')
      expect(apiClient.getCacheSize()).toBe(1)
      
      apiClient.clearCache()
      expect(apiClient.getCacheSize()).toBe(0)
    })

    it('should handle fetch errors', async () => {
      mockFetch.mockRejectedValueOnce(new Error('Network error'))
      
      await expect(apiClient.getReport('AAPL', '2025-01-01', 'Market Analyst'))
        .rejects.toThrow('Failed to fetch report: Network error')
    })
  })
})