# Railway Deployment Guide - Step by Step

## Overview

This guide provides a complete step-by-step process to deploy the optimized TradingAgents web application to Railway. The application has been optimized for fast startup (0.23s) and efficient resource usage.

## Prerequisites

Before starting, ensure you have:

1. **Railway Account**: Sign up at [railway.app](https://railway.app)
2. **Railway CLI**: Install the Railway CLI tool
3. **API Keys**: Obtain required API keys (see Environment Variables section)
4. **Database**: Set up a Neon PostgreSQL database (optional but recommended)

## Step 1: Install Railway CLI

### macOS/Linux:
```bash
curl -fsSL https://railway.app/install.sh | sh
```

### Windows:
```powershell
iwr https://railway.app/install.ps1 | iex
```

### Verify Installation:
```bash
railway --version
```

## Step 2: Prepare Your Environment Variables

### Required API Keys:

1. **OpenAI API Key**
   - Go to [OpenAI API Keys](https://platform.openai.com/api-keys)
   - Create a new API key
   - Copy the key (starts with `sk-`)

2. **Finnhub API Key**
   - Go to [Finnhub](https://finnhub.io/register)
   - Register for a free account
   - Get your API key from the dashboard

3. **Neon Database URL** (Recommended)
   - Go to [Neon](https://neon.tech)
   - Create a free PostgreSQL database
   - Copy the connection string

### Environment Variables List:
```bash
# Required
OPENAI_API_KEY=sk-your-openai-key-here
FINNHUB_API_KEY=your-finnhub-key-here
NEON_DATABASE_URL=postgresql://user:pass@host/db

# Optional (Railway will set these automatically)
PORT=8000
RAILWAY_ENVIRONMENT=production

# Optional API Keys (for additional features)
ANTHROPIC_API_KEY=your-anthropic-key-here
GOOGLE_API_KEY=your-google-key-here

# Optional Configuration
LOG_LEVEL=INFO
TRADINGAGENTS_DEBUG=false
TRADINGAGENTS_RESULTS_DIR=./results
```

## Step 3: Initialize Railway Project

### Option A: Deploy from GitHub (Recommended)

1. **Push your code to GitHub** (if not already done):
```bash
git add .
git commit -m "Optimized app for Railway deployment"
git push origin main
```

2. **Create Railway project from GitHub**:
   - Go to [Railway Dashboard](https://railway.app/dashboard)
   - Click "New Project"
   - Select "Deploy from GitHub repo"
   - Choose your repository
   - Select the branch (usually `main`)

### Option B: Deploy from Local Directory

1. **Login to Railway**:
```bash
railway login
```

2. **Initialize project**:
```bash
cd webapp
railway init
```

3. **Link to existing project** (if you have one):
```bash
railway link [project-id]
```

## Step 4: Configure Environment Variables

### Using Railway Dashboard:

1. Go to your project in Railway Dashboard
2. Click on your service
3. Go to "Variables" tab
4. Add each environment variable:
   - Click "New Variable"
   - Enter variable name and value
   - Click "Add"

### Using Railway CLI:

```bash
# Set required variables
railway variables set OPENAI_API_KEY=sk-your-key-here
railway variables set FINNHUB_API_KEY=your-key-here
railway variables set NEON_DATABASE_URL=postgresql://user:pass@host/db

# Set optional variables
railway variables set LOG_LEVEL=INFO
railway variables set TRADINGAGENTS_DEBUG=false
```

### Verify Variables:
```bash
railway variables
```

## Step 5: Configure Deployment Settings

### Create/Verify Railway Configuration Files:

1. **Procfile** (should already exist):
```
web: uvicorn app:app --host 0.0.0.0 --port $PORT
```

2. **requirements.txt** (should already exist):
```
fastapi==0.116.2
uvicorn[standard]==0.32.0
python-dotenv==1.0.1
pydantic==2.10.2
websockets==13.1
# ... other dependencies
```

3. **railway.toml** (optional, for advanced configuration):
```toml
[build]
builder = "nixpacks"

[deploy]
healthcheckPath = "/health"
healthcheckTimeout = 300
restartPolicyType = "on_failure"
restartPolicyMaxRetries = 3
```

## Step 6: Deploy the Application

### Using Railway Dashboard:

1. Go to your project
2. Click "Deploy"
3. Wait for deployment to complete
4. Check deployment logs for any issues

### Using Railway CLI:

```bash
# Deploy from current directory
railway up

# Or deploy and follow logs
railway up --detach=false
```

### Monitor Deployment:
```bash
# View logs
railway logs

# Check service status
railway status
```

## Step 7: Verify Deployment

### 1. Check Health Endpoint:

Once deployed, Railway will provide a URL like `https://your-app-name.railway.app`

Test the health endpoint:
```bash
curl https://your-app-name.railway.app/health
```

Expected response:
```json
{
  "status": "healthy",
  "message": "TradingAgents Web App is running",
  "environment": "production",
  "version": "1.0.0"
}
```

### 2. Test Environment Validation:
```bash
curl https://your-app-name.railway.app/api/environment/validation
```

### 3. Test Database Connection:
```bash
curl https://your-app-name.railway.app/api/database/health
```

### 4. Access Web Interface:

Open your browser and go to:
```
https://your-app-name.railway.app
```

You should see the TradingAgents web interface.

## Step 8: Configure Custom Domain (Optional)

### Using Railway Dashboard:

1. Go to your service settings
2. Click "Domains" tab
3. Click "Custom Domain"
4. Enter your domain name
5. Configure DNS records as instructed

### DNS Configuration:
Add a CNAME record pointing to your Railway app:
```
CNAME: your-domain.com -> your-app-name.railway.app
```

## Step 9: Set Up Monitoring and Alerts

### Railway Built-in Monitoring:

1. **Metrics**: View CPU, memory, and network usage in Railway dashboard
2. **Logs**: Monitor application logs in real-time
3. **Deployments**: Track deployment history and status

### Health Check Configuration:

Railway automatically monitors the `/health` endpoint. Configure alerts:

1. Go to project settings
2. Set up notification webhooks
3. Configure alert thresholds

## Step 10: Production Optimizations

### 1. Environment-Specific Settings:

Set production-specific variables:
```bash
railway variables set LOG_LEVEL=WARNING
railway variables set TRADINGAGENTS_DEBUG=false
```

### 2. Resource Limits:

Configure resource limits in Railway dashboard:
- **Memory**: Set appropriate memory limits
- **CPU**: Configure CPU allocation
- **Scaling**: Set up auto-scaling if needed

### 3. Security Headers:

The app includes security headers, but verify they're working:
```bash
curl -I https://your-app-name.railway.app/health
```

## Troubleshooting

### Common Issues:

1. **Deployment Fails**:
   - Check logs: `railway logs`
   - Verify all required environment variables are set
   - Ensure requirements.txt includes all dependencies

2. **App Starts but Health Check Fails**:
   - Check if PORT environment variable is set correctly
   - Verify the health endpoint is accessible
   - Check application logs for startup errors

3. **Database Connection Issues**:
   - Verify NEON_DATABASE_URL is correct
   - Check database server status
   - Test connection from local environment first

4. **API Key Issues**:
   - Verify API keys are valid and active
   - Check API key permissions and quotas
   - Test API keys locally before deploying

### Debug Commands:

```bash
# View detailed logs
railway logs --tail

# Check environment variables
railway variables

# Connect to service shell (if needed)
railway shell

# Restart service
railway redeploy
```

### Performance Monitoring:

Monitor these metrics after deployment:
- **Startup Time**: Should be under 1 second
- **Memory Usage**: Monitor for memory leaks
- **Response Time**: Health check should respond quickly
- **Error Rate**: Monitor application errors

## Maintenance

### Regular Tasks:

1. **Update Dependencies**:
   ```bash
   pip install --upgrade -r requirements.txt
   pip freeze > requirements.txt
   git commit -am "Update dependencies"
   railway up
   ```

2. **Monitor Logs**:
   ```bash
   railway logs --tail
   ```

3. **Check Health Status**:
   ```bash
   curl https://your-app-name.railway.app/health
   ```

4. **Update Environment Variables** (as needed):
   ```bash
   railway variables set VARIABLE_NAME=new_value
   ```

### Scaling:

If you need to scale your application:

1. **Vertical Scaling**: Increase memory/CPU in Railway dashboard
2. **Horizontal Scaling**: Enable auto-scaling in Railway settings
3. **Database Scaling**: Upgrade Neon database plan if needed

## Security Considerations

1. **Environment Variables**: Never commit API keys to version control
2. **HTTPS**: Railway provides HTTPS by default
3. **CORS**: The app includes CORS configuration for Railway
4. **Rate Limiting**: Consider implementing rate limiting for production
5. **Monitoring**: Set up alerts for unusual activity

## Cost Optimization

1. **Resource Monitoring**: Monitor CPU and memory usage
2. **Database Usage**: Monitor database connection pool usage
3. **API Costs**: Monitor API usage and costs
4. **Railway Credits**: Track Railway usage and costs

## Support Resources

- **Railway Documentation**: [docs.railway.app](https://docs.railway.app)
- **Railway Discord**: [discord.gg/railway](https://discord.gg/railway)
- **Application Logs**: Use `railway logs` for debugging
- **Health Endpoints**: Monitor `/health` and `/api/environment/validation`

## Conclusion

Your optimized TradingAgents application is now deployed on Railway with:

- ✅ **Fast Startup**: 0.23 second startup time
- ✅ **Efficient Resource Usage**: Minimal memory footprint
- ✅ **Health Monitoring**: Comprehensive health checks
- ✅ **Environment Validation**: Automatic configuration validation
- ✅ **Graceful Shutdown**: Proper cleanup on restart
- ✅ **Production Ready**: Optimized for Railway's infrastructure

The application will automatically restart if it crashes and includes comprehensive logging and monitoring capabilities.