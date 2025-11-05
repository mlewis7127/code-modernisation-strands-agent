# Code Modernisation Strands Agent

This is a working prototype of a model driven approach using the Strands Agent SDK to transform code from one programming language to another. The agent is triggered by a file being delivered to an S3 bucket that contains one of the following major programming languages:

 - **JavaScript**: .js, ,jsx, .mjs, .cjs
 - **TypeScript**: .ts, .tsx
 - **Java**: .java
 - **C#**: .cs
 - **C++**: .cpp, .cs, .cxx, .c++, .hpp, .hh, .hxx, h++, .h, .c
 - **Go**: .go
 - **Rust**: .rs
 - **Python**: .py, .pyw, .pyi 

The model driven approach uses an Agent acting as an orchestrator. Instead of coding for every scenario, it relies on the agent and its underlying large language model to drive its own behaviour. This allows it to figure out which tools to call and in which order, to translate the code to Python, ensure the generated code compiles, and that it is of the highest quality.

The following tools are made available to the agent:

- **language_detector_tool** - Identifies programming languages from code
- **code_translator_tool** - Translates code between programming languages
- **python_compiler_tool** - Compiles and validates Python code using Bedrock AgentCore
- **compilation_fixer_tool** - Automatically fixes compilation errors in Python code
- **quality_analyzer_tool** - Analyzes code quality, security, and best practices
- **quality_improvement_tool** - Applies quality recommendations to improve code
- **file_processor_tool** - Processes file metadata and provides insights


## Architecture

- **AWS Lambda**: Python 3.12 function with Strands Agents SDK
- **Lambda Layer**: Contains all dependencies including Strands Agents SDK and tools
- **Amazon Bedrock**: AI model provider
- **S3 Buckets**: Input bucket for code files, output bucket for analysis results
- **EventBridge**: Triggers Lambda function when files are uploaded to S3
- **CloudWatch**: Logging and monitoring
- **CDK**: Infrastructure as Code using TypeScript

## Project Structure

```
├── bin/
│   ├── agent-as-tools.ts            # CDK app entry point
│   └── package_for_lambda.py        # Lambda packaging script
├── lib/
│   └── agent-tools-stack.ts         # CDK stack definition
├── lambda/
│   └── agent_handler.py             # Strands Agent Lambda handler
├── packaging/                       # Lambda deployment packages
│   ├── app.zip                      # Lambda function code
│   ├── dependencies.zip             # Lambda layer dependencies
│   └── _dependencies/               # Installed Python packages
├── test/
│   └── agent-loop.test.ts           # CDK unit tests
├── cdk.json                         # CDK configuration
├── requirements.txt                 # Python dependencies
└── README.md                        # This file
```

## Features

### 🤖 AI-Powered Code Modernisation
- **Code Translation**: Translates code from other formats into the Python programming language
- **Code Compiler**: Compiles generated Python code
- **Code Fixer**: Fix compilation errors
- **Quality Analyser**: Analyse code for code quality, security and best practices
- **Quality Improvement**: Updates generated code in line with recommendations

### 🚀 Event-Driven Architecture
- **S3 Integration**: Dedicated input and output S3 buckets
- **EventBridge**: Automatic triggering when files are uploaded
- **File Type Support**: Supports 8 programming languages (more could be added)
- **Automatic Processing**: No manual intervention required

### 🏗️ Production-Ready Infrastructure
- **ARM64 Architecture**: Cost-effective Lambda execution
- **Lambda Layers**: Efficient dependency management
- **Auto-scaling**: Serverless scaling based on demand
- **Monitoring**: CloudWatch logs and metrics
- **Security**: IAM roles with least-privilege access

## Prerequisites

- **AWS CLI** configured with appropriate permissions
- **Node.js** 18+ for CDK
- **Python** 3.12+ for Lambda function
- **CDK CLI**: `npm install -g aws-cdk`
- **Amazon Bedrock** model access (Claude 3 Sonnet required)

## Quick Start

### 1. Install Dependencies

```bash
# Install Node.js dependencies
npm install

# Install Python dependencies locally (for development)
pip install -r requirements.txt

# Install Python dependencies for Lambda (ARM64 architecture)
pip install -r requirements.txt \
    --python-version 3.12 \
    --platform manylinux2014_aarch64 \
    --target ./packaging/_dependencies \
    --only-binary=:all:
```

### 2. Package Lambda Function

```bash
# Package the Lambda function and dependencies
python bin/package_for_lambda.py
```

### 3. Deploy Infrastructure

```bash
# Bootstrap CDK (first time only)
npx cdk bootstrap

# Build TypeScript
npm run build

# Deploy the stack
npx cdk deploy --require-approval never
```

### 4. Configure Bedrock Access

**Important**: You must enable model access in Amazon Bedrock before the agent will work properly.

1. Go to the [Amazon Bedrock Console](https://console.aws.amazon.com/bedrock/)
2. Navigate to "Model access" in the left sidebar
3. Click "Enable specific models"
4. Enable access to **Claude 3 Sonnet** (`anthropic.claude-3-sonnet-20240229-v1:0`)
5. Wait for the access to be granted (usually takes a few minutes)

**Note**: The agent uses Claude 3 Sonnet for all tasks, providing consistent and reliable performance across translation, orchestration, and quality analysis.

### 🤖 Single Model Architecture

The application uses **Claude 3 Sonnet** for all tasks:

- **Orchestrator Agent**: Workflow decisions and tool coordination
- **Code Translator**: Cross-language translation accuracy
- **Compilation Fixer**: Understanding and fixing Python errors
- **Quality Analyzer**: Code quality, security, and best practices analysis
- **Quality Improver**: Applying recommendations to enhance code

This approach provides **consistent, reliable performance** with a proven, stable model.

## Usage

After deployment, you can interact with the agent in multiple ways:

### 🔄 Event-Driven S3 Analysis (Recommended)

Simply upload code files to the input S3 bucket and analysis will happen automatically:

```bash
# Upload a code file for automatic analysis
aws s3 cp your_code.py s3://agents-as-tools-input-dev-YOUR_ACCOUNT_ID/

# Check the output bucket for results
aws s3 ls s3://agents-as-tools-output-dev-YOUR_ACCOUNT_ID/analysis/
```

## Development

### Local Testing

```bash
# Run CDK tests
npm test

# Validate CDK template
npx cdk synth

# Compare with deployed stack
npx cdk diff
```

### Adding New Features

1. **Update Lambda Handler**: Modify `lambda/agent_handler.py`
2. **Add Dependencies**: Update `requirements.txt`
3. **Update Infrastructure**: Modify `lib/agent-tools-stack.ts`
4. **Repackage**: Run `python bin/package_for_lambda.py`
5. **Deploy**: Run `npx cdk deploy`

### Monitoring

- **CloudWatch Logs**: `/aws/lambda/code-analysis-strands-agent-dev`
- **API Gateway Metrics**: Available in CloudWatch console
- **Lambda Metrics**: Duration, errors, invocations

## Configuration

### Environment Variables

The Lambda function uses these environment variables:

- `ENVIRONMENT`: Deployment environment (dev/staging/prod)

### Permissions

The Lambda function has the following AWS permissions:

- **Bedrock**: `bedrock:InvokeModel`, `bedrock:InvokeModelWithResponseStream`
- **S3**: `s3:GetObject`, `s3:PutObject`, `s3:ListBucket` (for future S3 integration)
- **CloudWatch**: Basic execution role for logging

## Troubleshooting

### Common Issues

**1. "Model access is denied" Error**
- **Cause**: Bedrock model access not enabled
- **Solution**: Enable model access in Bedrock console (see step 4 above)

**2. "No module named 'strands'" Error**
- **Cause**: Dependencies not properly packaged
- **Solution**: Re-run `python bin/package_for_lambda.py` and redeploy

**3. Lambda Timeout**
- **Cause**: Complex analysis taking too long
- **Solution**: Increase timeout in CDK stack (currently 60 seconds)

**4. Memory Issues**
- **Cause**: Large dependencies or complex analysis
- **Solution**: Increase memory size in CDK stack (currently 1024 MB)

### Debugging

1. **Check CloudWatch Logs**:
   ```bash
   aws logs tail /aws/lambda/code-analysis-strands-agent-dev --follow
   ```

2. **Test Lambda Directly**:
   ```bash
   aws lambda invoke --function-name code-analysis-strands-agent-dev \
     --payload '{"prompt": "test"}' output.json
   ```

3. **Validate Dependencies**:
   ```bash
   unzip -l packaging/dependencies.zip | grep strands
   ```

## Cost Optimization

- **ARM64 Architecture**: ~20% cost savings vs x86_64
- **Lambda Layers**: Reduces deployment package size
- **Efficient Memory**: 1024 MB balances performance and cost
- **Pay-per-use**: Only pay for actual analysis requests

## Security

- **IAM Roles**: Least-privilege access principles
- **VPC**: Can be deployed in VPC for additional security
- **HTTPS**: All API communication encrypted in transit
- **Input Validation**: Request validation and sanitization

## Cleanup

Remove all AWS resources:

```bash
npx cdk destroy --force
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## License

This project is licensed under the MIT License.

## Support

For issues and questions:
1. Check the troubleshooting section above
2. Review CloudWatch logs for error details
3. Consult the [Strands Agents documentation](https://strandsagents.com/)
4. Open an issue in the repository

---

**Built with ❤️ using Strands Agents SDK and AWS CDK**