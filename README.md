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

### 🎯 Design-Driven Translation

The agent uses a **two-phase design-driven approach** for superior code modernization:

1. **Design Phase**: Analyzes source code to generate a structured design specification document
2. **Implementation Phase**: Uses the design specification to generate idiomatic Python code

This approach produces higher quality translations by ensuring the AI understands the code's intent, architecture, and behavior before generating Python, rather than performing direct syntactic translation.

The following tools are made available to the orchestrator agent:

- **design_specification_tool** - Analyzes source code and generates structured design documents
- **implementation_from_design_tool** - Generates idiomatic Python from design specifications
- **code_translator_tool** - Direct translation fallback for edge cases
- **python_compiler_tool** - Compiles and validates Python code using Bedrock AgentCore
- **quality_analyzer_tool** - Analyzes code quality, security, and best practices
- **quality_improvement_tool** - Applies quality recommendations to improve code

**Note**: Language detection is handled by the Lambda handler before orchestration to avoid redundant LLM calls. The agent can self-correct compilation errors by analyzing error messages and regenerating improved code.


## Architecture

- **AWS Lambda**: Python 3.12 function with Strands Agents SDK
- **Lambda Layer**: Contains all dependencies including Strands Agents SDK and tools
- **Amazon Bedrock**: AI model provider (Claude 3 Sonnet)
- **S3 Buckets**: Input bucket for code files, output bucket for translated code and design documents
- **EventBridge**: Triggers Lambda function when files are uploaded to S3
- **CloudWatch**: Logging and monitoring
- **CDK**: Infrastructure as Code using TypeScript

### Translation Workflow

```
┌─────────────────┐
│  Upload Code    │
│   to S3 Input   │
└────────┬────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────┐
│              EventBridge Trigger                        │
└────────┬────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────┐
│              Lambda Handler (agent_handler.py)          │
│                                                          │
│  1. Detect Language (LanguageDetector)                  │
│     └─► Deterministic file extension + pattern check   │
│                                                          │
│  2. Skip if Python or Unknown                           │
│     └─► Python files bypass translation                 │
└────────┬────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────┐
│         Intelligent Translation Orchestrator            │
│                                                          │
│  1. Design-Driven Translation (Preferred)               │
│     ├─► design_specification_tool                       │
│     │   └─► Generate design document                    │
│     └─► implementation_from_design_tool                 │
│         └─► Generate Python from design                 │
│                                                          │
│  2. Fallback Translation (If needed)                    │
│     └─► code_translator_tool                            │
│         └─► Direct translation                          │
│                                                          │
│  3. Validation & Quality                                │
│     ├─► python_compiler_tool                            │
│     │   └─► If errors: agent self-corrects & retries   │
│     ├─► quality_analyzer_tool                           │
│     └─► quality_improvement_tool                        │
└────────┬────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────┐
│              Save Results to S3 Output                  │
│  • {filename}.py (Python code)                          │
│  • {filename}_design.md (Design specification)          │
│  • {filename}_metadata.json (Translation metadata)      │
└─────────────────────────────────────────────────────────┘
```

## Project Structure

```
├── bin/
│   ├── agent-as-tools.ts                        # CDK app entry point
│   └── package_for_lambda.py                    # Lambda packaging script
├── lib/
│   └── agent-tools-stack.ts                     # CDK stack definition
├── lambda/
│   ├── agent_handler.py                         # Lambda handler with language detection
│   └── translation/                             # Translation modules
│       ├── intelligent_orchestrator.py          # Main orchestrator agent with tools
│       ├── design_specification.py              # Design specification tool
│       ├── implementation_generator.py          # Implementation from design tool
│       ├── language_detector.py                 # Language detection (used by handler)
│       ├── bedrock_translator.py                # Bedrock translation service
│       ├── bedrock_compiler.py                  # Python compilation via Bedrock
│       ├── compilation_fixer.py                 # Compilation error fixer (legacy)
│       ├── compilation_processor.py             # Compilation result processing
│       ├── quality_assurance.py                 # Code quality analyzer
│       ├── base_translator.py                   # Base translation interface
│       ├── translation_engine.py                # Translation engine
│       ├── s3_output_handler.py                 # S3 output management
│       └── models.py                            # Data models
├── packaging/                                   # Lambda deployment packages
│   ├── app.zip                                  # Lambda function code
│   ├── dependencies.zip                         # Lambda layer dependencies
│   └── _dependencies/                           # Installed Python packages
├── test/
│   └── agent-loop.test.ts                       # CDK unit tests
├── test_backward_compatibility.py               # Backward compatibility tests
├── test_fallback_verification.py                # Fallback mechanism tests
├── cdk.json                                     # CDK configuration
├── requirements.txt                             # Python dependencies
└── README.md                                    # This file
```

## Features

### 🤖 AI-Powered Code Modernisation
- **Design-Driven Translation**: Two-phase approach that analyzes code intent before generating Python
- **Design Specification**: Generates structured design documents capturing architecture and behavior
- **Idiomatic Python Generation**: Creates Python code following best practices and PEP 8 guidelines
- **Code Compiler**: Compiles generated Python code using Bedrock AgentCore
- **Intelligent Self-Correction**: Agent analyzes compilation errors and regenerates improved code
- **Quality Analyser**: Analyzes code for quality, security and best practices
- **Quality Improvement**: Updates generated code in line with recommendations
- **Fallback Translation**: Direct translation available for edge cases
- **Escape Sequence Handling**: Properly decodes escape sequences in generated code for IDE compatibility

### 🚀 Event-Driven Architecture
- **S3 Integration**: Dedicated input and output S3 buckets
- **EventBridge**: Automatic triggering when files are uploaded
- **File Type Support**: Supports 8 programming languages (more could be added)
- **Automatic Processing**: No manual intervention required
- **Smart Pre-filtering**: Language detection happens before orchestration to optimize performance
- **Python Skip Logic**: Python files bypass translation, maintaining backward compatibility

### 🏗️ Production-Ready Infrastructure
- **ARM64 Architecture**: Cost-effective Lambda execution
- **Lambda Layers**: Efficient dependency management
- **Extended Timeout**: 300 seconds for complex design-driven workflows
- **Increased Memory**: 2048 MB for AI translation workloads
- **Auto-scaling**: Serverless scaling based on demand
- **Monitoring**: CloudWatch logs and metrics
- **Security**: IAM roles with least-privilege access
- **Backward Compatibility**: Python files skip design generation, maintaining existing workflows

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
- **Design Analysis Specialist**: Analyzing code architecture and intent
- **Python Implementation Specialist**: Creating idiomatic Python from designs
- **Quality Analysis Specialist**: Code quality, security, and best practices analysis
- **Code Improvement Specialist**: Applying recommendations to enhance code
- **Python Compiler Tool**: Validates Python code using Bedrock AgentCore (direct API, not an agent)

This approach provides **consistent, reliable performance** with a proven, stable model.

## Usage

After deployment, you can interact with the agent in multiple ways:

### 🔄 Event-Driven S3 Translation (Recommended)

Simply upload code files to the input S3 bucket and translation will happen automatically:

```bash
# Upload a code file for automatic translation
aws s3 cp your_code.js s3://agents-as-tools-input-dev-YOUR_ACCOUNT_ID/

# Check the output bucket for results
aws s3 ls s3://agents-as-tools-output-dev-YOUR_ACCOUNT_ID/translated/
```

### 📄 Output Files

For each translated file, the agent generates:

- **`{filename}.py`** - The translated Python code
- **`{filename}_design.md`** - The design specification document (for design-driven translations)
- **`{filename}_metadata.json`** - Translation metadata including approach used, timing, and quality metrics

Example output structure:
```
translated/
├── example.py                    # Translated Python code
├── example_design.md             # Design specification
└── example_metadata.json         # Translation metadata
```

### 🔍 Translation Workflow

The agent automatically determines the best translation approach:

1. **Design-Driven (Preferred)**: For non-Python code files
   - Generates design specification analyzing code architecture
   - Creates idiomatic Python implementation from design
   - Produces higher quality, more maintainable code

2. **Direct Translation (Fallback)**: Used when design generation fails or for edge cases
   - Faster but may produce less idiomatic Python
   - Automatically triggered if design-driven approach encounters issues

3. **Skip Translation**: Python files are validated and analyzed without translation
   - Maintains backward compatibility
   - Focuses on quality analysis and improvement

## Development

### Local Testing

```bash
# Run CDK tests
npm test

# Validate CDK template
npx cdk synth

# Compare with deployed stack
npx cdk diff

# Test backward compatibility
python test_backward_compatibility.py

# Test fallback mechanisms
python test_fallback_verification.py
```

### Testing the Design-Driven Workflow

The project includes comprehensive tests to verify the design-driven translation feature:

**Backward Compatibility Tests** (`test_backward_compatibility.py`):
- ✅ Python files skip design generation (Requirement 1.5)
- ✅ EventBridge S3 trigger mechanism works (Requirement 5.1)
- ✅ IAM permissions are sufficient (Requirement 5.3)
- ✅ Lambda timeout and memory adequate (Requirement 5.4)
- ✅ Bedrock model consistency maintained (Requirement 5.2)

**Fallback Verification Tests** (`test_fallback_verification.py`):
- ✅ Design generation failures trigger fallback to direct translation
- ✅ Implementation failures trigger fallback to direct translation
- ✅ Error messages are clear and actionable
- ✅ Partial results are saved for debugging

### Design Specification Format

The design specification tool generates structured markdown documents with the following sections:

- **Overview**: High-level description of what the code does
- **Functionality**: Detailed description of features and capabilities
- **Architecture**: Overall structure and organization
- **Components**: Major components/classes/modules with descriptions
- **Data Structures**: Key data types, classes, interfaces, or structures
- **Algorithms and Logic**: Important algorithms and business logic
- **Dependencies**: External libraries, APIs, or system dependencies
- **Input/Output**: Expected inputs and outputs
- **Error Handling**: How errors are handled in the original code
- **Special Considerations**: Language-specific features and performance notes

This structured approach ensures the implementation phase has complete context about the code's intent and architecture.

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
- **Cause**: Complex translation taking too long
- **Solution**: Timeout is set to 300 seconds for design-driven workflows; check CloudWatch logs for specific errors

**4. Memory Issues**
- **Cause**: Large dependencies or complex translation
- **Solution**: Memory is set to 2048 MB for AI translation workloads; check CloudWatch logs for specific errors

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

## Recent Improvements

### Performance Optimizations
- **Removed Redundant Language Detection**: Language detection now happens once in the handler, not again in the orchestrator (saves ~2-3 seconds and 200-300 tokens per translation)
- **Fixed Processing Success Detection**: Success is now determined by actual workflow outcomes (code generated + compilation passed) rather than naive string matching
- **Escape Sequence Decoding**: Generated code properly decodes `\n` and `\t` escape sequences for IDE compatibility
- **SDK Version Pinned**: Using `strands-agents==1.15.0` for stable API and simplified code (98% reduction in response extraction code)

### Simplifications
- **Removed Unused Tools**: Eliminated `file_processor_tool` (never used) and `compilation_fixer_tool` (ineffective)
- **Agent Self-Correction**: Agent now intelligently fixes compilation errors by analyzing error messages and regenerating code
- **Cleaner Codebase**: Reduced from 8 tools to 6 focused tools, removing ~100 lines of unused/ineffective code

### Bug Fixes
- **False Negative Detection**: Fixed issue where successful translations were marked as failed due to words like "error" appearing in exception names (e.g., `ZeroDivisionError`)
- **Code Formatting**: Downloaded Python files now display correctly in IDEs with proper newlines and indentation

## Cost Optimization

- **ARM64 Architecture**: ~20% cost savings vs x86_64
- **Lambda Layers**: Reduces deployment package size
- **Optimized Memory**: 2048 MB balances performance and cost for AI workloads
- **Intelligent Workflow**: Design-driven approach only used when beneficial
- **Pay-per-use**: Only pay for actual translation requests
- **Single Model**: Claude 3 Sonnet used consistently, simplifying cost management
- **Efficient Pre-filtering**: Language detection happens before orchestration, avoiding unnecessary LLM calls

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