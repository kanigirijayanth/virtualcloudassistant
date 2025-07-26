#!/usr/bin/env python3
"""
Test function to check knowledge base request with the query about incident ticket creation
This script makes a request to the existing Bedrock knowledge base CLRDOVZGIY and displays the exact response.
"""

import json
import sys
import boto3
import time

def test_knowledge_base_request():
    """
    Function to test knowledge base request and print the exact response from Bedrock knowledge base
    """
    # Knowledge base ID
    knowledge_base_id = "CLRDOVZGIY"
    
    # Query to test
    query = "under Initial Alert Reception and Acknowledgment, how to create incident ticket"
    
    print(f"Testing Bedrock knowledge base request on knowledge base ID: {knowledge_base_id}")
    print(f"Query: '{query}'")
    print("-" * 50)
    
    try:
        # Initialize the Bedrock Agent Runtime client
        bedrock_agent_runtime = boto3.client('bedrock-agent-runtime')
        
        start_time = time.time()
        
        print(f"Sending request with query: '{query}'")
        print("Processing request...")
        
        # Make the actual API call to retrieve information from the Bedrock knowledge base
        response = bedrock_agent_runtime.retrieve(
            knowledgeBaseId=knowledge_base_id,
            retrievalQuery={
                'text': query
            },
            retrievalConfiguration={
                'vectorSearchConfiguration': {
                    'numberOfResults': 5
                }
            }
        )
        
        # Calculate processing time
        end_time = time.time()
        processing_time = end_time - start_time
        
        # Print the raw response
        print("\nRAW RESPONSE:")
        print("-" * 50)
        print(response)
        
        # Print the formatted response for better readability
        print("\nFORMATTED RESPONSE:")
        print("-" * 50)
        
        if 'retrievalResults' in response:
            print(f"Number of results: {len(response['retrievalResults'])}")
            
            for i, result in enumerate(response['retrievalResults'], 1):
                print(f"\nResult {i}:")
                
                if 'content' in result and 'text' in result['content']:
                    print(f"Content: {result['content']['text']}")
                
                if 'documentMetadata' in result:
                    metadata = result['documentMetadata']
                    print(f"Source: {metadata.get('source', 'Unknown source')}")
                    print(f"Document ID: {metadata.get('documentId', 'No ID')}")
                
                if 'score' in result:
                    print(f"Relevance Score: {result['score']}")
        else:
            print("No retrieval results found in the response.")
        
        print("\nProcessing Time:")
        print("-" * 50)
        print(f"Total: {processing_time:.2f}s")
        
        return True
    
    except Exception as e:
        print(f"Error occurred: {str(e)}")
        return False

if __name__ == "__main__":
    # Run the test function
    success = test_knowledge_base_request()
    print("\nTest completed successfully" if success else "\nTest failed")
    sys.exit(0 if success else 1)
