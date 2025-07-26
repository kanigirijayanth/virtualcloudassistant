"""
Patch for main.py to improve knowledge base function logging
Copy these wrapped functions to replace the existing ones in main.py
"""

# Define wrapper functions that handle credential refresh with improved logging
def wrapped_query_knowledge_base(query, max_results=5):
    try:
        print(f"KNOWLEDGE BASE QUERY CALLED: '{query}'")
        refresh_bedrock_clients()  # Refresh credentials before calling
        
        print(f"Calling query_knowledge_base with query: '{query}', max_results: {max_results}")
        result = query_knowledge_base(query, max_results)
        
        print(f"Knowledge base query result status: {result.get('status')}")
        if result.get('status') == 'success':
            print(f"Found {len(result.get('results', []))} documents")
            if 'generated_answer' in result:
                print(f"Generated answer length: {len(result.get('generated_answer', ''))}")
        
        return result
    except Exception as e:
        print(f"ERROR in wrapped_query_knowledge_base: {str(e)}")
        traceback.print_exc()
        return {
            'status': 'error',
            'message': f"Knowledge base query failed: {str(e)}",
            'query': query,
            'results': []
        }

def wrapped_get_document_by_id(document_id):
    try:
        print(f"GET DOCUMENT CALLED with ID: {document_id}")
        refresh_bedrock_clients()  # Refresh credentials before calling
        
        print(f"Calling get_document_by_id with document_id: {document_id}")
        result = get_document_by_id(document_id)
        
        print(f"Get document result status: {result.get('status')}")
        return result
    except Exception as e:
        print(f"ERROR in wrapped_get_document_by_id: {str(e)}")
        traceback.print_exc()
        return {
            'status': 'error',
            'message': f"Document retrieval failed: {str(e)}",
            'document_id': document_id
        }

def wrapped_search_documents(keywords, document_type=None, max_results=10):
    try:
        print(f"SEARCH DOCUMENTS CALLED with keywords: '{keywords}', type: {document_type}")
        refresh_bedrock_clients()  # Refresh credentials before calling
        
        print(f"Calling search_documents with keywords: '{keywords}', document_type: {document_type}, max_results: {max_results}")
        result = search_documents(keywords, document_type, max_results)
        
        print(f"Search documents result status: {result.get('status')}")
        if result.get('status') == 'success':
            print(f"Found {len(result.get('results', []))} documents")
        
        return result
    except Exception as e:
        print(f"ERROR in wrapped_search_documents: {str(e)}")
        traceback.print_exc()
        return {
            'status': 'error',
            'message': f"Document search failed: {str(e)}",
            'keywords': keywords,
            'results': []
        }
