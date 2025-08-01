"""
Bedrock Knowledge Base Functions

This module provides functions to interact with Amazon Bedrock Knowledge Bases.
It allows querying the knowledge base for information related to SOPs, LLD, and HLD documents.
Uses Amazon Nova Lite for retrieval and response generation.
"""

import boto3
import json
import os
import time
import traceback
from typing import Dict, List, Any, Optional
import httpx

# Import CloudWatch logger
try:
    from cloudwatch_logger import (
        log_knowledge_base_request,
        log_knowledge_base_response,
        log_error
    )
    CLOUDWATCH_LOGGING_ENABLED = True
except ImportError:
    print("CloudWatch logger not available, logging will be disabled")
    CLOUDWATCH_LOGGING_ENABLED = False
    
    # Define dummy logging functions
    def log_knowledge_base_request(*args, **kwargs):
        pass
    
    def log_knowledge_base_response(*args, **kwargs):
        pass
    
    def log_error(*args, **kwargs):
        pass

# Knowledge Base ID
KNOWLEDGE_BASE_ID = "CLRDOVZGIY"

# Model ID for response generation - using Nova Lite
NOVA_LITE_MODEL_ID = "amazon.nova-lite-v1:0"

# Initialize Bedrock clients
bedrock_runtime = boto3.client(
    service_name='bedrock-runtime',
    region_name='us-east-1'
)

# Initialize Bedrock Agent Runtime client for knowledge base operations
bedrock_agent_runtime = boto3.client(
    service_name='bedrock-agent-runtime',
    region_name='us-east-1'
)

def refresh_credentials():
    """
    Refreshes the AWS credentials from the ECS container metadata endpoint.
    Returns True if successful, False otherwise.
    """
    try:
        uri = os.environ.get("AWS_CONTAINER_CREDENTIALS_RELATIVE_URI")
        if uri:
            print("Fetching fresh AWS credentials from ECS metadata endpoint")
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

# Function to refresh credentials for Bedrock clients
def refresh_bedrock_clients():
    """
    Refreshes the Bedrock clients with the latest credentials.
    This ensures that the clients have valid credentials when making API calls.
    """
    try:
        print("Refreshing Bedrock clients with latest credentials")
        global bedrock_runtime, bedrock_agent_runtime
        
        # First refresh credentials from ECS metadata if available
        refresh_success = refresh_credentials()
        if not refresh_success:
            print("WARNING: Failed to refresh credentials, will try to continue with existing ones")
        
        # Get credentials from environment variables
        access_key = os.environ.get("AWS_ACCESS_KEY_ID")
        secret_key = os.environ.get("AWS_SECRET_ACCESS_KEY")
        session_token = os.environ.get("AWS_SESSION_TOKEN")
        
        if not access_key or not secret_key:
            error_msg = "WARNING: Missing AWS credentials for Bedrock clients"
            print(error_msg)
            if CLOUDWATCH_LOGGING_ENABLED:
                log_error(error_msg)
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
            error_msg = f"WARNING: Bedrock client test failed: {str(e)}"
            print(error_msg)
            if CLOUDWATCH_LOGGING_ENABLED:
                log_error(error_msg, {"exception": str(e)})
            
    except Exception as e:
        error_msg = f"ERROR refreshing Bedrock clients: {str(e)}"
        print(error_msg)
        traceback.print_exc()
        if CLOUDWATCH_LOGGING_ENABLED:
            log_error(error_msg, {"exception": str(e), "traceback": traceback.format_exc()})

def query_knowledge_base(query: str, max_results: int = 5) -> Dict[str, Any]:
    """
    Query the Bedrock knowledge base with a specific question.
    Uses Amazon Nova Lite for both retrieval and response generation:
    1. Retrieve relevant documents from the knowledge base
    2. Generate a comprehensive response using Nova Lite model
    
    Args:
        query: The question to ask the knowledge base
        max_results: Maximum number of results to return (default: 5)
        
    Returns:
        Dictionary containing the query results, source information, and generated response
    """
    try:
        print(f"Processing knowledge base query with Nova Lite: {query}")
        print(f"Using knowledge base ID: {KNOWLEDGE_BASE_ID}")
        start_time = time.time()
        
        # Log the request to CloudWatch
        if CLOUDWATCH_LOGGING_ENABLED:
            log_knowledge_base_request(query, max_results)
        
        # Step 1: Retrieve relevant documents from the knowledge base using bedrock-agent-runtime
        try:
            print("Attempting to retrieve documents from knowledge base...")
            # Ensure max_results is an integer
            if not isinstance(max_results, int):
                try:
                    max_results_int = int(max_results)
                    print(f"Converting max_results from {type(max_results)} to int: {max_results} -> {max_results_int}")
                except (ValueError, TypeError):
                    print(f"Invalid max_results value: {max_results}, using default value of 5")
                    max_results_int = 5
            else:
                max_results_int = max_results
                
            retrieval_response = bedrock_agent_runtime.retrieve(
                knowledgeBaseId=KNOWLEDGE_BASE_ID,
                retrievalQuery={
                    'text': query
                },
                retrievalConfiguration={
                    'vectorSearchConfiguration': {
                        'numberOfResults': max_results_int
                    }
                }
            )
            print(f"Successfully retrieved documents from knowledge base: {KNOWLEDGE_BASE_ID}")
            print(f"Retrieved {len(retrieval_response.get('retrievalResults', []))} documents")
        except Exception as e:
            error_msg = f"ERROR during knowledge base retrieval: {str(e)}"
            print(error_msg)
            traceback.print_exc()
            
            if CLOUDWATCH_LOGGING_ENABLED:
                log_error(error_msg, {
                    "query": query,
                    "exception": str(e),
                    "traceback": traceback.format_exc()
                })
                
            return {
                'status': 'error',
                'message': f"Failed to retrieve from knowledge base: {str(e)}",
                'query': query,
                'results': []
            }
        
        # Process and format the retrieval results
        retrieval_results = []
        context_text = ""
        
        for result in retrieval_response.get('retrievalResults', []):
            content = result.get('content', {}).get('text', '')
            source = result.get('location', {}).get('s3Location', {}).get('uri', '')
            score = result.get('score', 0)
            
            # Add to formatted results
            retrieval_results.append({
                'content': content,
                'source': source,
                'score': score
            })
            
            # Build context for response generation
            context_text += f"\n\nDocument Source: {source}\nContent: {content}\n"
        
        retrieval_time = time.time() - start_time
        print(f"Retrieval completed in {retrieval_time:.2f} seconds, found {len(retrieval_results)} documents")
        
        # Step 2: Generate a comprehensive response using Nova Lite model
        if context_text and len(retrieval_results) > 0:
            generation_start = time.time()
            
            # Prepare prompt for Nova Lite
            prompt = f"""
            You are a Virtual Cloud Assistant that provides information from documentation.
            
            User Query: {query}
            
            Here are the relevant documents I found:
            {context_text}
            
            Based ONLY on the information in these documents, provide a comprehensive answer to the user's query.
            If the documents don't contain enough information to answer the query, clearly state that.
            Include references to the source documents in your response.
            """
            
            # Call Nova Lite to generate a response
            try:
                print("Calling Nova Lite to generate response...")
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
                
                generation_time = time.time() - generation_start
                print(f"Nova Lite response generation completed in {generation_time:.2f} seconds")
                
                # Create the result
                result = {
                    'status': 'success',
                    'query': query,
                    'results': retrieval_results,
                    'generated_answer': generated_answer,
                    'processing_time': {
                        'retrieval': f"{retrieval_time:.2f}s",
                        'generation': f"{generation_time:.2f}s",
                        'total': f"{(time.time() - start_time):.2f}s"
                    }
                }
                
                # Log the response to CloudWatch
                if CLOUDWATCH_LOGGING_ENABLED:
                    log_knowledge_base_response(query, result)
                
                # Return both the retrieval results and the generated answer
                return result
                
            except Exception as e:
                error_msg = f"ERROR generating response with Nova Lite: {str(e)}"
                print(error_msg)
                traceback.print_exc()
                
                if CLOUDWATCH_LOGGING_ENABLED:
                    log_error(error_msg, {
                        "query": query,
                        "exception": str(e),
                        "traceback": traceback.format_exc()
                    })
                
                # Fall back to just returning retrieval results
                result = {
                    'status': 'partial_success',
                    'query': query,
                    'results': retrieval_results,
                    'error': f"Failed to generate response: {str(e)}"
                }
                
                # Log the partial response to CloudWatch
                if CLOUDWATCH_LOGGING_ENABLED:
                    log_knowledge_base_response(query, result)
                
                return result
        else:
            # No good results found
            print(f"No relevant documents found for query: {query}")
            result = {
                'status': 'no_relevant_documents',
                'query': query,
                'results': retrieval_results,
                'message': "No relevant documents found in the knowledge base."
            }
            
            # Log the empty response to CloudWatch
            if CLOUDWATCH_LOGGING_ENABLED:
                log_knowledge_base_response(query, result)
            
            return result
            
    except Exception as e:
        error_msg = f"ERROR querying knowledge base: {str(e)}"
        print(error_msg)
        traceback.print_exc()
        
        if CLOUDWATCH_LOGGING_ENABLED:
            log_error(error_msg, {
                "query": query,
                "exception": str(e),
                "traceback": traceback.format_exc()
            })
        
        return {
            'status': 'error',
            'message': f"Failed to query knowledge base: {str(e)}",
            'query': query,
            'results': []
        }

def get_document_by_id(document_id: str) -> Dict[str, Any]:
    """
    Retrieve a specific document from the knowledge base by its ID.
    
    Args:
        document_id: The ID of the document to retrieve
        
    Returns:
        Dictionary containing the document information
    """
    try:
        # Call the Bedrock Agent Runtime retrieve API with document ID filter
        response = bedrock_agent_runtime.retrieve(
            knowledgeBaseId=KNOWLEDGE_BASE_ID,
            retrievalQuery={
                'text': f"document_id:{document_id}"
            }
        )
        
        # Process and return the document
        if response.get('retrievalResults'):
            result = response['retrievalResults'][0]
            return {
                'status': 'success',
                'document_id': document_id,
                'content': result.get('content', {}).get('text', ''),
                'source': result.get('location', {}).get('s3Location', {}).get('uri', ''),
                'metadata': result.get('metadata', {})
            }
        else:
            return {
                'status': 'error',
                'message': f"Document with ID {document_id} not found",
                'document_id': document_id
            }
            
    except Exception as e:
        print(f"Error retrieving document: {str(e)}")
        return {
            'status': 'error',
            'message': f"Failed to retrieve document: {str(e)}",
            'document_id': document_id
        }

def search_documents(keywords: str, document_type: Optional[str] = None, max_results: int = 10) -> Dict[str, Any]:
    """
    Search for documents in the knowledge base based on keywords and optional document type.
    
    Args:
        keywords: Keywords to search for
        document_type: Optional filter for document type (SOP, LLD, HLD)
        max_results: Maximum number of results to return (default: 10)
        
    Returns:
        Dictionary containing the search results
    """
    try:
        # Construct the query based on parameters
        query = keywords
        if document_type:
            query = f"{query} type:{document_type}"
            
        # Call the Bedrock Agent Runtime retrieve API
        response = bedrock_agent_runtime.retrieve(
            knowledgeBaseId=KNOWLEDGE_BASE_ID,
            retrievalQuery={
                'text': query
            },
            retrievalConfiguration={
                'vectorSearchConfiguration': {
                    'numberOfResults': max_results
                }
            }
        )
        
        # Process and format the results
        results = []
        for result in response.get('retrievalResults', []):
            # Extract filename from S3 URI
            s3_uri = result.get('location', {}).get('s3Location', {}).get('uri', '')
            filename = s3_uri.split('/')[-1] if s3_uri else 'Unknown'
            
            results.append({
                'title': filename,
                'content_snippet': result.get('content', {}).get('text', '')[:200] + '...',
                'source': s3_uri,
                'score': result.get('score', 0),
                'metadata': result.get('metadata', {})
            })
            
        return {
            'status': 'success',
            'keywords': keywords,
            'document_type': document_type,
            'results': results
        }
        
    except Exception as e:
        print(f"Error searching documents: {str(e)}")
        return {
            'status': 'error',
            'message': f"Failed to search documents: {str(e)}",
            'keywords': keywords,
            'document_type': document_type,
            'results': []
        }

# Function to format knowledge base results for the frontend
def format_kb_response(result: Dict[str, Any]) -> Dict[str, Any]:
    """
    Format knowledge base results for frontend display.
    
    Args:
        result: The knowledge base query result
        
    Returns:
        Formatted response for frontend display
    """
    if result.get('status') == 'error':
        return {
            'title': 'Error',
            'content': result.get('message', 'An error occurred while querying the knowledge base.'),
            'source': None,
            'metadata': {}
        }
    
    # For document retrieval
    if 'document_id' in result:
        return {
            'title': f"Document: {result.get('document_id')}",
            'content': result.get('content', ''),
            'source': result.get('source', ''),
            'metadata': result.get('metadata', {})
        }
    
    # For search results
    if 'keywords' in result:
        formatted_results = []
        for item in result.get('results', []):
            formatted_results.append({
                'title': item.get('title', ''),
                'content': item.get('content_snippet', ''),
                'source': item.get('source', ''),
                'score': item.get('score', 0)
            })
        
        return {
            'title': f"Search Results for: {result.get('keywords')}",
            'content': formatted_results,
            'source': None,
            'metadata': {'document_type': result.get('document_type')}
        }
    
    # For general queries with Nova Lite generated answer
    if 'query' in result and 'generated_answer' in result:
        formatted_results = []
        
        # Add the generated answer as the first item
        formatted_results.append({
            'content': result.get('generated_answer', ''),
            'source': 'Generated by Nova Lite',
            'score': 1.0
        })
        
        # Add the source documents
        for item in result.get('results', []):
            formatted_results.append({
                'content': item.get('content', ''),
                'source': item.get('source', ''),
                'score': item.get('score', 0)
            })
        
        return {
            'title': f"Knowledge Base Results for: {result.get('query')}",
            'content': formatted_results,
            'source': None,
            'metadata': {'processing_time': result.get('processing_time', {})}
        }
    
    # For general queries without generated answer
    if 'query' in result:
        formatted_results = []
        for item in result.get('results', []):
            formatted_results.append({
                'content': item.get('content', ''),
                'source': item.get('source', ''),
                'score': item.get('score', 0)
            })
        
        return {
            'title': f"Knowledge Base Results for: {result.get('query')}",
            'content': formatted_results,
            'source': None,
            'metadata': {}
        }
    
    # Default case
    return {
        'title': 'Knowledge Base Results',
        'content': str(result),
        'source': None,
        'metadata': {}
    }
