#!/usr/bin/env python3
"""
Test function to check knowledge base request with the query about incident ticket creation
This script makes a request to the existing Bedrock knowledge base CLRDOVZGIY and extracts
the specific information about creating incident tickets.
"""

import sys
import boto3
import time

def test_knowledge_base_request():
    """
    Function to test knowledge base request and extract incident ticket creation information
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
        
        print("\nEXTRACTED INFORMATION ABOUT INCIDENT TICKET CREATION:")
        print("-" * 50)
        
        # Look for the specific information about creating incident tickets
        found_info = False
        
        if 'retrievalResults' in response:
            for result in response['retrievalResults']:
                if 'content' in result and 'text' in result['content']:
                    content_text = result['content']['text']
                    
                    # Check if this result contains information about creating incident tickets
                    if 'Create Incident Ticket' in content_text:
                        # Extract the specific section about creating incident tickets
                        start_idx = content_text.find('3. Create Incident Ticket')
                        if start_idx == -1:
                            start_idx = content_text.find('Create Incident Ticket')
                        
                        end_idx = content_text.find('4.', start_idx)
                        if end_idx == -1:
                            end_idx = len(content_text)
                        
                        ticket_info = content_text[start_idx:end_idx].strip()
                        print(ticket_info)
                        
                        # Print the source document
                        if 'location' in result and 's3Location' in result['location']:
                            print(f"\nSource: {result['location']['s3Location'].get('uri', 'Unknown')}")
                        
                        # Print the relevance score
                        if 'score' in result:
                            print(f"Relevance Score: {result['score']}")
                        
                        found_info = True
                        break
        
        if not found_info:
            print("No specific information about incident ticket creation found.")
        
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
