# Railway CLI Setup and Usage Guide

This guide covers everything you need to know about setting up and using the Railway CLI for deploying and managing the TradingAgents application.

## Table of Contents

1. [Installation](#installation)
2. [Authentication](#authentication)
3. [Project Management](#project-management)
4. [Deployment Commands](#deployment-commands)
5. [Environment Variables](#environment-variables)
6. [Monitoring and Logs](#monitoring-and-logs)
7. [Advanced Usage](#advanced-usage)
8. [Troubleshooting CLI Issues](#troubleshooting-cli-issues)

## Installation

### Prerequisites

- Node.js (version 14 or higher)
- npm or yarn package manager
- Git (for repository management)

### Install Railway CLI

#### Using npm (Recommended)

```bash
npm install -g @railway/cli
```

#### Using yarn

```bash
yarn global add @railway/cli
```

#### Verify Installation

```bash
railway --version
```

Expected output:
```
@railway/cli/3.x.x
```

### Update Railway CLI

Keep your CLI updated for the latest features:

```bash
npm update -g @railway/cli
```

## Authentication

### Login to Railway

```bash
railway login
```

This command will:
1. Open your default browser
2. Redirect to Railway's authentication page
3. Prompt you to authorize the CLI
4. Return a success message in your terminal

### Verify Authentication

```bash
railway whoami
```

This shows your Railway account information.

### Logout

```bash
railway logout
```

## Project Management

### Create New Project

#### From Current Directory

```bash
railway init
```

This will:
- Create a new Railway project
- Link your current directory to the project
- Prompt for project name and settings

#### From GitHub Repository

```bash
railway init --template https://github.com/your-username/tradingagents
```

### Link to Existing Project

If you have an existing Railway project:

```bash
railway link
```

This will show a list of your projects to choose from.

#### Link to Specific Project

```bash
railway link [project-id]
```

### Project Information

```bash
# Show current project info
railway status

# Show project details
railway info
```

### Unlink Project

```bash
railway unlink
```

## Deployment Commands

### Deploy Application

#### Basic Deployment

```bash
railway up
```

This command:
- Builds your application
- Deploys to Railway
- Shows deployment progress
- Provides the deployment URL

#### Deploy with Custom Build Command

```bash
railway up --build-cmd "pip install -r requirements.txt"
```

#### Deploy Specific Directory

```bash
railway up --path ./webapp
```

### Deployment Options

#### Deploy and Watch Logs

```bash
railway up --logs
```

#### Deploy with Environment Variables

```bash
railway up --env ENVIRONMENT=production
```

#### Force Redeploy

```bash
railway redeploy
```

### Deployment Status

```bash
# Check deployment status
railway status

# List all deployments
railway deployments

# Get specific deployment info
railway deployment [deployment-id]
```

## Environment Variables

### List Variables

```bash
# List all environment variables
railway variables

# List variables in JSON format
railway variables --json
```

### Set Variables

#### Single Variable

```bash
railway variables set OPENAI_API_KEY=sk-your-key-here
```

#### Multiple Variables

```bash
railway variables set \
  OPENAI_API_KEY=sk-your-key-here \
  FINNHUB_API_KEY=your-finnhub-key \
  NEON_DATABASE_URL=postgresql://...
```

#### From File

Create a `.env.railway` file:
```bash
OPENAI_API_KEY=sk-your-key-here
FINNHUB_API_KEY=your-finnhub-key
NEON_DATABASE_URL=postgresql://...
```

Then load it:
```bash
railway variables set --from-file .env.railway
```

### Delete Variables

```bash
# Delete single variable
railway variables delete VARIABLE_NAME

# Delete multiple variables
railway variables delete VAR1 VAR2 VAR3
```

### Export Variables

```bash
# Export to .env file
railway variables > .env.backup

# Export specific variables
railway variables get OPENAI_API_KEY FINNHUB_API_KEY
```

## Monitoring and Logs

### View Logs

#### Recent Logs

```bash
# Show last 100 log lines
railway logs

# Show last 50 log lines
railway logs --tail 50
```

#### Follow Logs in Real-time

```bash
railway logs --follow
```

#### Deployment Logs

```bash
# Show build and deployment logs
railway logs --deployment

# Show logs for specific deployment
railway logs --deployment [deployment-id]
```

#### Filter Logs

```bash
# Filter by log level
railway logs | grep ERROR
railway logs | grep WARNING

# Filter by timestamp
railway logs --since 1h
railway logs --since "2025-09-17 10:00:00"
```

### Service Management

#### Restart Service

```bash
railway restart
```

#### Scale Service

```bash
railway scale --replicas 2
```

#### Service Information

```bash
railway service
```

## Advanced Usage

### Multiple Environments

#### Create Environment

```bash
railway environment create staging
```

#### Switch Environment

```bash
railway environment use staging
```

#### List Environments

```bash
railway environment list
```

### Database Management

#### Connect to Database

```bash
railway connect postgres
```

#### Database Shell

```bash
railway shell
```

### Custom Domains

#### Add Domain

```bash
railway domain add yourdomain.com
```

#### List Domains

```bash
railway domain list
```

#### Remove Domain

```bash
railway domain remove yourdomain.com
```

### Project Collaboration

#### Add Team Member

```bash
railway team add user@example.com
```

#### List Team Members

```bash
railway team list
```

### Configuration Files

#### Generate railway.toml

```bash
railway init --config
```

This creates a `railway.toml` file:
```toml
[build]
builder = "NIXPACKS"

[deploy]
healthcheckPath = "/health"
healthcheckTimeout = 300
restartPolicyType = "ON_FAILURE"
restartPolicyMaxRetries = 10
```

### Backup and Restore

#### Backup Project Configuration

```bash
# Export project settings
railway project export > project-backup.json

# Export environment variables
railway variables > variables-backup.env
```

#### Restore Configuration

```bash
# Import project settings
railway project import project-backup.json

# Import environment variables
railway variables set --from-file variables-backup.env
```

## Troubleshooting CLI Issues

### Common CLI Problems

#### CLI Not Found

**Error:** `railway: command not found`

**Solutions:**
```bash
# Reinstall CLI
npm uninstall -g @railway/cli
npm install -g @railway/cli

# Check PATH
echo $PATH

# Use npx as alternative
npx @railway/cli --version
```

#### Authentication Issues

**Error:** `Not authenticated`

**Solutions:**
```bash
# Re-authenticate
railway logout
railway login

# Check authentication status
railway whoami
```

#### Project Linking Issues

**Error:** `No project linked`

**Solutions:**
```bash
# Link to existing project
railway link

# Create new project
railway init

# Check current project
railway status
```

### CLI Performance Issues

#### Slow Commands

**Solutions:**
```bash
# Clear CLI cache
rm -rf ~/.railway

# Update CLI
npm update -g @railway/cli

# Use specific commands instead of general ones
railway logs --tail 10  # instead of railway logs
```

#### Network Issues

**Solutions:**
```bash
# Check Railway status
curl -I https://railway.app

# Use different network
# Check firewall settings
# Try with VPN if corporate network
```

### Debug Mode

Enable debug mode for detailed CLI output:

```bash
export RAILWAY_DEBUG=1
railway status
```

## CLI Automation and Scripting

### Deployment Script

Create a deployment script `deploy.sh`:

```bash
#!/bin/bash

echo "🚀 Starting TradingAgents deployment..."

# Check if logged in
if ! railway whoami > /dev/null 2>&1; then
    echo "❌ Not logged in to Railway"
    railway login
fi

# Ensure we're in the right directory
cd webapp

# Set environment variables if needed
if [ -f ".env.railway" ]; then
    echo "📝 Setting environment variables..."
    railway variables set --from-file .env.railway
fi

# Deploy application
echo "🔨 Deploying application..."
railway up --logs

# Check deployment status
echo "✅ Deployment complete!"
railway status
```

Make it executable:
```bash
chmod +x deploy.sh
./deploy.sh
```

### Environment Setup Script

Create `setup-env.sh`:

```bash
#!/bin/bash

echo "🔧 Setting up Railway environment variables..."

# Required variables
read -p "Enter OpenAI API Key: " OPENAI_KEY
read -p "Enter Finnhub API Key: " FINNHUB_KEY
read -p "Enter Neon Database URL: " DB_URL

# Set variables
railway variables set \
  OPENAI_API_KEY="$OPENAI_KEY" \
  FINNHUB_API_KEY="$FINNHUB_KEY" \
  NEON_DATABASE_URL="$DB_URL"

# Optional variables with defaults
railway variables set \
  DB_POOL_SIZE=10 \
  DB_SSL_MODE=require \
  LOG_LEVEL=INFO

echo "✅ Environment variables configured!"
railway variables
```

### Monitoring Script

Create `monitor.sh`:

```bash
#!/bin/bash

echo "📊 TradingAgents Monitoring Dashboard"
echo "=================================="

# Project status
echo "📋 Project Status:"
railway status

echo ""
echo "🌐 Health Check:"
HEALTH_URL=$(railway status --json | jq -r '.deployments[0].url')/health
curl -s "$HEALTH_URL" | jq '.'

echo ""
echo "📝 Recent Logs:"
railway logs --tail 10

echo ""
echo "💾 Environment Variables:"
railway variables | wc -l | xargs echo "Total variables:"
```

## Best Practices

### CLI Workflow

1. **Always verify authentication:**
   ```bash
   railway whoami
   ```

2. **Check project status before deploying:**
   ```bash
   railway status
   ```

3. **Use environment-specific deployments:**
   ```bash
   railway environment use staging
   railway up
   ```

4. **Monitor deployments:**
   ```bash
   railway up --logs
   ```

### Security Best Practices

1. **Never commit CLI tokens:**
   - CLI tokens are stored in `~/.railway/`
   - Don't share or commit this directory

2. **Use environment-specific variables:**
   ```bash
   # Development
   railway environment use development
   railway variables set DEBUG=true

   # Production
   railway environment use production
   railway variables set DEBUG=false
   ```

3. **Regularly rotate API keys:**
   ```bash
   railway variables set OPENAI_API_KEY=new-key-here
   ```

### Performance Optimization

1. **Use specific commands:**
   ```bash
   # Instead of
   railway logs

   # Use
   railway logs --tail 20
   ```

2. **Cache environment variables locally:**
   ```bash
   railway variables > .env.cache
   ```

3. **Use deployment IDs for specific operations:**
   ```bash
   railway logs --deployment abc123
   ```

## CLI Reference

### Complete Command List

```bash
# Authentication
railway login
railway logout
railway whoami

# Project Management
railway init
railway link
railway unlink
railway status
railway info

# Deployment
railway up
railway redeploy
railway deployments
railway deployment [id]

# Environment Variables
railway variables
railway variables set KEY=value
railway variables delete KEY
railway variables get KEY

# Logs and Monitoring
railway logs
railway logs --follow
railway logs --deployment
railway restart

# Environments
railway environment create [name]
railway environment use [name]
railway environment list
railway environment delete [name]

# Domains
railway domain add [domain]
railway domain list
railway domain remove [domain]

# Database
railway connect [service]
railway shell

# Team Management
railway team add [email]
railway team list
railway team remove [email]

# Utilities
railway open
railway docs
railway help
```

### Useful Aliases

Add these to your shell profile (`.bashrc`, `.zshrc`):

```bash
# Railway aliases
alias rl='railway'
alias rls='railway status'
alias rll='railway logs'
alias rlf='railway logs --follow'
alias rlu='railway up'
alias rlv='railway variables'
alias rld='railway deployments'
```

## Conclusion

The Railway CLI is a powerful tool for managing your TradingAgents deployment. This guide covers the essential commands and workflows you'll need for successful deployment and maintenance.

Key takeaways:
- Always authenticate before running commands
- Use environment variables for configuration
- Monitor deployments with logs
- Implement automation scripts for repetitive tasks
- Follow security best practices

For additional help, use `railway help` or visit the [Railway Documentation](https://docs.railway.app/).