import * as cdk from 'aws-cdk-lib';
import { Template } from 'aws-cdk-lib/assertions';
import * as AgentTools from '../lib/agent-tools-stack';

test('Agents-as-Tools Lambda Function Created', () => {
  const app = new cdk.App();
  const stack = new AgentTools.AgentToolsStack(app, 'MyTestStack');
  const template = Template.fromStack(stack);

  // Test that Lambda function is created with correct properties
  template.hasResourceProperties('AWS::Lambda::Function', {
    Runtime: 'python3.12',
    Handler: 'agent_handler.handler',
    FunctionName: 'agents-as-tools-strands-agent-dev',
    Architectures: ['arm64'],
    MemorySize: 2048,
    Timeout: 300,
  });
});

test('S3 Buckets Created', () => {
  const app = new cdk.App();
  const stack = new AgentTools.AgentToolsStack(app, 'MyTestStack');
  const template = Template.fromStack(stack);

  // Test that input bucket is created with dynamic name
  template.hasResourceProperties('AWS::S3::Bucket', {
    BucketName: {
      'Fn::Join': [
        '',
        [
          'agents-as-tools-input-dev-',
          { Ref: 'AWS::AccountId' }
        ]
      ]
    }
  });

  // Test that output bucket is created with dynamic name
  template.hasResourceProperties('AWS::S3::Bucket', {
    BucketName: {
      'Fn::Join': [
        '',
        [
          'agents-as-tools-output-dev-',
          { Ref: 'AWS::AccountId' }
        ]
      ]
    }
  });

  // Alternative: Just check that 2 S3 buckets exist
  template.resourceCountIs('AWS::S3::Bucket', 2);
});

test('Lambda Layer Created', () => {
  const app = new cdk.App();
  const stack = new AgentTools.AgentToolsStack(app, 'MyTestStack');
  const template = Template.fromStack(stack);

  // Test that Lambda layer is created
  template.hasResourceProperties('AWS::Lambda::LayerVersion', {
    Description: 'Strands Agents SDK and dependencies for agents-as-tools processing',
    CompatibleRuntimes: ['python3.12'],
  });
});

test('IAM Permissions for Bedrock and S3', () => {
  const app = new cdk.App();
  const stack = new AgentTools.AgentToolsStack(app, 'MyTestStack');
  const template = Template.fromStack(stack);

  // Check that IAM policies exist (there should be 2: Lambda role policy + bucket notifications policy)
  template.resourceCountIs('AWS::IAM::Policy', 2);

  // Check that the Lambda function has an IAM role
  template.hasResourceProperties('AWS::IAM::Role', {
    AssumeRolePolicyDocument: {
      Statement: [
        {
          Action: 'sts:AssumeRole',
          Effect: 'Allow',
          Principal: {
            Service: 'lambda.amazonaws.com'
          }
        }
      ]
    }
  });

  // Check that Bedrock permissions exist somewhere in the template
  const templateJson = template.toJSON();
  const hasBedrockPermissions = JSON.stringify(templateJson).includes('bedrock:InvokeModel');
  expect(hasBedrockPermissions).toBe(true);
});

test('EventBridge Rule Created', () => {
  const app = new cdk.App();
  const stack = new AgentTools.AgentToolsStack(app, 'MyTestStack');
  const template = Template.fromStack(stack);

  // Test that EventBridge rule is created
  template.hasResourceProperties('AWS::Events::Rule', {
    Name: 'agents-as-tools-s3-events-dev',
    Description: 'Trigger agents-as-tools processing when programming language files are uploaded to S3',
  });
});

test('Lambda Function has Environment Variables', () => {
  const app = new cdk.App();
  const stack = new AgentTools.AgentToolsStack(app, 'MyTestStack');
  const template = Template.fromStack(stack);

  // Test that Lambda function has correct environment variables
  template.hasResourceProperties('AWS::Lambda::Function', {
    Environment: {
      Variables: {
        ENVIRONMENT: 'dev',
        BEDROCK_REGION: 'us-east-1',
        TRANSLATION_MODEL: 'anthropic.claude-3-sonnet-20240229-v1:0',
        QUALITY_MODEL: 'anthropic.claude-3-sonnet-20240229-v1:0'
      }
    }
  });
});