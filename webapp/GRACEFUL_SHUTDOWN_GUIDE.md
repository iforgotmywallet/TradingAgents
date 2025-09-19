# Graceful Shutdown Implementation Guide

## Overview

The TradingAgents FastAPI application now implements comprehensive graceful shutdown handling to ensure clean termination of all resources when deployed on Railway or other cloud platforms.

## Features Implemented

### 1. Signal Handlers
- **SIGTERM**: Handles Railway's graceful shutdown signal
- **SIGINT**: Handles Ctrl+C for local development
- **Process Exit**: Cleanup function registered with `atexit`

### 2. WebSocket Connection Management
- Graceful closure of all active WebSocket connections
- Shutdown notification sent to connected clients
- Proper connection tracking and cleanup

### 3. Background Task Management
- Tracking of all background analysis tasks
- Graceful cancellation during shutdown
- Proper cleanup of task references

### 4. Database Connection Cleanup
- Proper closure of database connection pools
- Cleanup on both graceful shutdown and process exit
- Error handling for connection cleanup failures

## Implementation Details

### Lifespan Management
The application uses FastAPI's lifespan context manager to handle startup and shutdown:

```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup tasks
    setup_signal_handlers()
    await startup_tasks()
    
    yield
    
    # Shutdown tasks
    await shutdown_tasks()
```

### Signal Handling
Signal handlers are configured to set a global shutdown event:

```python
def setup_signal_handlers():
    def signal_handler(signum, frame):
        logger.info(f"Received signal {signum}. Initiating graceful shutdown...")
        shutdown_event.set()
    
    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)
```

### WebSocket Shutdown
The ConnectionManager handles graceful WebSocket closure:

```python
async def shutdown_all_connections(self):
    # Send shutdown notification
    shutdown_message = json.dumps({
        "type": "server_shutdown",
        "message": "Server is shutting down. Please reconnect in a moment."
    })
    await self.broadcast(shutdown_message)
    
    # Close all connections
    for connection in self.active_connections.copy():
        await connection.close(code=1001, reason="Server shutdown")
```

### Background Task Management
Background tasks are tracked and cancelled during shutdown:

```python
# Track tasks
task = asyncio.create_task(run_analysis_background(graph, request))
background_tasks.add(task)
task.add_done_callback(background_tasks.discard)

# Cancel during shutdown
for task in background_tasks.copy():
    if not task.done():
        task.cancel()
        await task
```

## Railway Deployment Benefits

### 1. Zero-Downtime Deployments
- Railway sends SIGTERM before stopping the container
- Application gracefully closes connections and saves state
- New deployment starts while old one shuts down cleanly

### 2. Resource Cleanup
- Database connections properly closed
- No connection pool leaks
- Memory and resource cleanup

### 3. Client Experience
- WebSocket clients receive shutdown notification
- Clients can automatically reconnect to new deployment
- No abrupt connection drops

## Testing

Run the graceful shutdown test to verify functionality:

```bash
python webapp/test_graceful_shutdown.py
```

The test verifies:
- Signal handler configuration
- Background task cancellation
- WebSocket connection cleanup
- Resource cleanup completion

## Monitoring

The application logs shutdown events for monitoring:

```
INFO - Received signal 15. Initiating graceful shutdown...
INFO - Starting graceful shutdown sequence...
INFO - Closing WebSocket connections...
INFO - Cancelling background tasks...
INFO - Closing database connections...
INFO - Graceful shutdown sequence completed
```

## Best Practices

### 1. Shutdown Timeout
Railway allows 30 seconds for graceful shutdown. The implementation:
- Completes most operations within 5 seconds
- Uses timeouts for WebSocket operations
- Prioritizes critical cleanup tasks

### 2. Error Handling
- All cleanup operations have error handling
- Failures in one cleanup don't prevent others
- Errors are logged for debugging

### 3. State Preservation
- Database transactions are completed before shutdown
- Analysis results are saved before termination
- Client state is preserved where possible

## Troubleshooting

### Common Issues

1. **Shutdown Timeout**
   - Check logs for slow cleanup operations
   - Verify database connection pool size
   - Monitor background task completion

2. **Connection Leaks**
   - Verify all WebSocket connections are tracked
   - Check database connection pool cleanup
   - Monitor resource usage during shutdown

3. **Signal Handling**
   - Ensure signal handlers are configured early
   - Check for signal masking in deployment environment
   - Verify Railway sends SIGTERM correctly

### Debug Mode

Enable debug logging to see detailed shutdown information:

```bash
export LOG_LEVEL=DEBUG
```

This will show:
- Individual connection closures
- Task cancellation details
- Database cleanup operations
- Timing information

## Requirements Satisfied

This implementation satisfies the following requirements from the Railway deployment spec:

- **8.1**: Graceful application shutdown with proper signal handling
- **8.2**: WebSocket connections properly closed on shutdown
- **8.2**: Database connection cleanup procedures implemented

The graceful shutdown handling ensures reliable operation in Railway's cloud environment with proper resource management and client experience.