"""
Bedrock Knowledge Base Functions

This module provides functions to interact with Amazon Bedrock Knowledge Bases.
It allows querying the knowledge base for information related to SOPs, LLD, and HLD documents.
"""

import boto3
import json
import os
from typing import Dict, List, Any, Optional

# Initialize Bedrock client
bedrock_runtime = boto3.client(
    service_name='bedrock-runtime',
    region_name='us-east-1'
)

# Knowledge Base ID
KNOWLEDGE_BASE_ID = "CLRDOVZGIY"

def query_knowledge_base(query: str, max_results: int = 5) -> Dict[str, Any]:
    """
    Query the Bedrock knowledge base with a specific question.
    
    Args:
        query: The question to ask the knowledge base
        max_results: Maximum number of results to return (default: 5)
        
    Returns:
        Dictionary containing the query results and source information
    """
    try:
        # Call the Bedrock Runtime retrieve API
        response = bedrock_runtime.retrieve(
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
            results.append({
                'content': result.get('content', {}).get('text', ''),
                'source': result.get('location', {}).get('s3Location', {}).get('uri', ''),
                'score': result.get('score', 0)
            })
            
        return {
            'status': 'success',
            'query': query,
            'results': results
        }
        
    except Exception as e:
        print(f"Error querying knowledge base: {str(e)}")
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
        # Call the Bedrock Runtime retrieve API with document ID filter
        response = bedrock_runtime.retrieve(
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
            
        # Call the Bedrock Runtime retrieve API
        response = bedrock_runtime.retrieve(
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
    
    # For general queries
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
