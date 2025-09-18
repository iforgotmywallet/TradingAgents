#!/bin/bash

# Railway Deployment Validation Script
# This script provides easy access to deployment validation tools

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Default values
BASE_URL=""
CONFIG_FILE="deployment_test_config.json"
COMMAND="validate"

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to show usage
show_usage() {
    echo "Usage: $0 [OPTIONS] [COMMAND]"
    echo ""
    echo "Commands:"
    echo "  validate      Run full deployment validation (default)"
    echo "  pre-deploy    Run pre-deployment checks"
    echo "  post-deploy   Run post-deployment validation"
    echo "  smoke-test    Run quick smoke test"
    echo "  monitor       Start continuous monitoring"
    echo ""
    echo "Options:"
    echo "  -u, --url URL        Base URL of the deployed application"
    echo "  -c, --config FILE    Configuration file (default: deployment_test_config.json)"
    echo "  -h, --help          Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0 validate -u https://myapp.railway.app"
    echo "  $0 pre-deploy"
    echo "  $0 smoke-test -u https://myapp.railway.app"
    echo "  $0 monitor -u https://myapp.railway.app"
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -u|--url)
            BASE_URL="$2"
            shift 2
            ;;
        -c|--config)
            CONFIG_FILE="$2"
            shift 2
            ;;
        -h|--help)
            show_usage
            exit 0
            ;;
        validate|pre-deploy|post-deploy|smoke-test|monitor)
            COMMAND="$1"
            shift
            ;;
        *)
            print_error "Unknown option: $1"
            show_usage
            exit 1
            ;;
    esac
done

# Check if we're in the right directory
if [[ ! -f "app.py" ]]; then
    print_error "This script must be run from the webapp directory"
    exit 1
fi

# Check if Python is available
if ! command -v python3 &> /dev/null; then
    print_error "Python 3 is required but not installed"
    exit 1
fi

# Check if required Python packages are available
print_status "Checking Python dependencies..."
python3 -c "import requests, psycopg2, websockets" 2>/dev/null || {
    print_error "Required Python packages not found. Please install:"
    echo "  pip install requests psycopg2-binary websockets"
    exit 1
}

# Set base URL from environment if not provided
if [[ -z "$BASE_URL" ]]; then
    if [[ -n "$RAILWAY_URL" ]]; then
        BASE_URL="$RAILWAY_URL"
        print_status "Using RAILWAY_URL: $BASE_URL"
    elif [[ -n "$RAILWAY_STATIC_URL" ]]; then
        BASE_URL="$RAILWAY_STATIC_URL"
        print_status "Using RAILWAY_STATIC_URL: $BASE_URL"
    else
        BASE_URL="http://localhost:8001"
        print_warning "No URL provided, using default: $BASE_URL"
    fi
fi

# Create results directory
mkdir -p deployment_test_results

# Run the appropriate command
case $COMMAND in
    validate)
        print_status "Running full deployment validation..."
        python3 validate_deployment.py --base-url "$BASE_URL" --verbose
        ;;
    pre-deploy)
        print_status "Running pre-deployment checks..."
        python3 test_deployment_automation.py pre-deploy --config "$CONFIG_FILE"
        ;;
    post-deploy)
        print_status "Running post-deployment validation..."
        python3 test_deployment_automation.py post-deploy --base-url "$BASE_URL" --config "$CONFIG_FILE"
        ;;
    smoke-test)
        print_status "Running smoke test..."
        python3 test_deployment_automation.py smoke-test --base-url "$BASE_URL" --config "$CONFIG_FILE"
        ;;
    monitor)
        print_status "Starting continuous monitoring..."
        print_warning "Press Ctrl+C to stop monitoring"
        python3 test_deployment_automation.py monitor --base-url "$BASE_URL" --config "$CONFIG_FILE"
        ;;
    *)
        print_error "Unknown command: $COMMAND"
        show_usage
        exit 1
        ;;
esac

# Check exit code and provide feedback
if [[ $? -eq 0 ]]; then
    print_success "Command completed successfully"
    
    # Show latest results file
    LATEST_RESULT=$(ls -t deployment_test_results/*.json 2>/dev/null | head -n1)
    if [[ -n "$LATEST_RESULT" ]]; then
        print_status "Results saved to: $LATEST_RESULT"
        
        # Show summary if it's a validation result
        if [[ "$COMMAND" == "validate" || "$COMMAND" == "post-deploy" ]]; then
            SUMMARY=$(python3 -c "
import json
try:
    with open('$LATEST_RESULT', 'r') as f:
        data = json.load(f)
    summary = data.get('summary', {})
    print(f\"Tests: {summary.get('total', 0)} total, {summary.get('passed', 0)} passed, {summary.get('failed', 0)} failed, {summary.get('warnings', 0)} warnings\")
except:
    pass
" 2>/dev/null)
            if [[ -n "$SUMMARY" ]]; then
                print_status "$SUMMARY"
            fi
        fi
    fi
else
    print_error "Command failed with exit code $?"
    exit 1
fi