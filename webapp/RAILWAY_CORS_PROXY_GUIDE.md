# Railway CORS and Proxy Configuration Guide

This guide explains the CORS and proxy handling configuration for deploying the TradingAgents web application on Railway.

## Overview

Railway uses a reverse proxy to route traffic to your application, which requires specific configuration for:
- CORS (Cross-Origin Resource Sharing) headers
- WebSocket connections
- Proxy header handling
- Static file serving

## CORS Configuration

### Dynamic Origin Detection

The application automatically detects and configures CORS origins based on the Railway environment:

```python
def get_allowed_origins():
    """Get allowed origins with comprehensive Railway proxy support"""
    origins = [
        "http://localhost:8000",
        "http://localhost:8001", 
        "http://127.0.0.1:8000",
        "http://127.0.0.1:8001"
    ]
    
    # Railway domain configurations
    railway_domain = os.environ.get("RAILWAY_PUBLIC_DOMAIN")
    railway_static_url = os.environ.get("RAILWAY_STATIC_URL")
    railway_project_domain = os.environ.get("RAILWAY_PROJECT_DOMAIN")
    
    # Add Railway domains with comprehensive coverage
    railway_domains = []
    if railway_domain:
        railway_domains.extend([railway_domain])
    if railway_static_url:
        # Extract domain from static URL
        import re
        domain_match = re.search(r'https?://([^/]+)', railway_static_url)
        if domain_match:
            railway_domains.append(domain_match.group(1))
    if railway_project_domain:
        railway_domains.append(railway_project_domain)
    
    # Add all Railway domains with both HTTP and HTTPS
    for domain in railway_domains:
        origins.extend([
            f"https://{domain}",
            f"http://{domain}"
        ])
    
    # In development or if no specific domain, allow all origins
    railway_env = os.environ.get("RAILWAY_ENVIRONMENT", "development")
    if railway_env != "production" or not railway_domains:
        return ["*"]
    
    return origins
```

### Environment Variables

The CORS configuration uses these Railway environment variables:

- `RAILWAY_PUBLIC_DOMAIN`: The public domain assigned by Railway
- `RAILWAY_STATIC_URL`: Static URL for the deployment
- `RAILWAY_PROJECT_DOMAIN`: Project-specific domain
- `RAILWAY_ENVIRONMENT`: Environment type (production, staging, etc.)

## Proxy Header Handling

### Railway Proxy Middleware

A custom middleware handles Railway's reverse proxy headers:

```python
class RailwayProxyMiddleware(BaseHTTPMiddleware):
    """Middleware to handle Railway's reverse proxy headers and routing"""
    
    async def dispatch(self, request: Request, call_next):
        # Handle Railway proxy headers
        forwarded_proto = request.headers.get("x-forwarded-proto")
        forwarded_host = request.headers.get("x-forwarded-host")
        forwarded_for = request.headers.get("x-forwarded-for")
        
        # Set proper scheme for Railway HTTPS termination
        if forwarded_proto:
            request.scope["scheme"] = forwarded_proto
        
        # Set proper host for Railway routing
        if forwarded_host:
            request.scope["server"] = (forwarded_host, 443 if forwarded_proto == "https" else 80)
        
        response = await call_next(request)
        
        # Add headers for Railway proxy compatibility
        response.headers["X-Railway-Proxy"] = "handled"
        
        # Ensure WebSocket upgrade headers are preserved
        if request.headers.get("upgrade") == "websocket":
            response.headers["Connection"] = "Upgrade"
            response.headers["Upgrade"] = "websocket"
        
        return response
```

### Proxy Headers

Railway forwards these headers to your application:

- `X-Forwarded-Proto`: Original protocol (http/https)
- `X-Forwarded-Host`: Original host header
- `X-Forwarded-For`: Client IP address
- `X-Real-IP`: Real client IP address

## WebSocket Configuration

### Enhanced WebSocket Endpoint

The WebSocket endpoint is enhanced to handle Railway's proxy:

```python
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """Enhanced WebSocket endpoint with Railway proxy support"""
    
    # Log connection details for Railway debugging
    client_host = websocket.client.host if websocket.client else "unknown"
    forwarded_for = websocket.headers.get("x-forwarded-for", "")
    
    # Check for Railway proxy headers
    railway_headers = {
        "x-forwarded-proto": websocket.headers.get("x-forwarded-proto"),
        "x-forwarded-host": websocket.headers.get("x-forwarded-host"),
        "x-forwarded-for": websocket.headers.get("x-forwarded-for"),
        "x-real-ip": websocket.headers.get("x-real-ip"),
    }
    
    # Send initial connection confirmation with Railway info
    await websocket.send_text(json.dumps({
        "type": "connection_established",
        "message": "WebSocket connected successfully",
        "railway_proxy": bool(railway_info),
        "timestamp": datetime.datetime.utcnow().isoformat()
    }))
```

### Client-Side WebSocket

The JavaScript WebSocket client automatically detects the correct protocol:

```javascript
setupWebSocket() {
    // Enhanced WebSocket setup with Railway proxy support
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const host = window.location.host;
    const wsUrl = `${protocol}//${host}/ws`;
    
    console.log('Connecting to WebSocket:', wsUrl);
    console.log('Connection details:', {
        protocol: window.location.protocol,
        host: window.location.host,
        pathname: window.location.pathname,
        origin: window.location.origin
    });
    
    this.websocket = new WebSocket(wsUrl);
    
    // Enhanced connection handling with reconnection logic
    this.websocket.onopen = () => {
        console.log('WebSocket connected successfully');
        
        // Send initial ping to test connection
        this.sendWebSocketMessage({
            type: 'ping',
            message: 'connection_test',
            timestamp: new Date().toISOString()
        });
    };
}
```

## Testing Configuration

### Proxy Test Endpoint

A dedicated endpoint tests the Railway proxy configuration:

```bash
GET /api/railway/proxy-test
```

This endpoint returns:
- Railway proxy headers
- Environment information
- CORS configuration
- Request details

### Test Script

Use the provided test script to validate the configuration:

```bash
# Test local development
python webapp/test_railway_proxy.py

# Test Railway deployment
python webapp/test_railway_proxy.py --railway

# Test specific URL
python webapp/test_railway_proxy.py --url https://your-app.railway.app
```

The test script validates:
- CORS preflight requests
- Proxy header handling
- WebSocket connections
- Static file serving
- Health endpoint

## Troubleshooting

### Common Issues

1. **CORS Errors**
   - Check `RAILWAY_PUBLIC_DOMAIN` environment variable
   - Verify allowed origins in logs
   - Test with `/api/railway/proxy-test` endpoint

2. **WebSocket Connection Failures**
   - Ensure WSS protocol for HTTPS sites
   - Check proxy headers in WebSocket handshake
   - Verify Railway proxy middleware is active

3. **Static File Issues**
   - Check static file mounting configuration
   - Verify file paths are relative
   - Test individual static file endpoints

### Debug Information

Enable debug logging to see detailed proxy information:

```python
# Set log level to DEBUG
LOG_LEVEL=DEBUG
```

Check logs for:
- Railway proxy headers
- CORS origin matching
- WebSocket connection details
- Static file serving

### Environment Variables

Ensure these Railway environment variables are set:

```bash
# Required
PORT=8001
RAILWAY_ENVIRONMENT=production

# Optional but recommended
RAILWAY_PUBLIC_DOMAIN=your-app.railway.app
RAILWAY_PROJECT_ID=your-project-id
```

## Best Practices

1. **CORS Configuration**
   - Use specific origins in production
   - Allow all origins only in development
   - Include both HTTP and HTTPS variants

2. **WebSocket Handling**
   - Implement reconnection logic
   - Handle proxy headers properly
   - Use proper protocol detection

3. **Proxy Headers**
   - Always check for forwarded headers
   - Set proper scheme and host
   - Preserve WebSocket upgrade headers

4. **Testing**
   - Test both local and Railway environments
   - Validate all endpoints and WebSocket connections
   - Monitor logs for proxy-related issues

## Security Considerations

1. **Origin Validation**
   - Restrict CORS origins in production
   - Validate forwarded headers
   - Log suspicious requests

2. **Header Handling**
   - Sanitize proxy headers
   - Validate forwarded protocols
   - Check for header injection

3. **WebSocket Security**
   - Validate WebSocket origins
   - Implement proper authentication
   - Rate limit connections

## Monitoring

Monitor these metrics in Railway:
- CORS preflight success rate
- WebSocket connection success rate
- Proxy header presence
- Static file serving performance

Use the health endpoint to monitor:
- Overall application health
- Database connectivity
- API service availability
- Static file availability