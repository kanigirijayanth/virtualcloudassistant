#!/usr/bin/env python3
"""
Test script for Bedrock Knowledge Base connectivity
This script tests the connection to the Bedrock Knowledge Base and performs a simple query
to verify that the knowledge base is accessible and functioning correctly.
"""

import boto3
import json
import os
import time
import traceback

# Knowledge Base ID from your application
KNOWLEDGE_BASE_ID = "CLRDOVZGIY"

# Model ID for response generation - using Nova Lite
NOVA_LITE_MODEL_ID = "amazon.nova-lite-v1:0"

def refresh_credentials():
    """
    Refreshes the AWS credentials from the ECS container metadata endpoint.
    """
    try:
        uri = os.environ.get("AWS_CONTAINER_CREDENTIALS_RELATIVE_URI")
        if uri:
            print("Fetching fresh AWS credentials from ECS metadata endpoint")
            import httpx
            with httpx.Client() as client:
                response = client.get(f"http://169.254.170.2{uri}")
                if response.status_code == 200:
                    creds = response.json()
                    os.environ["AWS_ACCESS_KEY_ID"] = creds["AccessKeyId"]
                    os.environ["AWS_SECRET_ACCESS_KEY"] = creds["SecretAccessKey"]
                    os.environ["AWS_SESSION_TOKEN"] = creds["Token"]
                    print("AWS credentials refreshed successfully")
                    return True
                else:
                    print(f"Failed to fetch credentials: {response.status_code}")
                    return False
        else:
            print("No AWS_CONTAINER_CREDENTIALS_RELATIVE_URI found, using existing credentials")
            return True
    except Exception as e:
        print(f"Error refreshing credentials: {str(e)}")
        traceback.print_exc()
        return False

def test_list_knowledge_bases():
    """
    Tests knowledge base connectivity by directly querying it.
    """
    try:
        print("
=== Testing Knowledge Base Connectivity ===")
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
        return False

def test_query_knowledge_base(query="What are the backup procedures?"):
    """
    Tests querying the knowledge base with a simple question.
    """
    try:
        print(f"\n=== Testing Knowledge Base Query: '{query}' ===")
        bedrock_agent_runtime = boto3.client(
            service_name='bedrock-agent-runtime',
            region_name='us-east-1'
        )
        
        print(f"Retrieving from knowledge base ID: {KNOWLEDGE_BASE_ID}")
        start_time = time.time()
        
        # Retrieve documents from the knowledge base
        retrieval_response = bedrock_agent_runtime.retrieve(
            knowledgeBaseId=KNOWLEDGE_BASE_ID,
            retrievalQuery={
                'text': query
            },
            retrievalConfiguration={
                'vectorSearchConfiguration': {
                    'numberOfResults': 3
                }
            }
        )
        
        retrieval_time = time.time() - start_time
        results = retrieval_response.get('retrievalResults', [])
        print(f"Success! Retrieved {len(results)} documents in {retrieval_time:.2f} seconds")
        
        # Print the results
        if results:
            print("\nResults:")
            for i, result in enumerate(results):
                content = result.get('content', {}).get('text', '')
                source = result.get('location', {}).get('s3Location', {}).get('uri', '')
                score = result.get('score', 0)
                
                print(f"\n--- Result {i+1} (Score: {score:.4f}) ---")
                print(f"Source: {source}")
                print(f"Content: {content[:200]}...")
            
            return True
        else:
            print("No results found for the query.")
            return False
            
    except Exception as e:
        print(f"Error querying knowledge base: {str(e)}")
        traceback.print_exc()
        return False

def test_nova_lite_generation(query="What are the backup procedures?", context="Regular backups are performed daily at midnight. Full backups are done weekly on Sundays."):
    """
    Tests generating a response using Nova Lite model.
    """
    try:
        print("\n=== Testing Nova Lite Response Generation ===")
        bedrock_runtime = boto3.client(
            service_name='bedrock-runtime',
            region_name='us-east-1'
        )
        
        # Prepare prompt for Nova Lite
        prompt = f"""
        You are a Virtual Cloud Assistant that provides information from documentation.
        
        User Query: {query}
        
        Here is the relevant document I found:
        {context}
        
        Based ONLY on the information in this document, provide a comprehensive answer to the user's query.
        """
        
        print("Calling Nova Lite model...")
        start_time = time.time()
        
        # Call Nova Lite to generate a response
        generation_response = bedrock_runtime.invoke_model(
            modelId=NOVA_LITE_MODEL_ID,
            body=json.dumps({
                "messages": [
                    {
                        "role": "user", 
                        "content": [
                            {"text": prompt}
                        ]
                    }
                ]
            })
        )
        
        # Parse the response
        response_body = json.loads(generation_response['body'].read().decode('utf-8'))
        generated_answer = response_body.get('output', {}).get('message', {}).get('content', [{}])[0].get('text', '')
        
        generation_time = time.time() - start_time
        print(f"Success! Generated response in {generation_time:.2f} seconds")
        print(f"\nGenerated Answer:\n{generated_answer}")
        
        return True
        
    except Exception as e:
        print(f"Error generating response with Nova Lite: {str(e)}")
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
    
    # Check boto3 version
    import boto3
    print(f"boto3 version: {boto3.__version__}")

def main():
    """
    Main function to run all tests.
    """
    print("=== Bedrock Knowledge Base Connectivity Test ===")
    print(f"Knowledge Base ID: {KNOWLEDGE_BASE_ID}")
    print(f"Nova Lite Model ID: {NOVA_LITE_MODEL_ID}")
    
    # Print environment information
    print_environment_info()
    
    # Refresh credentials
    if not refresh_credentials():
        print("\n❌ Failed to refresh credentials. Tests may fail.")
    
    # Test listing knowledge bases
    kb_exists = test_list_knowledge_bases()
    
    # Only proceed with query test if knowledge base exists
    if kb_exists:
        query_success = test_query_knowledge_base()
        if not query_success:
            print("\n❌ Knowledge base query test failed.")
        
        # Test Nova Lite generation
        generation_success = test_nova_lite_generation()
        if not generation_success:
            print("\n❌ Nova Lite generation test failed.")
    else:
        print("\n❌ Knowledge base not found. Skipping query and generation tests.")
    
    print("\n=== Test Summary ===")
    print(f"Knowledge Base Exists: {'✓' if kb_exists else '✗'}")
    if kb_exists:
        print(f"Query Test: {'✓' if query_success else '✗'}")
        print(f"Nova Lite Generation: {'✓' if generation_success else '✗'}")
    
    print("\nIf any tests failed, check the error messages above for details.")
    print("Make sure your IAM permissions, knowledge base ID, and region settings are correct.")

if __name__ == "__main__":
    main()
