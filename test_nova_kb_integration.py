#!/usr/bin/env python3
"""
Test script for Nova Sonic integration with Bedrock Knowledge Base
This script tests the integration between Nova Sonic and the Bedrock Knowledge Base
by simulating a function call to the knowledge base query function.
"""

import os
import json
import boto3
import traceback
from bedrock_kb_functions import query_knowledge_base, refresh_bedrock_clients

def test_function_call_simulation():
    """
    Simulates a function call from Nova Sonic to the knowledge base query function.
    This helps verify that the function registration and calling mechanism works.
    """
    print("\n=== Testing Function Call Simulation ===")
    
    # Sample query that would come from Nova Sonic
    test_query = "What are the backup procedures for the database?"
    
    try:
        print(f"Simulating function call with query: '{test_query}'")
        
        # Refresh Bedrock clients to ensure we have valid credentials
        refresh_bedrock_clients()
        
        # Call the knowledge base query function directly
        result = query_knowledge_base(test_query, max_results=3)
        
        # Print the result status
        print(f"Function call result status: {result.get('status')}")
        
        # Check if we got a successful response
        if result.get('status') == 'success':
            print("✓ Knowledge base query function call successful!")
            
            # Print the generated answer if available
            if 'generated_answer' in result:
                print("\nGenerated Answer:")
                print(result['generated_answer'][:500] + "..." if len(result['generated_answer']) > 500 else result['generated_answer'])
            
            # Print information about the retrieved documents
            print(f"\nRetrieved {len(result.get('results', []))} documents")
            for i, doc in enumerate(result.get('results', [])[:2]):  # Show first 2 documents
                print(f"\n--- Document {i+1} ---")
                print(f"Source: {doc.get('source', 'Unknown')}")
                content = doc.get('content', '')
                print(f"Content: {content[:200]}..." if len(content) > 200 else content)
            
            return True
        else:
            print(f"✗ Knowledge base query function call failed: {result.get('message', 'Unknown error')}")
            return False
            
    except Exception as e:
        print(f"Error in function call simulation: {str(e)}")
        traceback.print_exc()
        return False

def test_wrapped_function():
    """
    Tests the wrapped function that would be registered with Nova Sonic.
    This simulates how the function would be called in the actual application.
    """
    print("\n=== Testing Wrapped Function ===")
    
    # Define a wrapper function similar to what's in main.py
    def wrapped_query_knowledge_base(query, max_results=5):
        try:
            print(f"Wrapped function called with query: '{query}'")
            refresh_bedrock_clients()  # Refresh credentials before calling
            result = query_knowledge_base(query, max_results)
            print(f"Wrapped function result status: {result.get('status')}")
            return result
        except Exception as e:
            print(f"ERROR in wrapped function: {str(e)}")
            traceback.print_exc()
            return {
                'status': 'error',
                'message': f"Knowledge base query failed: {str(e)}",
                'query': query,
                'results': []
            }
    
    # Test query
    test_query = "What is the disaster recovery plan?"
    
    try:
        print(f"Testing wrapped function with query: '{test_query}'")
        result = wrapped_query_knowledge_base(test_query, 3)
        
        if result.get('status') == 'success':
            print("✓ Wrapped function call successful!")
            return True
        else:
            print(f"✗ Wrapped function call failed: {result.get('message', 'Unknown error')}")
            return False
    except Exception as e:
        print(f"Error in wrapped function test: {str(e)}")
        traceback.print_exc()
        return False

def print_environment_info():
    """
    Prints information about the environment for debugging.
    """
    print("\n=== Environment Information ===")
    print(f"AWS_REGION: {os.environ.get('AWS_REGION', 'Not set')}")
    print(f"AWS_DEFAULT_REGION: {os.environ.get('AWS_DEFAULT_REGION', 'Not set')}")
    
    # Check if credentials are set (don't print the actual values)
    access_key = os.environ.get("AWS_ACCESS_KEY_ID")
    secret_key = os.environ.get("AWS_SECRET_ACCESS_KEY")
    session_token = os.environ.get("AWS_SESSION_TOKEN")
    
    print(f"AWS_ACCESS_KEY_ID: {'Set' if access_key else 'Not set'}")
    print(f"AWS_SECRET_ACCESS_KEY: {'Set' if secret_key else 'Not set'}")
    print(f"AWS_SESSION_TOKEN: {'Set' if session_token else 'Not set'}")
    print(f"AWS_CONTAINER_CREDENTIALS_RELATIVE_URI: {os.environ.get('AWS_CONTAINER_CREDENTIALS_RELATIVE_URI', 'Not set')}")

def main():
    """
    Main function to run all tests.
    """
    print("=== Nova Sonic Knowledge Base Integration Test ===")
    
    # Print environment information
    print_environment_info()
    
    # Test direct function call
    direct_call_success = test_function_call_simulation()
    
    # Test wrapped function
    wrapped_call_success = test_wrapped_function()
    
    print("\n=== Test Summary ===")
    print(f"Direct Function Call: {'✓' if direct_call_success else '✗'}")
    print(f"Wrapped Function Call: {'✓' if wrapped_call_success else '✗'}")
    
    if not direct_call_success or not wrapped_call_success:
        print("\nPossible issues:")
        print("1. IAM permissions - Make sure your ECS task role has bedrock-agent-runtime:Retrieve and bedrock-runtime:InvokeModel permissions")
        print("2. Knowledge Base ID - Verify the ID in bedrock_kb_functions.py")
        print("3. Region configuration - Make sure your knowledge base is in us-east-1 or update the region in the code")
        print("4. Nova Lite model access - Ensure your account has access to amazon.nova-lite-v1:0")
        print("5. Credentials - Check if the credentials are being properly refreshed in the ECS environment")

if __name__ == "__main__":
    main()
