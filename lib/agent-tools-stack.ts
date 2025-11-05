import * as cdk from 'aws-cdk-lib';
import * as lambda from 'aws-cdk-lib/aws-lambda';
import * as iam from 'aws-cdk-lib/aws-iam';
import * as s3 from 'aws-cdk-lib/aws-s3';
import * as events from 'aws-cdk-lib/aws-events';
import * as targets from 'aws-cdk-lib/aws-events-targets';
import { Construct } from 'constructs';
import * as path from 'path';

export interface AgentToolsStackProps extends cdk.StackProps {
  environment?: string;
}

export class AgentToolsStack extends cdk.Stack {
  constructor(scope: Construct, id: string, props?: AgentToolsStackProps) {
    super(scope, id, props);

    const environment = props?.environment || 'dev';

    // Paths to packaged Lambda assets
    const packagingDirectory = path.join(__dirname, "../packaging");
    const zipDependencies = path.join(packagingDirectory, "dependencies.zip");
    const zipApp = path.join(packagingDirectory, "app.zip");

    // Create a Lambda layer with Strands Agent dependencies
    const dependenciesLayer = new lambda.LayerVersion(this, 'StrandsAgentDependenciesLayer', {
      code: lambda.Code.fromAsset(zipDependencies),
      compatibleRuntimes: [lambda.Runtime.PYTHON_3_12],
      description: 'Strands Agents SDK and dependencies for agents-as-tools processing',
    });

    // Define the Lambda function
    const agentToolsFunction = new lambda.Function(this, 'AgentToolsStrandsAgent', {
      runtime: lambda.Runtime.PYTHON_3_12,
      functionName: `agents-as-tools-strands-agent-${environment}`,
      handler: 'agent_handler.handler',
      code: lambda.Code.fromAsset(zipApp),
      timeout: cdk.Duration.seconds(300), // Extended timeout for complex translation operations
      memorySize: 2048, // Increased memory for AI translation workloads
      layers: [dependenciesLayer],
      architecture: lambda.Architecture.ARM_64, // ARM64 for better price/performance
      environment: {
        ENVIRONMENT: environment,
        // Translation configuration
        BEDROCK_REGION: 'us-east-1',
        TRANSLATION_MODEL: 'anthropic.claude-3-sonnet-20240229-v1:0',
        QUALITY_MODEL: 'anthropic.claude-3-sonnet-20240229-v1:0',
        MAX_FILE_SIZE_MB: '10',
        MAX_FIX_ATTEMPTS: '3',
        COMPILATION_TIMEOUT: '30',
        // Event loop cycle configuration
        EVENT_LOOP_TIMEOUT: '300',
        MAX_TRANSLATION_ITERATIONS: '3',
      },
      description: `Agents-as-Tools Strands Agent Lambda Function with intelligent orchestration (${environment})`,
    });

    // Add permissions for Bedrock APIs (required for Strands Agents)
    agentToolsFunction.addToRolePolicy(
      new iam.PolicyStatement({
        actions: [
          'bedrock:InvokeModel',
          'bedrock:InvokeModelWithResponseStream'
        ],
        resources: ['*'],
      }),
    );

    // Add permissions for Bedrock AgentCore tools (required for code compilation)
    agentToolsFunction.addToRolePolicy(
      new iam.PolicyStatement({
        actions: [
          'bedrock-agentcore:*',
          'bedrock-agentcore-control:*'
        ],
        resources: ['*'],
      }),
    );

    // Create S3 buckets for input and output
    const inputBucket = new s3.Bucket(this, 'AgentsAsToolsInputBucket', {
      bucketName: `agents-as-tools-input-${environment}-${this.account}`,
      removalPolicy: cdk.RemovalPolicy.DESTROY, // For dev environments
      autoDeleteObjects: true, // For dev environments
      eventBridgeEnabled: true, // Enable EventBridge notifications
      cors: [
        {
          allowedMethods: [s3.HttpMethods.GET, s3.HttpMethods.PUT, s3.HttpMethods.POST],
          allowedOrigins: ['*'],
          allowedHeaders: ['*'],
        },
      ],
    });

    const outputBucket = new s3.Bucket(this, 'AgentsAsToolsOutputBucket', {
      bucketName: `agents-as-tools-output-${environment}-${this.account}`,
      removalPolicy: cdk.RemovalPolicy.DESTROY, // For dev environments
      autoDeleteObjects: true, // For dev environments
      cors: [
        {
          allowedMethods: [s3.HttpMethods.GET],
          allowedOrigins: ['*'],
          allowedHeaders: ['*'],
        },
      ],
    });

    // Add permissions for S3 buckets
    agentToolsFunction.addToRolePolicy(
      new iam.PolicyStatement({
        actions: [
          's3:GetObject',
          's3:PutObject',
          's3:ListBucket'
        ],
        resources: [
          inputBucket.bucketArn,
          `${inputBucket.bucketArn}/*`,
          outputBucket.bucketArn,
          `${outputBucket.bucketArn}/*`,
        ],
      }),
    );

    // Create EventBridge rule for S3 object creation events
    const s3EventRule = new events.Rule(this, 'S3ObjectCreatedRule', {
      ruleName: `agents-as-tools-s3-events-${environment}`,
      description: 'Trigger agents-as-tools processing when programming language files are uploaded to S3',
      eventPattern: {
        source: ['aws.s3'],
        detailType: ['Object Created'],
        detail: {
          bucket: {
            name: [inputBucket.bucketName],
          },
          object: {
            key: [
              // Supported programming languages for translation
              { suffix: '.js' },    // JavaScript
              { suffix: '.jsx' },   // JavaScript (React)
              { suffix: '.mjs' },   // JavaScript (ES modules)
              { suffix: '.cjs' },   // JavaScript (CommonJS)
              { suffix: '.ts' },    // TypeScript
              { suffix: '.tsx' },   // TypeScript (React)
              { suffix: '.java' },  // Java
              { suffix: '.cs' },    // C#
              { suffix: '.cpp' },   // C++
              { suffix: '.cc' },    // C++
              { suffix: '.cxx' },   // C++
              { suffix: '.c++' },   // C++
              { suffix: '.hpp' },   // C++ header
              { suffix: '.hh' },    // C++ header
              { suffix: '.hxx' },   // C++ header
              { suffix: '.h++' },   // C++ header
              { suffix: '.h' },     // C/C++ header
              { suffix: '.c' },     // C (treated as C++)
              { suffix: '.go' },    // Go
              { suffix: '.rs' },    // Rust
              { suffix: '.py' },    // Python (for analysis/quality checks)
              { suffix: '.pyw' },   // Python (Windows)
              { suffix: '.pyi' },   // Python (type stubs)
            ],
          },
        },
      },
    });

    // Add Lambda function as target for EventBridge rule
    s3EventRule.addTarget(new targets.LambdaFunction(agentToolsFunction, {
      event: events.RuleTargetInput.fromObject({
        source: 'eventbridge',
        eventType: 's3-object-created',
        bucket: events.EventField.fromPath('$.detail.bucket.name'),
        key: events.EventField.fromPath('$.detail.object.key'),
        size: events.EventField.fromPath('$.detail.object.size'),
        etag: events.EventField.fromPath('$.detail.object.etag'),
        timestamp: events.EventField.fromPath('$.time'),
        outputBucket: outputBucket.bucketName,
      }),
    }));

    // Add environment variables for bucket names
    agentToolsFunction.addEnvironment('INPUT_BUCKET_NAME', inputBucket.bucketName);
    agentToolsFunction.addEnvironment('OUTPUT_BUCKET_NAME', outputBucket.bucketName);

    // Note: CloudWatch Log Group is automatically created by the Lambda function

    // Outputs
    new cdk.CfnOutput(this, 'LambdaFunctionName', {
      value: agentToolsFunction.functionName,
      description: 'Agents-as-Tools Lambda function name',
    });

    new cdk.CfnOutput(this, 'LambdaFunctionArn', {
      value: agentToolsFunction.functionArn,
      description: 'Agents-as-Tools Lambda function ARN',
    });

    new cdk.CfnOutput(this, 'LayerArn', {
      value: dependenciesLayer.layerVersionArn,
      description: 'Strands Agent dependencies layer ARN',
    });

    new cdk.CfnOutput(this, 'InputBucketName', {
      value: inputBucket.bucketName,
      description: 'S3 bucket for uploading code files for agents-as-tools processing',
    });

    new cdk.CfnOutput(this, 'OutputBucketName', {
      value: outputBucket.bucketName,
      description: 'S3 bucket where agents-as-tools processing results are stored',
    });

    new cdk.CfnOutput(this, 'EventBridgeRuleName', {
      value: s3EventRule.ruleName,
      description: 'EventBridge rule for S3 object creation events',
    });
  }
}