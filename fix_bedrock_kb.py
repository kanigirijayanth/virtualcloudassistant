#!/usr/bin/env python3
"""
Script to fix the Bedrock knowledge base API issue
This script updates the bedrock_kb_functions.py file to avoid using the list_knowledge_bases method
that doesn't exist in the current boto3 version.
"""

import os
import re
import shutil
import sys

def backup_file(file_path):
    """Create a backup of the file"""
    backup_path = file_path + '.bak'
    shutil.copy2(file_path, backup_path)
    print(f"Created backup at {backup_path}")

def update_refresh_bedrock_clients(content):
    """Update the refresh_bedrock_clients function to use direct retrieve call instead of list_knowledge_bases"""
    # Find the refresh_bedrock_clients function
    pattern = r'def refresh_bedrock_clients\(\):.*?try:.*?# Test the clients.*?except Exception as e:.*?print\(f"WARNING: Bedrock client test failed: {str\(e\)}"\)'
    pattern = re.compile(pattern, re.DOTALL)
    
    # New implementation that avoids list_knowledge_bases
    replacement = """def refresh_bedrock_clients():
    \"\"\"
    Refreshes the Bedrock clients with the latest credentials.
    This ensures that the clients have valid credentials when making API calls.
    \"\"\"
    try:
        print("Refreshing Bedrock clients with latest credentials")
        global bedrock_runtime, bedrock_agent_runtime
        
        # Get credentials from environment variables
        access_key = os.environ.get("AWS_ACCESS_KEY_ID")
        secret_key = os.environ.get("AWS_SECRET_ACCESS_KEY")
        session_token = os.environ.get("AWS_SESSION_TOKEN")
        
        if not access_key or not secret_key:
            print("WARNING: Missing AWS credentials for Bedrock clients")
            return
            
        # Create new clients with the latest credentials
        bedrock_runtime = boto3.client(
            service_name='bedrock-runtime',
            region_name='us-east-1',
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
            aws_session_token=session_token
        )
        
        bedrock_agent_runtime = boto3.client(
            service_name='bedrock-agent-runtime',
            region_name='us-east-1',
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
            aws_session_token=session_token
        )
        
        print("Bedrock clients refreshed successfully")
        
        # Test the clients to ensure they're working - use a direct retrieve call instead
        try:
            # Instead of listing knowledge bases, directly test with a retrieve call
            print(f"Testing Bedrock agent runtime with knowledge base ID: {KNOWLEDGE_BASE_ID}")
            test_query = "test query"
            response = bedrock_agent_runtime.retrieve(
                knowledgeBaseId=KNOWLEDGE_BASE_ID,
                retrievalQuery={
                    'text': test_query
                },
                retrievalConfiguration={
                    'vectorSearchConfiguration': {
                        'numberOfResults': 1
                    }
                }
            )
            
            results_count = len(response.get('retrievalResults', []))
            print(f"Bedrock agent runtime test successful. Retrieved {results_count} results")
            
            if results_count > 0:
                print(f"Knowledge base {KNOWLEDGE_BASE_ID} is working correctly")
            else:
                print(f"Knowledge base {KNOWLEDGE_BASE_ID} returned no results for test query")
                
        except Exception as e:
            print(f"WARNING: Bedrock client test failed: {str(e)}")"""
    
    # Replace the function
    updated_content = pattern.sub(replacement, content)
    return updated_content

def update_test_bedrock_kb():
    """Update the test_bedrock_kb.py file to use direct retrieve call instead of list_knowledge_bases"""
    test_file_path = "/root/aws/ciscld/voicebot/virtualcloudassistant/test_bedrock_kb.py"
    
    if not os.path.exists(test_file_path):
        print(f"Test file {test_file_path} not found, skipping update")
        return
    
    with open(test_file_path, 'r') as f:
        content = f.read()
    
    # Find the test_list_knowledge_bases function
    pattern = r'def test_list_knowledge_bases\(\):.*?try:.*?response = bedrock_agent_runtime\.list_knowledge_bases.*?return False'
    pattern = re.compile(pattern, re.DOTALL)
    
    # New implementation that avoids list_knowledge_bases
    replacement = """def test_list_knowledge_bases():
    \"\"\"
    Tests knowledge base connectivity by directly querying it.
    \"\"\"
    try:
        print("\\n=== Testing Knowledge Base Connectivity ===")
        bedrock_agent_runtime = boto3.client(
            service_name='bedrock-agent-runtime',
            region_name='us-east-1'
        )
        
        # Instead of listing knowledge bases, directly test with a retrieve call
        test_query = "test query"
        response = bedrock_agent_runtime.retrieve(
            knowledgeBaseId=KNOWLEDGE_BASE_ID,
            retrievalQuery={
                'text': test_query
            },
            retrievalConfiguration={
                'vectorSearchConfiguration': {
                    'numberOfResults': 1
                }
            }
        )
        
        results_count = len(response.get('retrievalResults', []))
        print(f"Success! Retrieved {results_count} results from knowledge base {KNOWLEDGE_BASE_ID}")
        
        if results_count > 0:
            print(f"  ✓ Knowledge base {KNOWLEDGE_BASE_ID} is working correctly")
            return True
        else:
            print(f"  ⚠️ Knowledge base {KNOWLEDGE_BASE_ID} returned no results for test query")
            print("  This could be normal if the knowledge base is empty or the query doesn't match any content")
            return True  # Still return true since the API call worked
            
    except Exception as e:
        print(f"Error testing knowledge base: {str(e)}")
        traceback.print_exc()
        return False"""
    
    # Replace the function
    updated_content = pattern.sub(replacement, content)
    
    # Backup the file
    backup_file(test_file_path)
    
    # Write the updated content
    with open(test_file_path, 'w') as f:
        f.write(updated_content)
    
    print(f"Updated {test_file_path}")

def main():
    """Main function to update the files"""
    # Path to the bedrock_kb_functions.py file
    file_path = "/root/aws/ciscld/voicebot/virtualcloudassistant/backend/app/bedrock_kb_functions.py"
    
    if not os.path.exists(file_path):
        print(f"File {file_path} not found")
        sys.exit(1)
    
    # Read the file
    with open(file_path, 'r') as f:
        content = f.read()
    
    # Backup the file
    backup_file(file_path)
    
    # Update the refresh_bedrock_clients function
    updated_content = update_refresh_bedrock_clients(content)
    
    # Write the updated content
    with open(file_path, 'w') as f:
        f.write(updated_content)
    
    print(f"Updated {file_path}")
    
    # Update the test_bedrock_kb.py file
    update_test_bedrock_kb()
    
    print("Fix completed. Please redeploy the application using deploy_kb_fix.sh")

if __name__ == "__main__":
    main()
