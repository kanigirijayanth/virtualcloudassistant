#!/bin/bash

# Get the ECS task role ARN
TASK_ROLE_ARN=$(aws ecs describe-task-definition --task-definition VirtualClouldAssistantCdkStack-VirtualCloudAssistantTaskDef --query 'taskDefinition.taskRoleArn' --output text)

if [ -z "$TASK_ROLE_ARN" ]; then
    echo "Failed to get task role ARN"
    exit 1
fi

# Extract the role name from the ARN
ROLE_NAME=$(echo $TASK_ROLE_ARN | awk -F'/' '{print $NF}')

echo "Updating IAM policy for role: $ROLE_NAME"

# Create a policy document
cat > bedrock-kb-policy.json << EOF
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "bedrock:InvokeModel",
                "bedrock-runtime:InvokeModel"
            ],
            "Resource": [
                "arn:aws:bedrock:us-east-1::foundation-model/amazon.nova-lite-v1"
            ]
        },
        {
            "Effect": "Allow",
            "Action": [
                "bedrock-agent-runtime:Retrieve",
                "bedrock-agent-runtime:RetrieveAndGenerate"
            ],
            "Resource": [
                "arn:aws:bedrock:us-east-1:*:knowledge-base/CLRDOVZGIY"
            ]
        }
    ]
}
EOF

# Attach the policy to the role
aws iam put-role-policy --role-name $ROLE_NAME --policy-name BedrockKnowledgeBaseAccess --policy-document file://bedrock-kb-policy.json

echo "IAM policy updated successfully"
