# Railway Environment Variables Setup Guide

This guide provides step-by-step instructions for configuring environment variables in Railway for the TradingAgents web application.

## Overview

The TradingAgents application requires several environment variables to function properly. These variables include API keys for external services, database configuration, and optional settings for enhanced functionality.

## Required Environment Variables

### 1. OpenAI API Key
**Variable:** `OPENAI_API_KEY`  
**Required:** Yes  
**Description:** API key for OpenAI GPT models used by the LLM agents

**How to get:**
1. Visit [OpenAI Platform](https://platform.openai.com/api-keys)
2. Sign up or log in to your account
3. Click "Create new secret key"
4. Copy the key (starts with `sk-`)

**Railway Setup:**
1. Go to your Railway project dashboard
2. Click on the "Variables" tab
3. Click "New Variable"
4. Set Name: `OPENAI_API_KEY`
5. Set Value: Your OpenAI API key
6. Click "Add"

### 2. Finnhub API Key
**Variable:** `FINNHUB_API_KEY`  
**Required:** Yes  
**Description:** API key for financial data from Finnhub (free tier available)

**How to get:**
1. Visit [Finnhub](https://finnhub.io/register)
2. Create a free account
3. Go to your dashboard
4. Copy your API key

**Railway Setup:**
1. In Railway project dashboard, go to "Variables" tab
2. Click "New Variable"
3. Set Name: `FINNHUB_API_KEY`
4. Set Value: Your Finnhub API key
5. Click "Add"

### 3. Database URL
**Variable:** `NEON_DATABASE_URL`  
**Required:** Yes  
**Description:** PostgreSQL database connection URL for storing analysis results

**How to get:**
1. Visit [Neon](https://neon.tech)
2. Create a free account
3. Create a new project
4. Go to "Connection Details"
5. Copy the connection string (starts with `postgresql://`)

**Railway Setup:**
1. In Railway project dashboard, go to "Variables" tab
2. Click "New Variable"
3. Set Name: `NEON_DATABASE_URL`
4. Set Value: Your Neon database URL
5. Click "Add"

## Optional Environment Variables

### Additional LLM Providers

#### Anthropic (Claude)
**Variable:** `ANTHROPIC_API_KEY`  
**Required:** No  
**Description:** API key for Anthropic Claude models (optional alternative to OpenAI)

**How to get:**
1. Visit [Anthropic Console](https://console.anthropic.com/)
2. Create an account and get API access
3. Generate an API key

#### Google (Gemini)
**Variable:** `GOOGLE_API_KEY`  
**Required:** No  
**Description:** API key for Google Gemini models (optional alternative to OpenAI)

**How to get:**
1. Visit [Google AI Studio](https://makersuite.google.com/app/apikey)
2. Create or select a project
3. Generate an API key

### Database Configuration

#### Database Pool Size
**Variable:** `DB_POOL_SIZE`  
**Required:** No  
**Default:** `10`  
**Description:** Number of database connections in the connection pool

**Recommended values:**
- Small applications: `5-10`
- Medium applications: `10-20`
- Large applications: `20-50`

#### Database SSL Mode
**Variable:** `DB_SSL_MODE`  
**Required:** No  
**Default:** `require`  
**Description:** SSL mode for database connections

**Valid values:**
- `require`: Require SSL connection (recommended for production)
- `prefer`: Prefer SSL but allow non-SSL
- `disable`: Disable SSL (not recommended for production)

### Application Configuration

#### Log Level
**Variable:** `LOG_LEVEL`  
**Required:** No  
**Default:** `INFO`  
**Description:** Logging level for the application

**Valid values:**
- `DEBUG`: Detailed debugging information
- `INFO`: General information (recommended)
- `WARNING`: Warning messages only
- `ERROR`: Error messages only

#### Debug Mode
**Variable:** `TRADINGAGENTS_DEBUG`  
**Required:** No  
**Default:** `false`  
**Description:** Enable debug mode for detailed logging

**Valid values:**
- `true`: Enable debug mode
- `false`: Disable debug mode

## Railway-Provided Variables

These variables are automatically provided by Railway and don't need to be set manually:

- `PORT`: Port number for the web server
- `RAILWAY_ENVIRONMENT`: Deployment environment (production, staging, etc.)
- `RAILWAY_PROJECT_ID`: Railway project identifier
- `RAILWAY_PUBLIC_DOMAIN`: Public domain for your Railway deployment

## Setup Instructions

### Method 1: Railway Dashboard (Recommended)

1. **Access your Railway project:**
   - Go to [Railway Dashboard](https://railway.app/dashboard)
   - Select your TradingAgents project

2. **Navigate to Variables:**
   - Click on your service
   - Click the "Variables" tab

3. **Add required variables:**
   - Click "New Variable" for each required variable
   - Enter the variable name and value
   - Click "Add"

4. **Deploy:**
   - Railway will automatically redeploy with new variables
   - Check the deployment logs for any issues

### Method 2: Railway CLI

1. **Install Railway CLI:**
   ```bash
   npm install -g @railway/cli
   ```

2. **Login to Railway:**
   ```bash
   railway login
   ```

3. **Link to your project:**
   ```bash
   railway link
   ```

4. **Set variables:**
   ```bash
   railway variables set OPENAI_API_KEY=your_openai_key_here
   railway variables set FINNHUB_API_KEY=your_finnhub_key_here
   railway variables set NEON_DATABASE_URL=your_database_url_here
   ```

5. **Deploy:**
   ```bash
   railway up
   ```

## Validation and Troubleshooting

### Environment Validation Endpoint

After deployment, you can check if your environment variables are properly configured:

**URL:** `https://your-app.railway.app/api/environment/validation`

This endpoint will return:
- Validation status for all variables
- Detailed error messages for missing or invalid variables
- Setup recommendations

### Health Check Endpoint

**URL:** `https://your-app.railway.app/health`

This endpoint provides overall application health including:
- Environment variable validation status
- Database connectivity
- API service availability
- Static file serving status

### Common Issues and Solutions

#### 1. "OpenAI API key is required" Error
**Solution:** Ensure `OPENAI_API_KEY` is set and starts with `sk-`

#### 2. "Database connection failed" Error
**Solutions:**
- Verify `NEON_DATABASE_URL` is correct
- Check if your Neon database is active
- Ensure the database URL includes SSL parameters

#### 3. "Finnhub API key appears to be too short" Error
**Solution:** Verify you copied the complete API key from Finnhub dashboard

#### 4. Application starts but features don't work
**Solutions:**
- Check the `/api/environment/validation` endpoint
- Review Railway deployment logs
- Verify all required environment variables are set

### Security Best Practices

1. **Never commit API keys to your repository**
2. **Use Railway's encrypted environment variables**
3. **Regularly rotate your API keys**
4. **Use the minimum required permissions for API keys**
5. **Monitor your API usage and costs**

## Environment Variable Checklist

Before deploying to Railway, ensure you have:

- [ ] `OPENAI_API_KEY` - OpenAI API key
- [ ] `FINNHUB_API_KEY` - Finnhub API key  
- [ ] `NEON_DATABASE_URL` - PostgreSQL database URL
- [ ] Optional: `ANTHROPIC_API_KEY` - Anthropic API key
- [ ] Optional: `GOOGLE_API_KEY` - Google API key
- [ ] Optional: `DB_POOL_SIZE` - Database pool size
- [ ] Optional: `DB_SSL_MODE` - Database SSL mode
- [ ] Optional: `LOG_LEVEL` - Application log level

## Support

If you encounter issues with environment variable setup:

1. Check the validation endpoint: `/api/environment/validation`
2. Review Railway deployment logs
3. Verify API keys are valid and have sufficient credits/quota
4. Check database connectivity from your local environment
5. Consult the Railway documentation for platform-specific issues

## Example .env File for Local Development

For local development, create a `.env` file in the webapp directory:

```bash
# Required API Keys
OPENAI_API_KEY=sk-your-openai-key-here
FINNHUB_API_KEY=your-finnhub-key-here

# Database Configuration
NEON_DATABASE_URL=postgresql://username:password@ep-example.us-east-1.aws.neon.tech/neondb?sslmode=require
DB_POOL_SIZE=10
DB_SSL_MODE=require

# Optional API Keys
# ANTHROPIC_API_KEY=your-anthropic-key-here
# GOOGLE_API_KEY=your-google-key-here

# Optional Configuration
LOG_LEVEL=INFO
TRADINGAGENTS_DEBUG=false
```

**Note:** Never commit the `.env` file to your repository. It's already included in `.gitignore`.