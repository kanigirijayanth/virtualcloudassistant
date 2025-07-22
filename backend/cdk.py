#!/usr/bin/env python3
# /*********************************************************************************************************************
# *  Copyright 2025 Amazon.com, Inc. or its affiliates. All Rights Reserved.                                           *
# *                                                                                                                    *
# *  Licensed under the Amazon Software License (the "License"). You may not use this file except in compliance        *
# *  with the License. A copy of the License is located at                                                             *
# *                                                                                                                    *
# *      http://aws.amazon.com/asl/                                                                                    *
# *                                                                                                                    *
# *  or in the "license" file accompanying this file. This file is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES *
# *  OR CONDITIONS OF ANY KIND, express or implied. See the License for the specific language governing permissions    *
# *  and limitations under the License.                                                                                *
# **********************************************************************************************************************/

"""
AWS CDK Application Entry Point

This module serves as the entry point for the AWS CDK application. It initializes and
configures the CDK stack for deployment. The stack can be environment-agnostic or
configured for specific AWS accounts and regions.

The application uses environment variables CDK_DEFAULT_ACCOUNT and CDK_DEFAULT_REGION
to determine the deployment target, making it flexible for different deployment
environments.

Usage:
    cdk deploy       # Deploy the stack to AWS
    cdk synth       # Synthesize CloudFormation template
    cdk destroy     # Remove the stack from AWS

Environment Variables:
    CDK_DEFAULT_ACCOUNT: AWS account ID for deployment
    CDK_DEFAULT_REGION: AWS region for deployment
"""

import os

import aws_cdk as cdk
from cdk_nag import AwsSolutionsChecks

from cdk_stack import CdkStack

# Initialize the CDK application
app = cdk.App()

# Add the cdk-nag AwsSolutions Pack with extra verbose logging enabled
cdk.Aspects.of(app).add(AwsSolutionsChecks(verbose=True))

# Create the Virtual Banking Assistant stack
# The stack can be environment-agnostic (deploy anywhere) or environment-specific
CdkStack(app, "VirtualBankingAssistantCdkStack",
    # If you don't specify 'env', this stack will be environment-agnostic.
    # Account/Region-dependent features and context lookups will not work,
    # but a single synthesized template can be deployed anywhere.

    # For environment-specific deployment, use the current CLI configuration
    env=cdk.Environment(
        account=os.getenv('CDK_DEFAULT_ACCOUNT'), 
        region=os.getenv('CDK_DEFAULT_REGION')
    ),

    description='Virtual Banking Assistant (uksb-ybsvnefrsb)'

    # For explicit account/region deployment, uncomment and modify:
    # env=cdk.Environment(account='123456789012', region='us-east-1'),

    # For more information on environments, see:
    # https://docs.aws.amazon.com/cdk/latest/guide/environments.html
)

# Optional: Add AWS Solutions security checks
# Uncomment to enable detailed security analysis during synthesis
# cdk.Aspects.of(app).add(AwsSolutionsChecks(verbose=True))

# Synthesize the CloudFormation template
app.synth()
