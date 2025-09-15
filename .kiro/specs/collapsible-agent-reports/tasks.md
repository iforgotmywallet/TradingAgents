# Implementation Plan

- [x] 1. Create backend API endpoint for serving agent reports
  - Add new route `/api/reports/{ticker}/{date}/{agent}` to FastAPI app
  - Implement file reading logic to load report content from results directory
  - Add agent name to report file mapping dictionary
  - Implement error handling for missing files and invalid paths
  - _Requirements: 3.1, 3.2, 3.3_

- [x] 2. Update HTML structure for collapsible agent cards
  - Replace existing progress display with card-based layout in index.html
  - Create team section containers with proper headers
  - Add card structure with header, status badge, and collapsible body
  - Include expand/collapse icons and proper Bootstrap classes
  - _Requirements: 1.1, 1.2, 5.1, 5.2_

- [x] 3. Implement CSS styling for agent cards and status states
  - Add CSS classes for different card states (pending, in_progress, completed, error)
  - Create color schemes for each status type matching requirement specifications
  - Style team section headers and card spacing
  - Add hover effects and transition animations for smooth interactions
  - _Requirements: 4.1, 4.2, 4.3, 4.4, 5.3_

- [x] 4. Create JavaScript AgentCard class for state management
  - Implement AgentCard class with properties for status, expansion state, and report content
  - Add methods for status updates, report loading, and UI synchronization
  - Create agent name to report file mapping logic
  - Implement caching mechanism to avoid repeated API calls
  - _Requirements: 2.1, 2.2, 3.1_

- [x] 5. Implement report content loading and formatting functionality
  - Create ReportFormatter class with markdown to HTML conversion methods
  - Add table formatting support for report data tables
  - Implement error handling for malformed content and missing reports
  - Add loading states and fallback messages for unavailable reports
  - _Requirements: 3.2, 3.3, 2.4_

- [x] 6. Add card expansion and collapse interaction logic
  - Implement click handlers for card headers to toggle expansion
  - Add smooth CSS transitions for card body show/hide animations
  - Update expand/collapse icons based on card state
  - Ensure only completed cards are clickable and expandable
  - _Requirements: 2.1, 2.2, 2.3, 5.3_

- [x] 7. Integrate collapsible cards with existing WebSocket status updates
  - Update existing `updateAgentStatus` method to work with new card structure
  - Modify `initializeProgress` method to create card-based layout instead of simple progress items
  - Ensure status changes properly update card appearance and enable/disable expansion
  - Maintain backward compatibility with existing WebSocket message handling
  - _Requirements: 1.3, 1.4, 4.1, 4.2, 4.3, 4.4_

- [x] 8. Add comprehensive error handling and user feedback
  - Implement graceful degradation when reports are not available
  - Add retry mechanisms for failed report loading attempts
  - Display user-friendly error messages for different failure scenarios
  - Add loading spinners and progress indicators during report fetching
  - _Requirements: 3.3, 3.4_

- [x] 9. Create unit tests for new functionality
  - Write tests for AgentCard class methods and state management
  - Test ReportFormatter markdown conversion with various content types
  - Create tests for API endpoint with different scenarios (success, not found, error)
  - Add tests for card interaction logic and expansion behavior
  - _Requirements: All requirements validation_

- [x] 10. Update existing analysis completion flow to work with new card system
  - Modify `handleAnalysisComplete` method to populate cards with final results
  - Ensure final recommendation display works alongside expanded cards
  - Update results display logic to complement rather than replace card content
  - Test complete analysis workflow from start to finish with new card interface
  - _Requirements: 2.4, 5.4_