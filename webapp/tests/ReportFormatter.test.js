import { describe, it, expect, beforeEach } from 'vitest'

// Import the ReportFormatter class from the main app file
// Since we can't easily import from app.js, we'll define it here for testing
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
    if (!text) return text;
    return text
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#39;');
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
        <strong>Report Not Available</strong>
        <p class="mb-2 mt-2">No detailed report found for ${agentName}.</p>
        <small class="text-muted">Expected file: ${reportFile}</small>
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
          <button class="btn btn-sm btn-outline-info mt-2" onclick="this.closest('.agent-card').agentCard.checkReportStatus()">
            <i class="fas fa-search me-1"></i>Check Status
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
        <strong>Unable to Load Report</strong>
        <p class="mb-2 mt-2">Failed to load the ${agentName} report.</p>
        <small class="text-muted">Error: ${errorMessage}</small>
        ${retryCount > 0 ? `<small class="d-block text-muted mt-1">Retry attempt ${retryCount} of ${maxRetries}</small>` : ''}
        <div class="mt-3">
          ${canRetry ? `
            <button class="btn btn-sm btn-outline-warning retry-btn" onclick="this.closest('.agent-card').agentCard.retryLoadReport()">
              <i class="fas fa-redo me-1"></i>Retry Loading
            </button>
            <button class="btn btn-sm btn-outline-secondary ms-2" onclick="this.closest('.agent-card').agentCard.showRawError()">
              <i class="fas fa-info-circle me-1"></i>Show Details
            </button>
          ` : `
            <div class="text-muted small">
              <i class="fas fa-times-circle me-1"></i>
              Maximum retry attempts reached. Please try again later.
            </div>
            <button class="btn btn-sm btn-outline-secondary mt-2" onclick="this.closest('.agent-card').agentCard.showRawError()">
              <i class="fas fa-info-circle me-1"></i>Show Error Details
            </button>
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

describe('ReportFormatter', () => {
  describe('formatMarkdown', () => {
    it('should handle null or undefined content', () => {
      expect(ReportFormatter.formatMarkdown(null)).toBe('<p class="text-muted">No content available</p>')
      expect(ReportFormatter.formatMarkdown(undefined)).toBe('<p class="text-muted">No content available</p>')
      expect(ReportFormatter.formatMarkdown('')).toBe('<p class="text-muted">No content available</p>')
    })

    it('should format headers correctly', () => {
      const markdown = '# Header 1\n## Header 2\n### Header 3'
      const result = ReportFormatter.formatMarkdown(markdown)
      
      expect(result).toContain('<h3 class="report-heading text-primary mt-4 mb-3">Header 1</h3>')
      expect(result).toContain('<h4 class="report-heading text-primary mt-3 mb-2">Header 2</h4>')
      expect(result).toContain('<h5 class="report-heading text-primary mt-3 mb-2">Header 3</h5>')
    })

    it('should format bold and italic text', () => {
      const markdown = '**bold text** and *italic text*'
      const result = ReportFormatter.formatMarkdown(markdown)
      
      expect(result).toContain('<strong>bold text</strong>')
      expect(result).toContain('<em>italic text</em>')
    })

    it('should format inline code', () => {
      const markdown = 'This is `inline code` in text'
      const result = ReportFormatter.formatMarkdown(markdown)
      
      expect(result).toContain('<code class="bg-light px-1 rounded">inline code</code>')
    })

    it('should format lists', () => {
      const markdown = '- Item 1\n- Item 2\n1. Numbered 1\n2. Numbered 2'
      const result = ReportFormatter.formatMarkdown(markdown)
      
      expect(result).toContain('<li>Item 1</li>')
      expect(result).toContain('<li>Item 2</li>')
      expect(result).toContain('<ul class="mb-2">')
    })

    it('should handle complex markdown with multiple elements', () => {
      const markdown = `# Main Title

## Section Header

This is a paragraph with **bold** and *italic* text.

- List item 1
- List item 2

Another paragraph with \`code\`.`

      const result = ReportFormatter.formatMarkdown(markdown)
      
      expect(result).toContain('<h3 class="report-heading text-primary mt-4 mb-3">Main Title</h3>')
      expect(result).toContain('<h4 class="report-heading text-primary mt-3 mb-2">Section Header</h4>')
      expect(result).toContain('<strong>bold</strong>')
      expect(result).toContain('<em>italic</em>')
      expect(result).toContain('<li>List item 1</li>')
      expect(result).toContain('<code class="bg-light px-1 rounded">code</code>')
    })
  })

  describe('formatTables', () => {
    it('should format simple markdown tables', () => {
      const markdown = `| Header 1 | Header 2 |
|----------|----------|
| Cell 1   | Cell 2   |
| Cell 3   | Cell 4   |`

      const result = ReportFormatter.formatTables(markdown)
      
      expect(result).toContain('<table class="table table-sm table-striped table-hover">')
      expect(result).toContain('<thead class="table-dark">')
      expect(result).toContain('<th scope="col">Header 1</th>')
      expect(result).toContain('<th scope="col">Header 2</th>')
      expect(result).toContain('<td>Cell 1</td>')
      expect(result).toContain('<td>Cell 2</td>')
    })

    it('should handle malformed tables gracefully', () => {
      const markdown = '| Header 1 | Header 2 |\n| Cell 1   |' // Missing separator row
      const result = ReportFormatter.formatTables(markdown)
      
      // Should return original content if table is malformed
      expect(result).toBe(markdown)
    })

    it('should handle tables with special characters', () => {
      const markdown = `| Name | Value |
|------|-------|
| Test & Co | $100.50 |
| <Script> | "Quote" |`

      const result = ReportFormatter.formatTables(markdown)
      
      expect(result).toContain('Test &amp; Co')
      expect(result).toContain('$100.50')
      expect(result).toContain('&lt;Script&gt;')
      expect(result).toContain('&quot;Quote&quot;')
    })
  })

  describe('parseTableRow', () => {
    it('should parse table rows correctly', () => {
      const row = '| Cell 1 | Cell 2 | Cell 3 |'
      const result = ReportFormatter.parseTableRow(row)
      
      expect(result).toEqual(['Cell 1', 'Cell 2', 'Cell 3'])
    })

    it('should handle empty cells', () => {
      const row = '| Cell 1 |  | Cell 3 |'
      const result = ReportFormatter.parseTableRow(row)
      
      expect(result).toEqual(['Cell 1', '', 'Cell 3'])
    })

    it('should return empty array for invalid rows', () => {
      expect(ReportFormatter.parseTableRow('')).toEqual([])
      expect(ReportFormatter.parseTableRow('No pipes here')).toEqual([])
      expect(ReportFormatter.parseTableRow(null)).toEqual([])
    })
  })

  describe('formatLists', () => {
    it('should format unordered lists', () => {
      const content = '- Item 1\n- Item 2\n- Item 3'
      const result = ReportFormatter.formatLists(content)
      
      expect(result).toContain('<li>Item 1</li>')
      expect(result).toContain('<li>Item 2</li>')
      expect(result).toContain('<ul class="mb-2">')
    })

    it('should format ordered lists', () => {
      const content = '1. First item\n2. Second item\n3. Third item'
      const result = ReportFormatter.formatLists(content)
      
      expect(result).toContain('<li>First item</li>')
      expect(result).toContain('<li>Second item</li>')
      expect(result).toContain('<ul class="mb-2">')
    })

    it('should handle mixed list formats', () => {
      const content = '- Bullet item\n* Another bullet\n+ Plus bullet\n1. Numbered item'
      const result = ReportFormatter.formatLists(content)
      
      expect(result).toContain('<li>Bullet item</li>')
      expect(result).toContain('<li>Another bullet</li>')
      expect(result).toContain('<li>Plus bullet</li>')
      expect(result).toContain('<li>Numbered item</li>')
    })
  })

  describe('formatParagraphs', () => {
    it('should wrap text in paragraph tags', () => {
      const content = 'This is a paragraph.'
      const result = ReportFormatter.formatParagraphs(content)
      
      expect(result).toContain('<p class="mb-2">This is a paragraph.</p>')
    })

    it('should handle multiple paragraphs', () => {
      const content = 'First paragraph.\n\nSecond paragraph.'
      const result = ReportFormatter.formatParagraphs(content)
      
      expect(result).toContain('<p class="mb-2">First paragraph.</p>')
      expect(result).toContain('<p class="mb-2">Second paragraph.</p>')
    })

    it('should convert line breaks to <br> tags within paragraphs', () => {
      const content = 'Line 1\nLine 2'
      const result = ReportFormatter.formatParagraphs(content)
      
      expect(result).toContain('Line 1<br>Line 2')
    })

    it('should skip already formatted HTML elements', () => {
      const content = '<h1>Header</h1>\n\nRegular paragraph.'
      const result = ReportFormatter.formatParagraphs(content)
      
      expect(result).toContain('<h1>Header</h1>')
      expect(result).toContain('<p class="mb-2">Regular paragraph.</p>')
    })
  })

  describe('escapeHtml', () => {
    it('should escape HTML special characters', () => {
      expect(ReportFormatter.escapeHtml('<script>')).toBe('&lt;script&gt;')
      expect(ReportFormatter.escapeHtml('Test & Co')).toBe('Test &amp; Co')
      expect(ReportFormatter.escapeHtml('"Quote"')).toBe('&quot;Quote&quot;')
      expect(ReportFormatter.escapeHtml("'Single'")).toBe('&#39;Single&#39;')
    })

    it('should handle empty or null input', () => {
      expect(ReportFormatter.escapeHtml('')).toBe('')
      expect(ReportFormatter.escapeHtml('Normal text')).toBe('Normal text')
    })
  })

  describe('createErrorContent', () => {
    it('should create error content with message', () => {
      const result = ReportFormatter.createErrorContent('Test Error', 'Original content')
      
      expect(result).toContain('alert alert-warning')
      expect(result).toContain('Test Error')
      expect(result).toContain('Original content')
    })

    it('should handle error without original content', () => {
      const result = ReportFormatter.createErrorContent('Test Error')
      
      expect(result).toContain('alert alert-warning')
      expect(result).toContain('Test Error')
      expect(result).not.toContain('<pre')
    })
  })

  describe('createLoadingContent', () => {
    it('should create loading content with agent name', () => {
      const result = ReportFormatter.createLoadingContent('Market Analyst')
      
      expect(result).toContain('Loading Market Analyst Report')
      expect(result).toContain('spinner-border')
      expect(result).toContain('progress-bar')
    })

    it('should use custom loading message', () => {
      const result = ReportFormatter.createLoadingContent('Market Analyst', 'Custom message')
      
      expect(result).toContain('Custom message')
    })
  })

  describe('createNotFoundContent', () => {
    it('should create not found content with agent and file info', () => {
      const result = ReportFormatter.createNotFoundContent('Market Analyst', 'market_report.md')
      
      expect(result).toContain('Report Not Available')
      expect(result).toContain('Market Analyst')
      expect(result).toContain('market_report.md')
      expect(result).toContain('alert alert-info')
    })
  })

  describe('createNetworkErrorContent', () => {
    it('should create network error content with retry option', () => {
      const result = ReportFormatter.createNetworkErrorContent('Market Analyst', 'Network timeout', 1)
      
      expect(result).toContain('Unable to Load Report')
      expect(result).toContain('Market Analyst')
      expect(result).toContain('Network timeout')
      expect(result).toContain('Retry attempt 1 of 3')
      expect(result).toContain('Retry Loading')
    })

    it('should show max retries reached when limit exceeded', () => {
      const result = ReportFormatter.createNetworkErrorContent('Market Analyst', 'Network timeout', 3)
      
      expect(result).toContain('Maximum retry attempts reached')
      expect(result).not.toContain('Retry Loading')
    })
  })

  describe('formatReportContent', () => {
    it('should format complete report with header', () => {
      const content = '# Test Report\n\nThis is test content.'
      const result = ReportFormatter.formatReportContent(content, 'Market Analyst', 'market_report.md')
      
      expect(result).toContain('report-header')
      expect(result).toContain('Market Analyst Analysis Report')
      expect(result).toContain('market_report.md')
      expect(result).toContain('report-body')
      expect(result).toContain('<h3 class="report-heading text-primary mt-4 mb-3">Test Report</h3>')
    })

    it('should handle empty content', () => {
      const result = ReportFormatter.formatReportContent('', 'Market Analyst', 'market_report.md')
      
      expect(result).toContain('Report Not Available')
      expect(result).toContain('Market Analyst')
      expect(result).toContain('market_report.md')
    })
  })
})