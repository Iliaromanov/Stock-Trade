import * as cdk from 'aws-cdk-lib';
import { CfnOutput, Duration, RemovalPolicy } from 'aws-cdk-lib';
import * as apigw from 'aws-cdk-lib/aws-apigateway';
import * as iam from 'aws-cdk-lib/aws-iam';
import * as lambda from 'aws-cdk-lib/aws-lambda';
import * as eventTargets from 'aws-cdk-lib/aws-events-targets';
import * as s3 from 'aws-cdk-lib/aws-s3';
import * as events from 'aws-cdk-lib/aws-events';
import { RuleTargetInput } from 'aws-cdk-lib/aws-events';
import * as cloudfront from 'aws-cdk-lib/aws-cloudfront';
import * as origins from 'aws-cdk-lib/aws-cloudfront-origins';
import * as logs from 'aws-cdk-lib/aws-logs';
import { BlockPublicAccess, BucketEncryption } from 'aws-cdk-lib/aws-s3';
import { Construct } from 'constructs';


const LAMBDA_CONFIG_ENV : {[key:string]: {[key:string]:any}} = {
  "dev": {
    "SESSION_COOKIE_SECURE": false,
    "DEBUG": true,
    "TEMPLATES_AUTO_RELOAD": true,
    "SEND_FILE_MAX_AGE_DEFAULT": 300,
    "PERMANENT_SESSION_LIFETIME": 86400, // 1 day
    "SERVER_NAME": "localhost:5000",
    "ROOT_LOG_LEVEL": "DEBUG"
  },
  'staging': {
    "SESSION_COOKIE_SECURE": true,
    "DEBUG": false,
    "TEMPLATES_AUTO_RELOAD": false,
    "SEND_FILE_MAX_AGE_DEFAULT": 300,
    "PERMANENT_SESSION_LIFETIME": 86400, // 1 day,
    "ROOT_LOG_LEVEL": "DEBUG"
  },
  "prod": {
    "SESSION_COOKIE_SECURE": true,
    "DEBUG": false,
    "TEMPLATES_AUTO_RELOAD": false,
    "SEND_FILE_MAX_AGE_DEFAULT": 300,
    "PERMANENT_SESSION_LIFETIME": 86400, // 1 day
    "ROOT_LOG_LEVEL": "INFO"
  }
};


export class StockTradeCdKappStack extends cdk.Stack {
  constructor(scope: Construct, id: string, props?: cdk.StackProps) {
    super(scope, id, props);

    const stageName = this.node.tryGetContext("stage") as string;
    
    // S3 bucket for storing flask session secret key and Sqlite db
    let appStore = new s3.Bucket(this, "S3Storage", {
      blockPublicAccess: BlockPublicAccess.BLOCK_ALL,
      removalPolicy: RemovalPolicy.RETAIN,
      encryption: BucketEncryption.S3_MANAGED,
      bucketName: `${this.account}-stock-trade-s3storage-${stageName}`
    });

    // IAM role for lambda which grants access to logs and cloudwatch metrics
    //  and can be used later to grant lambda r/w permissions to other resources
    let lambdaRole = new iam.Role(this, "LambdaRole", {
      assumedBy: new iam.ServicePrincipal("lambda.amazonaws.com"),
      inlinePolicies: {
        "lambda-executor": new iam.PolicyDocument({
          assignSids: true,
          statements: [
            new iam.PolicyStatement({
              effect: iam.Effect.ALLOW,
              actions: ["ec2:DescribeTags",
                "cloudwatch:GetMetricStatistics",
                "cloudwatch:ListMetrics",
                "logs:CreateLogGroup",
                "logs:CreateLogStream",
                "logs:PutLogEvents",
                "logs:DescribeLogStreams"],
              resources: ["*"]
            }),
            new iam.PolicyStatement({
              effect: iam.Effect.ALLOW,
              actions: ["lambda:InvokeFunction"],
              resources: ["*"]
            })
          ]
        })
      }
    });

    let lambdaEnv = LAMBDA_CONFIG_ENV[stageName];
    lambdaEnv["S3_BUCKET"] = appStore.bucketName;

    let webappLambda = new lambda.Function(this, "StockTradeLambda", {
      functionName: `stock-trade-lambda-${stageName}`,
      code: lambda.Code.fromAsset(__dirname + "/../build-python",), // created in Makefile
      runtime: lambda.Runtime.PYTHON_3_9,
      handler: "serverless_flask.lambda.lambda_handler",
      role: lambdaRole,
      timeout: Duration.seconds(30),
      memorySize: 256,
      environment: {"JSON_CONFIG_OVERRIDE": JSON.stringify(lambdaEnv)},
      // logRetention: logs.RetentionDays.SIX_MONTHS, // default is infinite
    });
  }
}


