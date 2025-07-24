#!/bin/bash

# Virtual Cloud Assistant Deployment Script
# This script deploys the updated Virtual Cloud Assistant with Bedrock Knowledge Base integration

set -e

echo "Starting deployment of Virtual Cloud Assistant..."

# Activate virtual environment
source ~/venv/bin/activate

# Deploy backend
echo "Deploying backend..."
cd backend
python -m pip install -r requirements.txt
cdk deploy

# Get outputs from CDK deployment
BUCKET_NAME=$(aws cloudformation describe-stacks --stack-name VirtualCloudAssistantStack --query "Stacks[0].Outputs[?OutputKey=='FrontendBucket'].OutputValue" --output text)
CLOUDFRONT_URL=$(aws cloudformation describe-stacks --stack-name VirtualCloudAssistantStack --query "Stacks[0].Outputs[?OutputKey=='CloudFrontURL'].OutputValue" --output text)

echo "Frontend bucket: $BUCKET_NAME"
echo "CloudFront URL: $CLOUDFRONT_URL"

# Build and deploy frontend
echo "Building and deploying frontend..."
cd ../frontend/react-web
npm install
npm run build

# Upload to S3
echo "Uploading to S3 bucket: $BUCKET_NAME"
aws s3 cp build s3://$BUCKET_NAME --recursive

# Create CloudFront invalidation
echo "Creating CloudFront invalidation..."
DISTRIBUTION_ID=$(echo $CLOUDFRONT_URL | sed 's/https:\/\///g' | sed 's/\.cloudfront\.net//g')
aws cloudfront create-invalidation --distribution-id $DISTRIBUTION_ID --paths "/*"

echo "Deployment complete!"
echo "You can access the application at: $CLOUDFRONT_URL"
echo ""
echo "Note: It may take a few minutes for the CloudFront invalidation to complete."
