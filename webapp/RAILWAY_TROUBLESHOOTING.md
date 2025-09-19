# Railway Deployment Troubleshooting Guide

This guide provides solutions to common issues encountered when deploying TradingAgents to Railway.

## Quick Diagnostic Commands

Before troubleshooting, run these commands to gather information:

```bash
# Check Railway service status
railway status

# View recent logs
railway logs --tail 50

# Check environment variables
railway variables

# Test health endpoint
curl https://your-app.railway.app/health

# Check environment validation
curl https://your-app.railway.app/api/environment/validation
```

## Build and Deployment Issues

### Issue: Build Fails with Dependency Errors

**Symptoms:**
```
ERROR: Could not find a version that satisfies the requirement
ERROR: No matching distribution found for package-name
```

**Causes:**
- Outdated or incompatible package versions
- Missing system dependencies
- Python version mismatch

**Solutions:**

1. **Update requirements.txt:**
   ```bash
   # Generate fresh requirements
   pip freeze > requirements.txt
   
   # Or specify exact versions
   fastapi==0.104.1
   uvicorn[standard]==0.24.0
   ```

2. **Check Python version compatibility:**
   ```toml
   # railway.toml
   [build]
   builder = "NIXPACKS"
   
   [build.env]
   PYTHON_VERSION = "3.11"
   ```

3. **Add system dependencies if needed:**
   ```toml
   # railway.toml
   [build]
   builder = "NIXPACKS"
   
   [build.env]
   APT_PACKAGES = "postgresql-client libpq-dev"
   ```

### Issue: Build Succeeds but Application Won't Start

**Symptoms:**
```
Application failed to start on port 8001
Process exited with code 1
```

**Causes:**
- Port binding issues
- Missing environment variables
- Application startup errors

**Solutions:**

1. **Verify port configuration in app.py:**
   ```python
   import os
   
   if __name__ == "__main__":
       port = int(os.environ.get("PORT", 8001))
       uvicorn.run(app, host="0.0.0.0", port=port)
   ```

2. **Check Procfile:**
   ```
   web: python app.py
   ```

3. **Verify environment variables:**
   ```bash
   railway variables
   ```

4. **Check startup logs:**
   ```bash
   railway logs --deployment
   ```

### Issue: Application Starts but Returns 500 Errors

**Symptoms:**
- Health check fails
- API endpoints return internal server errors
- Application logs show Python exceptions

**Causes:**
- Missing or invalid environment variables
- Database connection failures
- API key issues

**Solutions:**

1. **Check environment validation:**
   ```bash
   curl https://your-app.railway.app/api/environment/validation
   ```

2. **Verify required environment variables:**
   ```bash
   railway variables set OPENAI_API_KEY=sk-your-key-here
   railway variables set FINNHUB_API_KEY=your-key-here
   railway variables set NEON_DATABASE_URL=postgresql://...
   ```

3. **Test database connection:**
   ```python
   # Test script
   import os
   import psycopg2
   
   try:
       conn = psycopg2.connect(os.environ['NEON_DATABASE_URL'])
       print("✅ Database connection successful")
       conn.close()
   except Exception as e:
       print(f"❌ Database connection failed: {e}")
   ```

## Environment Variable Issues

### Issue: "Required environment variable is missing"

**Symptoms:**
```json
{
  "error": "OPENAI_API_KEY: Required environment variable is missing"
}
```

**Solutions:**

1. **Set missing variables:**
   ```bash
   railway variables set OPENAI_API_KEY=sk-your-key-here
   ```

2. **Verify variable names (case-sensitive):**
   ```bash
   railway variables | grep -i openai
   ```

3. **Check for typos in variable names:**
   - `OPENAI_API_KEY` (not `OPENAI_KEY`)
   - `FINNHUB_API_KEY` (not `FINNHUB_KEY`)
   - `NEON_DATABASE_URL` (not `DATABASE_URL`)

### Issue: "API key must start with 'sk-'"

**Symptoms:**
```json
{
  "error": "OPENAI_API_KEY: OpenAI API key must start with 'sk-'"
}
```

**Solutions:**

1. **Verify API key format:**
   - OpenAI keys start with `sk-`
   - Should be 51 characters long
   - Check for extra spaces or characters

2. **Get new API key if needed:**
   - Go to [OpenAI Platform](https://platform.openai.com/api-keys)
   - Create new secret key
   - Copy complete key including `sk-` prefix

### Issue: Database URL Format Errors

**Symptoms:**
```json
{
  "error": "NEON_DATABASE_URL: Database URL must start with 'postgresql://'"
}
```

**Solutions:**

1. **Verify database URL format:**
   ```
   postgresql://username:password@host:port/database?sslmode=require
   ```

2. **Get correct URL from Neon:**
   - Go to Neon dashboard
   - Select your database
   - Copy connection string from "Connection Details"

3. **Ensure SSL mode is included:**
   ```
   ?sslmode=require
   ```

## Database Connection Issues

### Issue: "Database connection failed"

**Symptoms:**
```
psycopg2.OperationalError: could not connect to server
FATAL: password authentication failed
```

**Causes:**
- Incorrect database credentials
- Database server unavailable
- Network connectivity issues
- SSL configuration problems

**Solutions:**

1. **Verify database URL:**
   ```bash
   # Test connection locally first
   python -c "
   import os
   import psycopg2
   conn = psycopg2.connect(os.environ['NEON_DATABASE_URL'])
   print('Connection successful')
   conn.close()
   "
   ```

2. **Check Neon database status:**
   - Go to Neon dashboard
   - Verify database is active
   - Check for any maintenance notifications

3. **Update database URL if needed:**
   ```bash
   railway variables set NEON_DATABASE_URL=postgresql://new-url-here
   ```

4. **Configure SSL properly:**
   ```bash
   railway variables set DB_SSL_MODE=require
   ```

### Issue: Database Connection Pool Exhausted

**Symptoms:**
```
sqlalchemy.exc.TimeoutError: QueuePool limit of size 10 overflow 20 reached
```

**Solutions:**

1. **Adjust pool settings:**
   ```bash
   railway variables set DB_POOL_SIZE=5
   railway variables set DB_MAX_OVERFLOW=10
   ```

2. **Monitor connection usage:**
   ```python
   # Add to your application
   from sqlalchemy import event
   
   @event.listens_for(engine, "connect")
   def set_sqlite_pragma(dbapi_connection, connection_record):
       print(f"Database connection established: {dbapi_connection}")
   ```

## API Integration Issues

### Issue: OpenAI API Calls Fail

**Symptoms:**
```
openai.error.AuthenticationError: Incorrect API key provided
openai.error.RateLimitError: Rate limit exceeded
```

**Solutions:**

1. **Verify API key:**
   ```bash
   # Test API key locally
   python -c "
   import openai
   import os
   openai.api_key = os.environ['OPENAI_API_KEY']
   response = openai.Model.list()
   print('OpenAI API key is valid')
   "
   ```

2. **Check API usage and billing:**
   - Go to [OpenAI Usage Dashboard](https://platform.openai.com/usage)
   - Verify you have available credits
   - Check rate limits

3. **Handle rate limits:**
   ```python
   # Add retry logic
   import time
   from openai.error import RateLimitError
   
   def call_openai_with_retry(func, max_retries=3):
       for attempt in range(max_retries):
           try:
               return func()
           except RateLimitError:
               if attempt < max_retries - 1:
                   time.sleep(2 ** attempt)
               else:
                   raise
   ```

### Issue: Finnhub API Issues

**Symptoms:**
```
HTTP 401: Unauthorized
HTTP 429: Too Many Requests
```

**Solutions:**

1. **Verify Finnhub API key:**
   ```bash
   # Test Finnhub API
   curl "https://finnhub.io/api/v1/quote?symbol=AAPL&token=YOUR_API_KEY"
   ```

2. **Check API limits:**
   - Free tier: 60 calls/minute
   - Upgrade plan if needed
   - Implement caching to reduce calls

3. **Add error handling:**
   ```python
   import requests
   
   def get_stock_data(symbol, api_key):
       try:
           response = requests.get(
               f"https://finnhub.io/api/v1/quote?symbol={symbol}&token={api_key}",
               timeout=10
           )
           response.raise_for_status()
           return response.json()
       except requests.exceptions.RequestException as e:
           print(f"Finnhub API error: {e}")
           return None
   ```

## Static File and WebSocket Issues

### Issue: Static Files Return 404

**Symptoms:**
- CSS and JavaScript files not loading
- Images not displaying
- Browser console shows 404 errors

**Solutions:**

1. **Verify static file configuration:**
   ```python
   # In app.py
   from fastapi.staticfiles import StaticFiles
   
   app.mount("/static", StaticFiles(directory="static"), name="static")
   ```

2. **Check file paths:**
   ```html
   <!-- Use relative paths -->
   <link rel="stylesheet" href="/static/style.css">
   <script src="/static/app.js"></script>
   ```

3. **Verify files are included in deployment:**
   ```bash
   # Check if static files exist
   ls -la static/
   ```

### Issue: WebSocket Connections Fail

**Symptoms:**
```
WebSocket connection failed: Error during WebSocket handshake
Connection closed before receiving a handshake response
```

**Solutions:**

1. **Verify WebSocket endpoint:**
   ```python
   # In app.py
   @app.websocket("/ws")
   async def websocket_endpoint(websocket: WebSocket):
       await websocket.accept()
       # WebSocket logic here
   ```

2. **Check Railway proxy configuration:**
   ```javascript
   // Use wss:// for secure WebSocket connections
   const ws = new WebSocket('wss://your-app.railway.app/ws');
   ```

3. **Test WebSocket locally first:**
   ```bash
   # Install wscat for testing
   npm install -g wscat
   
   # Test WebSocket connection
   wscat -c wss://your-app.railway.app/ws
   ```

## Performance Issues

### Issue: High Memory Usage

**Symptoms:**
- Application restarts frequently
- Out of memory errors
- Slow response times

**Solutions:**

1. **Monitor memory usage:**
   ```bash
   # Check Railway metrics in dashboard
   railway logs | grep -i memory
   ```

2. **Optimize database connections:**
   ```bash
   railway variables set DB_POOL_SIZE=5
   railway variables set DB_MAX_OVERFLOW=5
   ```

3. **Implement memory monitoring:**
   ```python
   import psutil
   import logging
   
   def log_memory_usage():
       memory = psutil.virtual_memory()
       logging.info(f"Memory usage: {memory.percent}%")
   ```

### Issue: Slow Response Times

**Symptoms:**
- API calls take longer than 30 seconds
- Timeout errors
- Poor user experience

**Solutions:**

1. **Add request timeout handling:**
   ```python
   import asyncio
   
   @app.middleware("http")
   async def timeout_middleware(request: Request, call_next):
       try:
           return await asyncio.wait_for(call_next(request), timeout=30.0)
       except asyncio.TimeoutError:
           return JSONResponse(
               status_code=504,
               content={"error": "Request timeout"}
           )
   ```

2. **Optimize database queries:**
   ```python
   # Use connection pooling
   # Add query timeouts
   # Implement caching
   ```

3. **Monitor external API response times:**
   ```python
   import time
   
   def timed_api_call(func):
       start_time = time.time()
       result = func()
       end_time = time.time()
       print(f"API call took {end_time - start_time:.2f} seconds")
       return result
   ```

## Logging and Debugging

### Issue: Missing or Insufficient Logs

**Solutions:**

1. **Configure proper logging:**
   ```python
   import logging
   import os
   
   # Set log level from environment
   log_level = os.environ.get('LOG_LEVEL', 'INFO')
   logging.basicConfig(
       level=getattr(logging, log_level),
       format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
   )
   ```

2. **Add structured logging:**
   ```python
   import json
   import logging
   
   class JSONFormatter(logging.Formatter):
       def format(self, record):
           log_entry = {
               'timestamp': self.formatTime(record),
               'level': record.levelname,
               'message': record.getMessage(),
               'module': record.module
           }
           return json.dumps(log_entry)
   ```

3. **Enable debug mode temporarily:**
   ```bash
   railway variables set TRADINGAGENTS_DEBUG=true
   railway variables set LOG_LEVEL=DEBUG
   ```

### Issue: Can't Access Application Logs

**Solutions:**

1. **Use Railway CLI:**
   ```bash
   # View recent logs
   railway logs --tail 100
   
   # Follow logs in real-time
   railway logs --follow
   
   # Filter logs
   railway logs | grep ERROR
   ```

2. **Check deployment logs:**
   ```bash
   railway logs --deployment
   ```

3. **Export logs for analysis:**
   ```bash
   railway logs --tail 1000 > app_logs.txt
   ```

## Emergency Recovery Procedures

### Issue: Application Completely Down

**Immediate Actions:**

1. **Check Railway service status:**
   ```bash
   railway status
   ```

2. **Review recent deployments:**
   ```bash
   railway logs --deployment --tail 50
   ```

3. **Rollback to previous deployment:**
   - Go to Railway dashboard
   - Navigate to deployments
   - Click "Redeploy" on last working version

4. **Check for Railway platform issues:**
   - Visit [Railway Status Page](https://status.railway.app/)

### Issue: Database Connection Lost

**Immediate Actions:**

1. **Check Neon database status:**
   - Go to Neon dashboard
   - Verify database is active

2. **Test database connection:**
   ```bash
   # Test from local machine
   psql $NEON_DATABASE_URL -c "SELECT 1;"
   ```

3. **Restart Railway service:**
   ```bash
   railway redeploy
   ```

### Issue: Environment Variables Corrupted

**Recovery Steps:**

1. **Backup current variables:**
   ```bash
   railway variables > variables_backup.txt
   ```

2. **Reset critical variables:**
   ```bash
   railway variables set OPENAI_API_KEY=sk-your-key-here
   railway variables set FINNHUB_API_KEY=your-key-here
   railway variables set NEON_DATABASE_URL=postgresql://...
   ```

3. **Verify and redeploy:**
   ```bash
   railway variables
   railway redeploy
   ```

## Prevention and Monitoring

### Proactive Monitoring Setup

1. **Health check monitoring:**
   ```bash
   # Create monitoring script
   #!/bin/bash
   while true; do
       if curl -f https://your-app.railway.app/health > /dev/null 2>&1; then
           echo "$(date): ✅ Health check passed"
       else
           echo "$(date): ❌ Health check failed"
           # Send alert
       fi
       sleep 300  # Check every 5 minutes
   done
   ```

2. **Log monitoring:**
   ```bash
   # Monitor for errors
   railway logs --follow | grep -i error | while read line; do
       echo "ERROR DETECTED: $line"
       # Send alert
   done
   ```

3. **Resource monitoring:**
   - Set up Railway dashboard alerts
   - Monitor memory and CPU usage
   - Track response times

### Best Practices for Stability

1. **Environment variable management:**
   - Document all required variables
   - Use validation on startup
   - Implement graceful degradation

2. **Error handling:**
   - Implement comprehensive error handling
   - Add retry logic for external APIs
   - Use circuit breakers for unreliable services

3. **Testing:**
   - Test deployments in staging first
   - Implement health checks
   - Monitor key metrics

4. **Documentation:**
   - Keep deployment docs updated
   - Document troubleshooting procedures
   - Maintain runbooks for common issues

## Getting Additional Help

### Railway Support Channels

1. **Railway Documentation:** [docs.railway.app](https://docs.railway.app/)
2. **Railway Discord:** [discord.gg/railway](https://discord.gg/railway)
3. **Railway GitHub:** [github.com/railwayapp](https://github.com/railwayapp)

### TradingAgents Specific Help

1. **Environment validation endpoint:** `/api/environment/validation`
2. **Health check endpoint:** `/health`
3. **Application logs:** `railway logs`

### Escalation Process

1. **Check validation endpoints first**
2. **Review Railway deployment logs**
3. **Test configuration locally**
4. **Search Railway community forums**
5. **Contact Railway support if platform issue**

Remember: Most deployment issues are related to environment variables, database connections, or API key problems. Start with the validation endpoints to quickly identify the root cause.