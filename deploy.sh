#!/bin/bash

# Code Analysis Strands Agent Deployment Script

set -e

echo "========================================="
echo "Code Analysis Strands Agent Deployment"
echo "========================================="
echo

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

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

# Check prerequisites
print_status "Checking prerequisites..."

# Check if Node.js is installed
if ! command -v node &> /dev/null; then
    print_error "Node.js is not installed. Please install Node.js 18+ and try again."
    exit 1
fi

# Check if Python is installed
if ! command -v python &> /dev/null && ! command -v python3 &> /dev/null; then
    print_error "Python is not installed. Please install Python 3.12+ and try again."
    exit 1
fi

# Check if AWS CLI is installed
if ! command -v aws &> /dev/null; then
    print_error "AWS CLI is not installed. Please install AWS CLI and configure it."
    exit 1
fi

# Check if CDK is installed
if ! command -v cdk &> /dev/null; then
    print_warning "CDK CLI is not installed. Installing globally..."
    npm install -g aws-cdk
fi

print_success "Prerequisites check completed"

# Install Node.js dependencies
print_status "Installing Node.js dependencies..."
npm install
print_success "Node.js dependencies installed"

# Install Python dependencies for Lambda
print_status "Installing Python dependencies for Lambda (ARM64)..."
pip install -r requirements.txt \
    --python-version 3.12 \
    --platform manylinux2014_aarch64 \
    --target ./packaging/_dependencies \
    --only-binary=:all:
print_success "Python dependencies installed"

# Package Lambda function
print_status "Packaging Lambda function..."
python bin/package_for_lambda.py
print_success "Lambda function packaged"

# Build TypeScript
print_status "Building TypeScript..."
npm run build
print_success "TypeScript built"

# Check if CDK is bootstrapped
print_status "Checking CDK bootstrap status..."
if ! aws cloudformation describe-stacks --stack-name CDKToolkit &> /dev/null; then
    print_warning "CDK not bootstrapped. Bootstrapping..."
    npx cdk bootstrap
    print_success "CDK bootstrapped"
else
    print_success "CDK already bootstrapped"
fi

# Deploy the stack
print_status "Deploying CDK stack..."
npx cdk deploy --require-approval never

print_success "Deployment completed successfully!"

echo
echo "========================================="
echo "Deployment Summary"
echo "========================================="

# Get stack outputs
API_ENDPOINT=$(aws cloudformation describe-stacks \
    --stack-name agents-as-tools-dev \
    --query 'Stacks[0].Outputs[?OutputKey==`ApiEndpoint`].OutputValue' \
    --output text 2>/dev/null || echo "Not available")

LAMBDA_FUNCTION=$(aws cloudformation describe-stacks \
    --stack-name agents-as-tools-dev \
    --query 'Stacks[0].Outputs[?OutputKey==`LambdaFunctionName`].OutputValue' \
    --output text 2>/dev/null || echo "Not available")

echo "API Endpoint: $API_ENDPOINT"
echo "Lambda Function: $LAMBDA_FUNCTION"
echo

echo "========================================="
echo "Next Steps"
echo "========================================="
echo "1. Enable Bedrock model access:"
echo "   - Go to Amazon Bedrock Console"
echo "   - Navigate to 'Model access'"
echo "   - Enable Claude 3.5 Sonnet or your preferred model"
echo
echo "2. Test the health endpoint:"
echo "   curl $API_ENDPOINT/health"
echo
echo "3. Test code analysis:"
echo "   curl -X POST $API_ENDPOINT/analyze \\"
echo "     -H 'Content-Type: application/json' \\"
echo "     -d '{\"prompt\": \"Analyze this code: def hello(): print(\\\"Hello World\\\")\"}'"
echo
echo "4. Monitor logs:"
echo "   aws logs tail /aws/lambda/$LAMBDA_FUNCTION --follow"
echo

print_success "Deployment script completed!"