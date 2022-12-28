#!/usr/bin/env node
import 'source-map-support/register';
import * as cdk from 'aws-cdk-lib';
import { StockTradeCdKappStack } from '../lib/stock_trade-cdk_app-stack';

const app = new cdk.App();

// Find what stage the app is in and name the stack based on that
const stackName = ({
  "dev": "serverless-stock-trade-dev",
  "staging": "serverless-stock-trade-staging",
  "prod": "serverless-stock-trade-prod"
} as Record<string, string>)[app.node.tryGetContext("stage") as string];

new StockTradeCdKappStack(app, 'StockTradeCdkappStack', {
  /* If you don't specify 'env', this stack will be environment-agnostic.
   * Account/Region-dependent features and context lookups will not work,
   * but a single synthesized template can be deployed anywhere. */

  /* Uncomment the next line to specialize this stack for the AWS Account
   * and Region that are implied by the current CLI configuration. */
  // env: { account: process.env.CDK_DEFAULT_ACCOUNT, region: process.env.CDK_DEFAULT_REGION },

  /* Uncomment the next line if you know exactly what Account and Region you
   * want to deploy the stack to. */
  // env: { account: '123456789012', region: 'us-east-1' },

  /* For more information, see https://docs.aws.amazon.com/cdk/latest/guide/environments.html */
});