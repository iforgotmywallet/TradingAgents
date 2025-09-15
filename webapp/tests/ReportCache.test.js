/**
 * @vitest-environment jsdom
 * Tests for ReportCache functionality
 */
import { describe, test, expect, beforeEach, vi } from 'vitest';

// ReportCache class implementation for testing
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
    
    getContext() {
        return {
            ticker: this.currentTicker,
            date: this.currentDate
        };
    }
    
    getStats() {
        return {
            size: this.cache.size,
            ticker: this.currentTicker,
            date: this.currentDate,
            keys: Array.from(this.cache.keys())
        };
    }
    
    delete(agentKey) {
        return this.cache.delete(agentKey);
    }
}

describe('ReportCache', () => {
    let reportCache;
    
    beforeEach(() => {
        reportCache = new ReportCache();
    });
    
    describe('Initialization', () => {
        test('should initialize with empty cache and null context', () => {
            expect(reportCache.cache.size).toBe(0);
            expect(reportCache.currentTicker).toBe(null);
            expect(reportCache.currentDate).toBe(null);
        });
        
        test('should return empty context initially', () => {
            const context = reportCache.getContext();
            expect(context.ticker).toBe(null);
            expect(context.date).toBe(null);
        });
        
        test('should return empty stats initially', () => {
            const stats = reportCache.getStats();
            expect(stats.size).toBe(0);
            expect(stats.ticker).toBe(null);
            expect(stats.date).toBe(null);
            expect(stats.keys).toEqual([]);
        });
    });
    
    describe('Context Management', () => {
        test('should set context without clearing cache on first call', () => {
            // Set context first, then add content
            reportCache.setContext('AAPL', '2025-09-14');
            reportCache.set('market', 'test content');
            
            expect(reportCache.currentTicker).toBe('AAPL');
            expect(reportCache.currentDate).toBe('2025-09-14');
            expect(reportCache.cache.size).toBe(1);
        });
        
        test('should clear cache when ticker changes', () => {
            reportCache.setContext('AAPL', '2025-09-14');
            reportCache.set('market', 'test content');
            
            expect(reportCache.cache.size).toBe(1);
            
            reportCache.setContext('TSLA', '2025-09-14');
            
            expect(reportCache.currentTicker).toBe('TSLA');
            expect(reportCache.cache.size).toBe(0);
        });
        
        test('should clear cache when date changes', () => {
            reportCache.setContext('AAPL', '2025-09-14');
            reportCache.set('market', 'test content');
            
            expect(reportCache.cache.size).toBe(1);
            
            reportCache.setContext('AAPL', '2025-09-15');
            
            expect(reportCache.currentDate).toBe('2025-09-15');
            expect(reportCache.cache.size).toBe(0);
        });
        
        test('should not clear cache when context remains the same', () => {
            reportCache.setContext('AAPL', '2025-09-14');
            reportCache.set('market', 'test content');
            
            expect(reportCache.cache.size).toBe(1);
            
            reportCache.setContext('AAPL', '2025-09-14');
            
            expect(reportCache.cache.size).toBe(1);
            expect(reportCache.get('market')).toBe('test content');
        });
        
        test('should clear cache when both ticker and date change', () => {
            reportCache.setContext('AAPL', '2025-09-14');
            reportCache.set('market', 'test content');
            reportCache.set('news', 'news content');
            
            expect(reportCache.cache.size).toBe(2);
            
            reportCache.setContext('TSLA', '2025-09-15');
            
            expect(reportCache.currentTicker).toBe('TSLA');
            expect(reportCache.currentDate).toBe('2025-09-15');
            expect(reportCache.cache.size).toBe(0);
        });
    });
    
    describe('Cache Operations', () => {
        beforeEach(() => {
            reportCache.setContext('AAPL', '2025-09-14');
        });
        
        test('should store and retrieve content', () => {
            const content = '<h1>Market Analysis</h1><p>Content here</p>';
            reportCache.set('market', content);
            
            expect(reportCache.get('market')).toBe(content);
            expect(reportCache.has('market')).toBe(true);
        });
        
        test('should return undefined for non-existent keys', () => {
            expect(reportCache.get('nonexistent')).toBe(undefined);
            expect(reportCache.has('nonexistent')).toBe(false);
        });
        
        test('should handle multiple agent reports', () => {
            reportCache.set('market', 'Market analysis content');
            reportCache.set('news', 'News analysis content');
            reportCache.set('fundamentals', 'Fundamentals analysis content');
            
            expect(reportCache.cache.size).toBe(3);
            expect(reportCache.get('market')).toBe('Market analysis content');
            expect(reportCache.get('news')).toBe('News analysis content');
            expect(reportCache.get('fundamentals')).toBe('Fundamentals analysis content');
        });
        
        test('should delete specific entries', () => {
            reportCache.set('market', 'content1');
            reportCache.set('news', 'content2');
            
            expect(reportCache.cache.size).toBe(2);
            
            const deleted = reportCache.delete('market');
            
            expect(deleted).toBe(true);
            expect(reportCache.cache.size).toBe(1);
            expect(reportCache.has('market')).toBe(false);
            expect(reportCache.has('news')).toBe(true);
        });
        
        test('should return false when deleting non-existent entries', () => {
            const deleted = reportCache.delete('nonexistent');
            expect(deleted).toBe(false);
        });
        
        test('should clear all cached content', () => {
            reportCache.set('market', 'content1');
            reportCache.set('news', 'content2');
            reportCache.set('fundamentals', 'content3');
            
            expect(reportCache.cache.size).toBe(3);
            
            reportCache.clear();
            
            expect(reportCache.cache.size).toBe(0);
            expect(reportCache.has('market')).toBe(false);
            expect(reportCache.has('news')).toBe(false);
            expect(reportCache.has('fundamentals')).toBe(false);
        });
    });
    
    describe('Statistics and Monitoring', () => {
        beforeEach(() => {
            reportCache.setContext('AAPL', '2025-09-14');
        });
        
        test('should provide accurate cache statistics', () => {
            reportCache.set('market', 'content1');
            reportCache.set('news', 'content2');
            
            const stats = reportCache.getStats();
            
            expect(stats.size).toBe(2);
            expect(stats.ticker).toBe('AAPL');
            expect(stats.date).toBe('2025-09-14');
            expect(stats.keys).toEqual(['market', 'news']);
        });
        
        test('should update statistics after cache operations', () => {
            let stats = reportCache.getStats();
            expect(stats.size).toBe(0);
            expect(stats.keys).toEqual([]);
            
            reportCache.set('market', 'content');
            stats = reportCache.getStats();
            expect(stats.size).toBe(1);
            expect(stats.keys).toEqual(['market']);
            
            reportCache.delete('market');
            stats = reportCache.getStats();
            expect(stats.size).toBe(0);
            expect(stats.keys).toEqual([]);
        });
        
        test('should maintain context information in stats', () => {
            const stats1 = reportCache.getStats();
            expect(stats1.ticker).toBe('AAPL');
            expect(stats1.date).toBe('2025-09-14');
            
            reportCache.setContext('TSLA', '2025-09-15');
            const stats2 = reportCache.getStats();
            expect(stats2.ticker).toBe('TSLA');
            expect(stats2.date).toBe('2025-09-15');
        });
    });
    
    describe('Edge Cases and Error Handling', () => {
        test('should handle null and undefined values', () => {
            reportCache.set('test1', null);
            reportCache.set('test2', undefined);
            reportCache.set('test3', '');
            
            expect(reportCache.get('test1')).toBe(null);
            expect(reportCache.get('test2')).toBe(undefined);
            expect(reportCache.get('test3')).toBe('');
            expect(reportCache.has('test1')).toBe(true);
            expect(reportCache.has('test2')).toBe(true);
            expect(reportCache.has('test3')).toBe(true);
        });
        
        test('should handle special characters in agent keys', () => {
            const specialKeys = ['agent-with-dash', 'agent_with_underscore', 'agent.with.dots', 'agent with spaces'];
            
            specialKeys.forEach((key, index) => {
                reportCache.set(key, `content${index}`);
            });
            
            specialKeys.forEach((key, index) => {
                expect(reportCache.get(key)).toBe(`content${index}`);
                expect(reportCache.has(key)).toBe(true);
            });
        });
        
        test('should handle large content strings', () => {
            const largeContent = 'x'.repeat(100000); // 100KB string
            reportCache.set('large', largeContent);
            
            expect(reportCache.get('large')).toBe(largeContent);
            expect(reportCache.has('large')).toBe(true);
        });
        
        test('should handle context with null or undefined values', () => {
            reportCache.setContext(null, '2025-09-14');
            expect(reportCache.currentTicker).toBe(null);
            expect(reportCache.currentDate).toBe('2025-09-14');
            
            reportCache.setContext('AAPL', null);
            expect(reportCache.currentTicker).toBe('AAPL');
            expect(reportCache.currentDate).toBe(null);
            
            reportCache.setContext(undefined, undefined);
            expect(reportCache.currentTicker).toBe(undefined);
            expect(reportCache.currentDate).toBe(undefined);
        });
    });
    
    describe('Performance and Memory', () => {
        test('should handle multiple rapid context switches', () => {
            // Add some initial content
            reportCache.setContext('AAPL', '2025-09-14');
            reportCache.set('market', 'content1');
            reportCache.set('news', 'content2');
            
            expect(reportCache.cache.size).toBe(2);
            
            // Rapid context switches
            for (let i = 0; i < 10; i++) {
                reportCache.setContext(`TICKER${i}`, `2025-09-${14 + i}`);
                expect(reportCache.cache.size).toBe(0); // Should be cleared each time
                
                reportCache.set('test', `content${i}`);
                expect(reportCache.cache.size).toBe(1);
            }
        });
        
        test('should handle many cached entries efficiently', () => {
            reportCache.setContext('AAPL', '2025-09-14');
            
            // Add many entries
            const numEntries = 1000;
            for (let i = 0; i < numEntries; i++) {
                reportCache.set(`agent${i}`, `content${i}`);
            }
            
            expect(reportCache.cache.size).toBe(numEntries);
            
            // Verify all entries are accessible
            for (let i = 0; i < numEntries; i++) {
                expect(reportCache.get(`agent${i}`)).toBe(`content${i}`);
                expect(reportCache.has(`agent${i}`)).toBe(true);
            }
            
            // Clear should work efficiently
            reportCache.clear();
            expect(reportCache.cache.size).toBe(0);
        });
    });
});