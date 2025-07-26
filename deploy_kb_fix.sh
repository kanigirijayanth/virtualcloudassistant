#!/bin/bash
# Script to deploy the knowledge base fix to the ECS service

# Set variables
echo "Setting up variables..."
REGION=$(aws configure get region)
if [ -z "$REGION" ]; then
  REGION="us-east-1"  # Default region
fi
echo "Using AWS region: $REGION"

# Build and deploy the backend
echo "Building and deploying the backend..."
cd /root/aws/ciscld/voicebot/virtualcloudassistant/backend
source ~/venv/bin/activate
cdk deploy

# Get the ECS cluster and service names
echo "Getting ECS cluster and service information..."
CLUSTER_NAME=$(aws ecs list-clusters --region $REGION --query 'clusterArns[0]' --output text | awk -F'/' '{print $2}')
SERVICE_NAME=$(aws ecs list-services --cluster $CLUSTER_NAME --region $REGION --query 'serviceArns[0]' --output text | awk -F'/' '{print $3}')

if [ -z "$CLUSTER_NAME" ] || [ -z "$SERVICE_NAME" ]; then
  echo "Error: Could not determine ECS cluster or service name."
  echo "Please manually update the ECS service to pick up the changes."
  exit 1
fi

echo "Found ECS cluster: $CLUSTER_NAME"
echo "Found ECS service: $SERVICE_NAME"

# Force a new deployment of the ECS service
echo "Forcing a new deployment of the ECS service..."
aws ecs update-service --cluster $CLUSTER_NAME --service $SERVICE_NAME --force-new-deployment --region $REGION

echo "Deployment initiated. The changes should be applied within a few minutes."
echo "You can monitor the deployment status in the AWS ECS console."
echo ""
echo "After deployment completes, test the knowledge base queries with questions like:"
echo "  - 'What are the backup procedures?'"
echo "  - 'Tell me about the disaster recovery plan'"
echo "  - 'How do we handle incidents?'"
echo ""
echo "Check the CloudWatch logs for entries like 'KNOWLEDGE BASE QUERY CALLED' to confirm the functions are being called."
