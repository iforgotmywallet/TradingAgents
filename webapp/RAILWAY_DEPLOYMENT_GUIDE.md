# Railway Deployment Guide for TradingAgents

This comprehensive guide walks you through deploying the TradingAgents web application to Railway, from initial setup to production deployment and troubleshooting.

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Railway CLI Setup](#railway-cli-setup)
3. [Project Setup](#project-setup)
4. [Environment Variables Configuration](#environment-variables-configuration)
5. [Deployment Process](#deployment-process)
6. [Post-Deployment Verification](#post-deployment-verification)
7. [Troubleshooting Guide](#troubleshooting-guide)
8. [Monitoring and Maintenance](#monitoring-and-maintenance)
9. [Advanced Configuration](#advanced-configuration)

## Prerequisites

Before deploying to Railway, ensure you have:

- [ ] Git repository with the TradingAgents code
- [ ] Railway account (sign up at [railway.app](https://railway.app))
- [ ] Node.js installed (for Railway CLI)
- [ ] Required API keys:
  - OpenAI API key
  - Finnhub API key
  - Neon PostgreSQL database URL

## Railway CLI Setup

### Installation

Install the Railway CLI using npm:

```bash
npm install -g @railway/cli
```

Verify installation:

```bash
railway --version
```

### Authentication

Login to your Railway account:

```bash
railway login
```

This will open a browser window for authentication. Once logged in, you'll see a success message in your terminal.

### CLI Commands Reference

Essential Railway CLI commands:

```bash
# Login to Railway
railway login

# Create a new project
railway init

# Link to existing project
railway link

# Deploy current directory
railway up

# View deployment logs
railway logs

# Set environment variables
railway variables set KEY=value

# List environment variables
railway variables

# Open project in browser
railway open

# Check project status
railway status
```

## Project Setup

### Method 1: Deploy from GitHub (Recommended)

1. **Push your code to GitHub:**
   ```bash
   git add .
   git commit -m "Prepare for Railway deployment"
   git push origin main
   ```

2. **Create Railway project from GitHub:**
   - Go to [Railway Dashboard](https://railway.app/dashboard)
   - Click "New Project"
   - Select "Deploy from GitHub repo"
   - Choose your TradingAgents repository
   - Select the `webapp` directory as the root

3. **Configure build settings:**
   - Railway will automatically detect Python
   - Build command: `pip install -r requirements.txt`
   - Start command: `python app.py`

### Method 2: Deploy using Railway CLI

1. **Navigate to webapp directory:**
   ```bash
   cd webapp
   ```

2. **Initialize Railway project:**
   ```bash
   railway init
   ```

3. **Deploy:**
   ```bash
   railway up
   ```

## Environment Variables Configuration

### Required Environment Variables

Set these variables before deployment:

```bash
# OpenAI API Key
railway variables set OPENAI_API_KEY=sk-your-openai-key-here

# Finnhub API Key
railway variables set FINNHUB_API_KEY=your-finnhub-key-here

# Database URL
railway variables set NEON_DATABASE_URL=postgresql://username:password@host/database?sslmode=require
```

### Optional Environment Variables

Configure these for enhanced functionality:

```bash
# Database configuration
railway variables set DB_POOL_SIZE=10
railway variables set DB_SSL_MODE=require

# Logging configuration
railway variables set LOG_LEVEL=INFO
railway variables set TRADINGAGENTS_DEBUG=false

# Additional LLM providers (optional)
railway variables set ANTHROPIC_API_KEY=your-anthropic-key-here
railway variables set GOOGLE_API_KEY=your-google-key-here
```

### Environment Variables via Dashboard

1. Go to your Railway project dashboard
2. Click on your service
3. Navigate to the "Variables" tab
4. Click "New Variable" for each variable
5. Enter name and value
6. Click "Add"

### Bulk Environment Variable Setup

Create a `.env.railway` file locally (don't commit this):

```bash
OPENAI_API_KEY=sk-your-openai-key-here
FINNHUB_API_KEY=your-finnhub-key-here
NEON_DATABASE_URL=postgresql://username:password@host/database?sslmode=require
DB_POOL_SIZE=10
DB_SSL_MODE=require
LOG_LEVEL=INFO
```

Then set all variables at once:

```bash
railway variables set --from-file .env.railway
```

## Deployment Process

### Step-by-Step Deployment

1. **Prepare your code:**
   ```bash
   # Ensure all changes are committed
   git add .
   git commit -m "Ready for Railway deployment"
   git push origin main
   ```

2. **Deploy to Railway:**
   ```bash
   cd webapp
   railway up
   ```

3. **Monitor deployment:**
   ```bash
   railway logs --follow
   ```

4. **Check deployment status:**
   ```bash
   railway status
   ```

### Deployment Configuration Files

Ensure these files are present in your `webapp` directory:

#### railway.toml
```toml
[build]
builder = "NIXPACKS"

[deploy]
healthcheckPath = "/health"
healthcheckTimeout = 300
restartPolicyType = "ON_FAILURE"
restartPolicyMaxRetries = 10
```

#### Procfile
```
web: python app.py
```

#### requirements.txt
Ensure all dependencies are listed:
```
fastapi==0.104.1
uvicorn[standard]==0.24.0
websockets==12.0
psycopg2-binary==2.9.9
sqlalchemy==2.0.23
openai==1.3.7
anthropic==0.7.7
google-generativeai==0.3.2
finnhub-python==2.4.20
python-dotenv==1.0.0
pydantic==2.5.0
jinja2==3.1.2
python-multipart==0.0.6
```

## Post-Deployment Verification

### 1. Check Application Health

Visit your health check endpoint:
```bash
curl https://your-app.railway.app/health
```

Expected response:
```json
{
  "status": "healthy",
  "timestamp": "2025-09-17T10:30:00Z",
  "environment": "production",
  "services": {
    "database": "connected",
    "openai": "available",
    "finnhub": "available"
  }
}
```

### 2. Validate Environment Variables

Check environment validation:
```bash
curl https://your-app.railway.app/api/environment/validation
```

### 3. Test Web Interface

1. Open your Railway app URL in a browser
2. Verify the web interface loads correctly
3. Test WebSocket connections (real-time updates)
4. Try running a trading analysis

### 4. Test API Endpoints

```bash
# Test basic API
curl https://your-app.railway.app/api/health

# Test environment status
curl https://your-app.railway.app/api/environment/status
```

## Troubleshooting Guide

### Common Deployment Issues

#### 1. Build Failures

**Issue:** Dependencies fail to install
```
ERROR: Could not find a version that satisfies the requirement
```

**Solutions:**
- Check `requirements.txt` for correct package versions
- Ensure Python version compatibility
- Update Railway build settings if needed

```bash
# Check Railway build logs
railway logs --deployment
```

#### 2. Application Won't Start

**Issue:** Application fails to start after successful build
```
Error: Application failed to start on port 8001
```

**Solutions:**
- Verify `PORT` environment variable usage in `app.py`
- Check for missing environment variables
- Review application startup logs

```bash
# Check startup logs
railway logs --tail 100
```

#### 3. Environment Variable Issues

**Issue:** "Required environment variable is missing"

**Solutions:**
- Verify all required variables are set:
```bash
railway variables
```
- Check variable names for typos
- Ensure values are properly formatted

#### 4. Database Connection Issues

**Issue:** "Database connection failed"

**Solutions:**
- Verify `NEON_DATABASE_URL` format
- Check database is active in Neon dashboard
- Test connection locally first

```bash
# Test database connection
python -c "
import os
import psycopg2
url = os.environ['NEON_DATABASE_URL']
conn = psycopg2.connect(url)
print('Database connection successful')
conn.close()
"
```

#### 5. Static Files Not Loading

**Issue:** CSS/JS files return 404 errors

**Solutions:**
- Verify static file paths in `app.py`
- Check static files are included in deployment
- Review Railway static file serving configuration

#### 6. WebSocket Connection Issues

**Issue:** Real-time features not working

**Solutions:**
- Verify WebSocket endpoint configuration
- Check Railway proxy settings
- Test WebSocket connections locally

### Debugging Steps

1. **Check deployment logs:**
   ```bash
   railway logs --deployment
   ```

2. **Monitor runtime logs:**
   ```bash
   railway logs --follow
   ```

3. **Verify environment variables:**
   ```bash
   railway variables
   ```

4. **Test health endpoints:**
   ```bash
   curl https://your-app.railway.app/health
   curl https://your-app.railway.app/api/environment/validation
   ```

5. **Check Railway service status:**
   ```bash
   railway status
   ```

### Performance Issues

#### High Memory Usage

**Symptoms:** Application restarts frequently, slow responses

**Solutions:**
- Monitor memory usage in Railway dashboard
- Optimize database connection pooling
- Reduce `DB_POOL_SIZE` if needed
- Consider upgrading Railway plan

#### Slow Response Times

**Symptoms:** API calls take too long, timeouts

**Solutions:**
- Check database query performance
- Optimize API key usage and caching
- Monitor external service response times
- Review application logs for bottlenecks

## Monitoring and Maintenance

### Railway Dashboard Monitoring

1. **Deployment History:**
   - View all deployments
   - Compare deployment performance
   - Rollback if needed

2. **Metrics:**
   - CPU and memory usage
   - Request volume and response times
   - Error rates

3. **Logs:**
   - Real-time log streaming
   - Log search and filtering
   - Export logs for analysis

### Health Check Monitoring

Set up automated monitoring:

```bash
# Create a simple monitoring script
#!/bin/bash
URL="https://your-app.railway.app/health"
RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" $URL)

if [ $RESPONSE -eq 200 ]; then
    echo "✅ Application is healthy"
else
    echo "❌ Application health check failed (HTTP $RESPONSE)"
fi
```

### Log Analysis

Monitor application logs for:
- Error patterns
- Performance bottlenecks
- API usage patterns
- Database connection issues

```bash
# Search logs for errors
railway logs | grep ERROR

# Monitor specific patterns
railway logs --follow | grep "Database connection"
```

### Maintenance Tasks

#### Regular Updates

1. **Update dependencies:**
   ```bash
   pip list --outdated
   pip install --upgrade package-name
   ```

2. **Update Railway CLI:**
   ```bash
   npm update -g @railway/cli
   ```

3. **Monitor API usage:**
   - Check OpenAI API usage and billing
   - Monitor Finnhub API rate limits
   - Review database storage usage

#### Backup and Recovery

1. **Database backups:**
   - Use Neon's automatic backup features
   - Export critical data regularly
   - Test restore procedures

2. **Configuration backups:**
   - Document environment variable settings
   - Keep deployment configuration in version control
   - Maintain deployment runbooks

## Advanced Configuration

### Custom Domains

1. **Add custom domain in Railway:**
   - Go to project settings
   - Add custom domain
   - Configure DNS records

2. **SSL certificates:**
   - Railway provides automatic SSL
   - Custom certificates can be configured

### Scaling Configuration

```toml
# railway.toml
[deploy]
replicas = 2
healthcheckPath = "/health"
healthcheckTimeout = 300
restartPolicyType = "ON_FAILURE"
restartPolicyMaxRetries = 10

[build]
builder = "NIXPACKS"
buildCommand = "pip install -r requirements.txt"
```

### Environment-Specific Configuration

Create different configurations for staging and production:

```bash
# Staging environment
railway variables set ENVIRONMENT=staging
railway variables set LOG_LEVEL=DEBUG

# Production environment
railway variables set ENVIRONMENT=production
railway variables set LOG_LEVEL=INFO
```

### Database Connection Optimization

```python
# Optimize database settings for Railway
DB_CONFIG = {
    'pool_size': int(os.environ.get('DB_POOL_SIZE', 10)),
    'max_overflow': int(os.environ.get('DB_MAX_OVERFLOW', 20)),
    'pool_timeout': int(os.environ.get('DB_POOL_TIMEOUT', 30)),
    'pool_recycle': int(os.environ.get('DB_POOL_RECYCLE', 3600)),
}
```

## Security Best Practices

### Environment Variable Security

1. **Never commit secrets to Git**
2. **Use Railway's encrypted environment variables**
3. **Regularly rotate API keys**
4. **Monitor API key usage**

### Network Security

1. **Use HTTPS for all communications**
2. **Configure proper CORS settings**
3. **Implement rate limiting**
4. **Monitor for suspicious activity**

### Database Security

1. **Use SSL connections**
2. **Implement proper access controls**
3. **Regular security updates**
4. **Monitor database access logs**

## Support and Resources

### Railway Resources

- [Railway Documentation](https://docs.railway.app/)
- [Railway Community Discord](https://discord.gg/railway)
- [Railway Status Page](https://status.railway.app/)

### TradingAgents Resources

- Environment validation: `/api/environment/validation`
- Health check: `/health`
- Application logs: `railway logs`

### Getting Help

1. **Check validation endpoints first**
2. **Review Railway deployment logs**
3. **Test configuration locally**
4. **Consult Railway documentation**
5. **Check Railway community forums**

## Deployment Checklist

Before deploying to Railway:

- [ ] All code committed and pushed to Git
- [ ] `requirements.txt` is up to date
- [ ] `railway.toml` and `Procfile` are configured
- [ ] All required environment variables are ready
- [ ] Database is set up and accessible
- [ ] API keys are valid and have sufficient quota
- [ ] Local testing completed successfully
- [ ] Health check endpoint is working
- [ ] Static files are properly configured

After deployment:

- [ ] Health check endpoint returns 200
- [ ] Environment validation passes
- [ ] Web interface loads correctly
- [ ] WebSocket connections work
- [ ] Database operations function properly
- [ ] All API integrations are working
- [ ] Monitoring is set up
- [ ] Custom domain configured (if applicable)

## Conclusion

This guide provides comprehensive instructions for deploying TradingAgents to Railway. Follow the steps carefully, and use the troubleshooting section to resolve any issues. The application should be fully functional on Railway with proper configuration and monitoring in place.

For additional support, refer to the validation endpoints and Railway's extensive documentation and community resources.