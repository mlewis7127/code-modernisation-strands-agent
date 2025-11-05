# Agents-as-Tools Deployment Guide

This guide walks you through deploying the Agents-as-Tools intelligent code translation system.

## 🚀 Quick Deployment

### 1. **Package Lambda Function**
```bash
python3 bin/package_for_lambda.py
```

This creates:
- `packaging/dependencies.zip` - Lambda layer with Python packages (16MB)
- `packaging/app.zip` - Lambda function code (75KB)

### 2. **Deploy Infrastructure**
```bash
# Build TypeScript
npm run build

# Deploy the stack
npx cdk deploy
```

### 3. **Get Stack Information**
```bash
# List deployed stacks
npx cdk list

# Get stack outputs (bucket names, function name, etc.)
aws cloudformation describe-stacks --stack-name agents-as-tools-dev
```

## 📋 Prerequisites

### Required Tools
- **AWS CLI** configured with appropriate permissions
- **Node.js** 18+ for CDK
- **Python** 3.12+ for Lambda function
- **CDK CLI**: `npm install -g aws-cdk`

### AWS Permissions Required
Your AWS credentials need permissions for:
- CloudFormation (create/update/delete stacks)
- Lambda (create functions and layers)
- S3 (create buckets, put/get objects)
- IAM (create roles and policies)
- EventBridge (create rules)
- Bedrock (model access - see below)

### Amazon Bedrock Model Access
**IMPORTANT**: Enable model access in Amazon Bedrock:

1. Go to [Amazon Bedrock Console](https://console.aws.amazon.com/bedrock/)
2. Navigate to "Model access" 
3. Enable access to:
   - **Claude 3 Sonnet** (`anthropic.claude-3-sonnet-20240229-v1:0`)
4. Wait for access to be granted (usually 2-5 minutes)

## 🏗️ What Gets Deployed

### CloudFormation Stack: `agents-as-tools-dev`

**Lambda Function**: `agents-as-tools-strands-agent-dev`
- Runtime: Python 3.12 on ARM64
- Memory: 2048MB (for AI workloads)
- Timeout: 300 seconds (5 minutes)
- Intelligent orchestration with specialist tools

**S3 Buckets**:
- Input: `agents-as-tools-input-dev-{account-id}`
- Output: `agents-as-tools-output-dev-{account-id}`

**EventBridge Rule**: `agents-as-tools-s3-events-dev`
- Triggers on file uploads to input bucket
- Supports 7 programming languages (.js, .ts, .java, .cs, .cpp, .go, .rs) + Python for analysis

**IAM Permissions**:
- Bedrock model access for AI processing
- Bedrock AgentCore for code compilation
- S3 read/write for file processing

## 🧪 Testing the Deployment

### 1. **Upload Test Files**
```bash
# Get bucket name from stack outputs
INPUT_BUCKET=$(aws cloudformation describe-stacks \
    --stack-name agents-as-tools-dev \
    --query 'Stacks[0].Outputs[?OutputKey==`InputBucketName`].OutputValue' \
    --output text)

# Upload a JavaScript file for translation
echo 'function hello() { console.log("Hello World!"); }' > test.js
aws s3 cp test.js s3://$INPUT_BUCKET/

# Upload a Python file for quality analysis
echo 'def hello(): print("Hello World!")' > test.py
aws s3 cp test.py s3://$INPUT_BUCKET/
```

### 2. **Check Processing Results**
```bash
# Get output bucket name
OUTPUT_BUCKET=$(aws cloudformation describe-stacks \
    --stack-name agents-as-tools-dev \
    --query 'Stacks[0].Outputs[?OutputKey==`OutputBucketName`].OutputValue' \
    --output text)

# List processing results
aws s3 ls s3://$OUTPUT_BUCKET/ --recursive

# Download a result file
aws s3 cp s3://$OUTPUT_BUCKET/analysis/test.js_analysis.md ./
```

### 3. **Monitor Lambda Logs**
```bash
# Watch Lambda logs in real-time
aws logs tail /aws/lambda/agents-as-tools-strands-agent-dev --follow
```

## 🎯 Usage Examples

### Intelligent Processing Examples

**JavaScript Translation**:
- Upload: `calculator.js` → Automatically translates to Python, compiles, fixes errors
- Result: Working Python code + analysis report

**Python Quality Analysis**:
- Upload: `my_script.py` → Skips translation, analyzes quality and security
- Result: Detailed quality report with recommendations

**Language Detection**:
- Upload: `unknown_file.txt` → Detects language, processes accordingly
- Result: Language identification + appropriate processing

### File Types Supported
- **Programming Languages**: .js/.jsx/.mjs/.cjs (JavaScript), .ts/.tsx (TypeScript), .java (Java), .cs (C#), .cpp/.cc/.cxx/.c++/.hpp/.hh/.hxx/.h++/.h/.c (C++), .go (Go), .rs (Rust), .py/.pyw/.pyi (Python)

- **Scripts**: .sh, .r

## 🔧 Configuration

### Environment Variables (Lambda)
The system is pre-configured with:
- `BEDROCK_REGION`: us-east-1
- `TRANSLATION_MODEL`: anthropic.claude-3-sonnet-20240229-v1:0
- `QUALITY_MODEL`: anthropic.claude-3-sonnet-20240229-v1:0
- `MAX_FILE_SIZE_MB`: 10
- `COMPILATION_TIMEOUT`: 30 seconds
- `EVENT_LOOP_TIMEOUT`: 300 seconds

### Different Environments
```bash
# Deploy to staging
npx cdk deploy --context environment=staging

# Deploy to production  
npx cdk deploy --context environment=prod
```

## 🚨 Troubleshooting

### Common Issues

**1. "Model access denied"**
- **Solution**: Enable Claude 3 Sonnet model access in Bedrock console (see prerequisites)

**2. "No module named 'strands'"**
- **Solution**: Re-run `python3 bin/package_for_lambda.py`

**3. "Lambda timeout"**
- **Cause**: Large files or complex processing
- **Solution**: Files >10MB are automatically rejected

**4. "S3 access denied"**
- **Cause**: Insufficient IAM permissions
- **Solution**: Ensure your AWS credentials have S3 permissions

### Debug Commands
```bash
# Check stack status
aws cloudformation describe-stacks --stack-name agents-as-tools-dev

# Test Lambda directly
aws lambda invoke \
  --function-name agents-as-tools-strands-agent-dev \
  --payload '{"source":"test","bucket":"test","key":"test.py","outputBucket":"test"}' \
  output.json

# Check Lambda logs
aws logs describe-log-groups --log-group-name-prefix /aws/lambda/agents-as-tools
```

## 🧹 Cleanup

Remove all resources:
```bash
npx cdk destroy --force
```

This deletes:
- Lambda function and layer
- S3 buckets and all contents
- EventBridge rules
- IAM roles and policies
- CloudWatch log groups

## 💡 Next Steps

After successful deployment:

1. **Integrate with CI/CD**: Add the system to your development workflow
2. **Custom Processing**: Upload files with specific requirements in filenames
3. **Batch Processing**: Upload multiple files for bulk translation
4. **Monitor Usage**: Check CloudWatch metrics for processing patterns
5. **Scale Up**: The system auto-scales based on demand

## 🎉 Success!

Your Agents-as-Tools intelligent code translation system is now deployed and ready to intelligently process code files with AI-powered orchestration!

**Key Benefits**:
- ✅ Intelligent decision making (skips unnecessary steps)
- ✅ Multi-language support (25+ file types)
- ✅ Automatic error fixing and quality analysis
- ✅ Event-driven processing (just upload files)
- ✅ Scalable serverless architecture