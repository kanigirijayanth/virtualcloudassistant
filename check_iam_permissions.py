#!/usr/bin/env python3
"""
Script to check IAM permissions for ECS task role
This script checks if the current IAM role has the necessary permissions
for accessing Bedrock Knowledge Base and Nova Sonic.
"""

import boto3
import json
import os
import traceback
from botocore.exceptions import ClientError

def get_current_identity():
    """
    Gets information about the current IAM identity.
    """
    try:
        print("=== Current Identity Information ===")
        sts_client = boto3.client('sts')
        identity = sts_client.get_caller_identity()
        
        print(f"Account ID: {identity['Account']}")
        print(f"User/Role ARN: {identity['Arn']}")
        print(f"User/Role ID: {identity['UserId']}")
        
        # Extract role name if this is a role
        if ':assumed-role/' in identity['Arn']:
            role_name = identity['Arn'].split(':assumed-role/')[1].split('/')[0]
            print(f"Role Name: {role_name}")
            return role_name
        elif ':role/' in identity['Arn']:
            role_name = identity['Arn'].split(':role/')[1]
            print(f"Role Name: {role_name}")
            return role_name
        else:
            print("Not running as a role")
            return None
    except Exception as e:
        print(f"Error getting identity: {str(e)}")
        traceback.print_exc()
        return None

def check_bedrock_permissions():
    """
    Checks if the current role has permissions to access Bedrock services.
    """
    print("\n=== Checking Bedrock Permissions ===")
    
    # List of permissions to check
    permissions_to_check = [
        "bedrock:ListFoundationModels",
        "bedrock-runtime:InvokeModel",
        "bedrock-agent-runtime:Retrieve",
        "bedrock-agent-runtime:ListKnowledgeBases"
    ]
    
    try:
        # Create IAM client
        iam_client = boto3.client('iam')
        
        # Get current role name
        role_name = get_current_identity()
        if not role_name:
            print("Could not determine role name. Skipping permission check.")
            return
        
        print(f"Checking permissions for role: {role_name}")
        
        # Simulate policy evaluation
        for permission in permissions_to_check:
            try:
                service, action = permission.split(':')
                response = iam_client.simulate_principal_policy(
                    PolicySourceArn=f"arn:aws:iam::{boto3.client('sts').get_caller_identity()['Account']}:role/{role_name}",
                    ActionNames=[permission]
                )
                
                # Check evaluation result
                result = response['EvaluationResults'][0]
                decision = result['EvalDecision']
                
                if decision == 'allowed':
                    print(f"✓ {permission}: Allowed")
                else:
                    print(f"✗ {permission}: Denied - {result.get('EvalDecisionDetails', {})}")
            except Exception as e:
                print(f"✗ {permission}: Error checking permission - {str(e)}")
    except Exception as e:
        print(f"Error checking permissions: {str(e)}")
        traceback.print_exc()

def test_bedrock_access():
    """
    Tests actual access to Bedrock services.
    """
    print("\n=== Testing Actual Bedrock Access ===")
    
    # Test bedrock-runtime:InvokeModel
    try:
        print("\nTesting bedrock-runtime:InvokeModel...")
        bedrock_runtime = boto3.client('bedrock-runtime', region_name='us-east-1')
        
        # Just check if we can list models (doesn't actually invoke)
        bedrock = boto3.client('bedrock', region_name='us-east-1')
        response = bedrock.list_foundation_models(maxResults=10)
        print(f"✓ Successfully listed foundation models: {len(response.get('modelSummaries', []))} models found")
    except ClientError as e:
        error_code = e.response.get('Error', {}).get('Code', 'Unknown')
        error_message = e.response.get('Error', {}).get('Message', 'Unknown error')
        print(f"✗ Error accessing bedrock-runtime: {error_code} - {error_message}")
    except Exception as e:
        print(f"✗ Error accessing bedrock-runtime: {str(e)}")
    
    # Test bedrock-agent-runtime:ListKnowledgeBases
    try:
        print("\nTesting bedrock-agent-runtime:ListKnowledgeBases...")
        bedrock_agent_runtime = boto3.client('bedrock-agent-runtime', region_name='us-east-1')
        response = bedrock_agent_runtime.list_knowledge_bases(maxResults=10)
        print(f"✓ Successfully listed knowledge bases: {len(response.get('knowledgeBaseSummaries', []))} knowledge bases found")
    except ClientError as e:
        error_code = e.response.get('Error', {}).get('Code', 'Unknown')
        error_message = e.response.get('Error', {}).get('Message', 'Unknown error')
        print(f"✗ Error accessing bedrock-agent-runtime: {error_code} - {error_message}")
    except Exception as e:
        print(f"✗ Error accessing bedrock-agent-runtime: {str(e)}")

def check_environment_variables():
    """
    Checks if necessary environment variables are set.
    """
    print("\n=== Checking Environment Variables ===")
    
    # Variables to check
    variables = [
        "AWS_REGION",
        "AWS_DEFAULT_REGION",
        "AWS_ACCESS_KEY_ID",
        "AWS_SECRET_ACCESS_KEY",
        "AWS_SESSION_TOKEN",
        "AWS_CONTAINER_CREDENTIALS_RELATIVE_URI"
    ]
    
    for var in variables:
        value = os.environ.get(var)
        if value:
            if var in ["AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY", "AWS_SESSION_TOKEN"]:
                print(f"✓ {var}: Set (value hidden)")
            else:
                print(f"✓ {var}: {value}")
        else:
            print(f"✗ {var}: Not set")

def main():
    """
    Main function to run all checks.
    """
    print("=== IAM Permission Check for Bedrock Knowledge Base ===")
    
    # Check environment variables
    check_environment_variables()
    
    # Get current identity
    get_current_identity()
    
    # Check permissions
    check_bedrock_permissions()
    
    # Test actual access
    test_bedrock_access()
    
    print("\n=== Recommendations ===")
    print("If any permissions are missing, update the IAM role with the following policy:")
    print("""
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "bedrock:ListFoundationModels",
                "bedrock-runtime:InvokeModel",
                "bedrock-agent-runtime:Retrieve",
                "bedrock-agent-runtime:ListKnowledgeBases"
            ],
            "Resource": "*"
        }
    ]
}
    """)
    print("You can use the update-iam-policy.sh script in your project to update the policy.")

if __name__ == "__main__":
    main()
