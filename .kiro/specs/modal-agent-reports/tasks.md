# Implementation Plan

- [x] 1. Create modal HTML structure and base styling
  - Add modal overlay and container HTML to index.html
  - Implement modal CSS styles with overlay, container, header, and body
  - Add responsive design for different screen sizes
  - _Requirements: 2.2, 2.4, 3.2, 3.3_

- [x] 2. Implement ModalManager class for modal functionality
  - Create ModalManager class with open/close methods
  - Add event listeners for close button, ESC key, and background clicks
  - Implement modal state management (loading, error, content)
  - Add body scroll prevention when modal is open
  - _Requirements: 2.2, 2.4, 2.5, 3.4, 4.4_

- [x] 3. Create ReportCache class for efficient data management
  - Implement ReportCache class with Map-based storage
  - Add context switching logic to clear cache when ticker/date changes
  - Implement cache get/set/has/clear methods
  - _Requirements: 4.1, 4.2, 4.3_

- [x] 4. Create AgentCardManager for handling card interactions
  - Implement AgentCardManager class with card click event handling
  - Add agent name to agent key mapping logic
  - Implement report loading with API integration using existing ReportFormatter
  - Add error handling and retry functionality
  - Initialize AgentCardManager in main app initialization
  - _Requirements: 2.1, 2.3, 4.1, 4.4, 4.5_

- [x] 5. Remove collapsible card functionality from existing code
  - Remove toggleExpansion, updateExpansionUI, enableExpansion, disableExpansion methods from AgentCard class
  - Remove card-body expansion logic and event listeners from setupEventListeners
  - Remove isExpanded property and expansion-related state management
  - Remove reportCache Map from AgentCard instances (use centralized ReportCache)
  - Remove loadReport method and related report loading logic from AgentCard
  - Keep status management, updateStatus, and basic card structure
  - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.5_

- [x] 6. Simplify agent card HTML structure and styling
  - Remove card-body elements from createAgentCard function in app.js
  - Update card structure to header-only with status display
  - Add hover effects for completed cards to indicate clickability
  - Remove expansion-related CSS classes (.expanded, .card-body.show, etc.) from style.css
  - Remove expand-icon elements and related styling
  - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 2.1, 5.1, 5.2, 5.4_

- [x] 7. Replace card expansion with modal opening
  - Update AgentCard setupEventListeners to use AgentCardManager for clicks
  - Remove existing card expansion event listeners
  - Ensure only completed cards trigger modal opening
  - Update card hover states to indicate clickability for completed cards only
  - _Requirements: 2.1, 2.2, 2.3, 5.1, 5.2_

- [x] 8. Integrate modal system with existing WebSocket updates
  - Update WebSocket message handlers to work with simplified cards
  - Ensure status updates properly enable/disable card clickability
  - Maintain existing team grouping and card organization
  - Update ReportCache context when ticker/date changes via WebSocket
  - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 4.2_

- [x] 9. Remove collapsible-related test files and update existing tests
  - Delete cardInteraction.test.js (contains expansion/collapse tests)
  - Delete analysisCompletion.test.js if it contains expansion-related tests
  - Remove expansion-related test cases from AgentCard.test.js
  - Update remaining tests to focus on modal functionality
  - _Requirements: 5.3, 5.5_

- [x] 10. Create comprehensive tests for modal functionality
  - Create AgentCardManager.test.js for card click handling tests
  - Add tests for ReportCache caching behavior (ReportCache.test.js)
  - Update ModalManager.test.js if needed for integration
  - Add integration tests for complete modal workflow
  - _Requirements: 2.1, 2.2, 2.3, 4.1, 4.2_

- [x] 11. Final cleanup and optimization
  - Remove any remaining dead code from collapsible implementation
  - Remove unused expansion CSS classes and animations from style.css
  - Remove report loading methods from AgentCard class
  - Ensure no console errors or warnings in browser
  - Verify all functionality works with real report data using existing /api/reports endpoint
  - _Requirements: 5.1, 5.2, 5.4, 5.5_