# Implementation Plan

- [x] 1. Remove ChromaDB dependencies and implementations
  - [x] 1.1 Remove ChromaDB imports and references from codebase
    - Search and remove all chromadb imports from Python files
    - Remove chromadb from requirements.txt
    - Clean up any ChromaDB configuration code
    - _Requirements: 1.1, 1.3_

  - [x] 1.2 Remove ChromaDB configuration files and directories
    - Delete .chromadb/ directory if it exists
    - Remove any ChromaDB-specific configuration files
    - Clean up ChromaDB environment variables from .env files
    - _Requirements: 1.2, 1.4_

- [x] 2. Install and configure Neon with Drizzle ORM
  - [x] 2.1 Install required dependencies
    - Add psycopg2-binary for PostgreSQL connection
    - Add drizzle-orm for Python (or use SQLAlchemy as alternative)
    - Update requirements.txt with new dependencies
    - _Requirements: 2.1, 2.2_

  - [x] 2.2 Configure environment variables for Neon
    - Update .env file with NEON_DATABASE_URL
    - Add database connection configuration variables
    - Set SSL mode and channel binding requirements
    - _Requirements: 3.1, 3.2, 3.3, 3.4_

- [x] 3. Create database configuration and connection module
  - [x] 3.1 Implement NeonConfig class
    - Create tradingagents/storage/neon_config.py
    - Implement connection string parsing and validation
    - Add connection pooling configuration
    - Create connection health check methods
    - _Requirements: 3.1, 3.2, 3.3, 3.4_

  - [x] 3.2 Create database connection utilities
    - Implement connection factory with SSL requirements
    - Add connection pool management
    - Create connection retry logic with exponential backoff
    - Add comprehensive error handling for connection failures
    - _Requirements: 3.1, 3.2, 3.3, 3.4_

- [x] 4. Design and implement database schema
  - [x] 4.1 Create database schema definition
    - Create tradingagents/storage/schema.py
    - Define agent_reports table with all required columns
    - Add proper indexes for session_id and ticker/date queries
    - Include UUID primary key and timestamp columns
    - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5, 4.6_

  - [x] 4.2 Implement database migration system
    - Create migration scripts for schema creation
    - Add migration runner that can create tables and indexes
    - Implement schema validation to ensure proper deployment
    - Create rollback capabilities for schema changes
    - _Requirements: 5.1, 5.2, 5.3, 5.4_

- [x] 5. Create report storage service
  - [x] 5.1 Implement ReportStorageService class
    - Create tradingagents/storage/report_storage.py
    - Implement session creation with unique session ID generation
    - Add methods for saving individual agent reports
    - Create final decision and analysis storage methods
    - _Requirements: 6.1, 6.2, 6.3, 6.4, 6.5_

  - [x] 5.2 Add session management utilities
    - Create tradingagents/storage/session_utils.py
    - Implement session ID generation using ticker, date, and timestamp
    - Add session ID parsing and validation functions
    - Create session existence checking methods
    - _Requirements: 4.1, 6.1, 6.2_

  - [x] 5.3 Implement agent type mapping and validation
    - Create mapping between agent names and database columns
    - Add validation for supported agent types
    - Implement report content sanitization and validation
    - Add support for large report content handling
    - _Requirements: 4.2, 4.3, 4.4, 6.1, 6.3_

- [x] 6. Create report retrieval service
  - [x] 6.1 Implement ReportRetrievalService class
    - Create tradingagents/storage/report_retrieval.py
    - Add method to retrieve individual agent reports by session and agent type
    - Implement complete session data retrieval
    - Create final decision and analysis retrieval methods
    - _Requirements: 7.1, 7.2, 7.3, 7.6_

  - [x] 6.2 Add error handling for missing reports
    - Implement proper handling when reports are not yet available
    - Create appropriate error messages for different failure scenarios
    - Add logging for debugging report retrieval issues
    - Ensure consistent API response format
    - _Requirements: 7.3, 7.4, 7.5_

- [x] 7. Integrate storage service with trading graph
  - [x] 7.1 Modify trading graph to use database storage
    - Update TradingAgentsGraph class to initialize storage service
    - Add session creation at the start of analysis
    - Integrate report saving after each agent completes analysis
    - Ensure proper error handling doesn't break existing workflow
    - _Requirements: 6.1, 6.2, 6.3, 6.4, 6.5_

  - [x] 7.2 Add storage hooks for individual agents
    - Identify all points where agent reports are generated
    - Add database storage calls for each agent completion
    - Implement proper session ID tracking throughout analysis
    - Add timestamp updates when reports are saved
    - _Requirements: 6.1, 6.2, 6.3, 6.5_

- [x] 8. Update web API to use database retrieval
  - [x] 8.1 Modify report endpoint to use new retrieval service
    - Update /api/reports/{ticker}/{date}/{agent} endpoint in webapp/app.py
    - Replace file-based report loading with database queries
    - Implement session ID generation from ticker and date
    - Maintain backward compatibility with existing API contract
    - _Requirements: 7.1, 7.2, 7.5, 7.6_

  - [x] 8.2 Implement comprehensive error handling in API
    - Add specific error messages for database vs missing report scenarios
    - Implement proper HTTP status codes for different error types
    - Add structured logging for debugging report retrieval issues
    - Ensure consistent error response format
    - _Requirements: 7.3, 7.4, 7.5_

- [x] 9. Add comprehensive testing
  - [x] 9.1 Create unit tests for storage components
    - Write tests for NeonConfig class and connection management
    - Create tests for ReportStorageService save and retrieve methods
    - Add tests for ReportRetrievalService with various scenarios
    - Test session ID generation and validation functions
    - _Requirements: 8.1, 8.2, 8.3, 8.4, 8.5_

  - [x] 9.2 Create integration tests for end-to-end functionality
    - Test complete analysis workflow with database storage
    - Verify report retrieval through web API works correctly
    - Test concurrent access and data consistency
    - Validate error handling for database connection failures
    - _Requirements: 8.1, 8.2, 8.3, 8.4, 8.5_

- [x] 10. Deploy database schema and validate setup
  - [x] 10.1 Deploy schema to Neon PostgreSQL
    - Run migration scripts to create tables and indexes
    - Verify database connection from application
    - Test basic CRUD operations on agent_reports table
    - Validate SSL connection and security settings
    - _Requirements: 5.1, 5.2, 5.3, 5.4_

  - [x] 10.2 Validate complete system integration
    - Run end-to-end test with actual trading analysis
    - Verify all agent reports are saved correctly to database
    - Test web API retrieval of stored reports
    - Confirm no "Report not available from API" errors occur
    - _Requirements: 6.1, 6.2, 6.3, 6.4, 6.5, 7.1, 7.2, 7.6_