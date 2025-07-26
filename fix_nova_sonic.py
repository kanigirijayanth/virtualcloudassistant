#!/usr/bin/env python3
"""
Script to fix the Nova Sonic input request issue
This script updates the custom_nova_sonic.py file to fix the issue with function calls
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

def update_custom_nova_sonic():
    """Update the CustomNovaSonicService class to fix the function call issue"""
    file_path = "/root/aws/ciscld/voicebot/virtualcloudassistant/backend/app/custom_nova_sonic.py"
    
    if not os.path.exists(file_path):
        print(f"File {file_path} not found")
        sys.exit(1)
    
    # Read the file
    with open(file_path, 'r') as f:
        content = f.read()
    
    # Backup the file
    backup_file(file_path)
    
    # Update the register_function method to fix parameter handling
    updated_content = content.replace(
        """    def register_function(self, name: str, func: Callable):
        \"\"\"
        Register a function with the service and add special handling for knowledge base functions.
        
        Args:
            name: The name of the function
            func: The function to register
        \"\"\"
        original_func = func
        
        # For knowledge base functions, add special handling
        if name in ["query_knowledge_base", "get_document_by_id", "search_documents"]:
            async def wrapped_func(*args, **kwargs):
                # Set flag that we're processing a knowledge base query
                self._processing_kb_query = True
                
                # Start sending heartbeat audio frames to prevent buffer starvation
                self._start_heartbeat_audio()
                
                try:
                    # Extract the actual query from args or kwargs
                    # The LLM might pass multiple arguments, but we only need the query
                    query = ""
                    if args and len(args) > 0:
                        # If first arg is a string, use it as the query
                        if isinstance(args[0], str):
                            query = args[0]
                        # Otherwise, try to find a query parameter in kwargs
                        elif kwargs and "query" in kwargs:
                            query = kwargs["query"]
                    elif kwargs and "query" in kwargs:
                        query = kwargs["query"]
                    
                    # First send a processing notification to the frontend
                    await self._send_json_to_client({
                        "event": "kb_processing",
                        "data": json.dumps({
                            "status": "processing",
                            "message": f"Processing {name} request...",
                            "query": query
                        })
                    })
                    
                    # Call the original function with only the parameters it expects
                    start_time = time.time()
                    
                    # Handle different function signatures
                    if name == "query_knowledge_base":
                        # query_knowledge_base(query, max_results=5)
                        result = original_func(query)
                    elif name == "get_document_by_id":
                        # get_document_by_id(document_id)
                        document_id = kwargs.get("document_id", query)
                        result = original_func(document_id)
                    elif name == "search_documents":
                        # search_documents(keywords, document_type=None, max_results=10)
                        document_type = kwargs.get("document_type", None)
                        result = original_func(query, document_type)
                    else:
                        # Fallback
                        result = original_func(query)
                        
                    processing_time = time.time() - start_time
                    
                    print(f"Knowledge base function {name} completed in {processing_time:.2f} seconds")
                    
                    # Format the result for frontend display
                    formatted_result = format_kb_response(result)
                    
                    # Send the formatted result to the frontend
                    await self._send_json_to_client({
                        "event": "knowledge_base",
                        "data": json.dumps(formatted_result)
                    })
                    
                    # Stop the heartbeat audio after sending the result
                    self._stop_heartbeat_audio()
                    self._processing_kb_query = False
                    
                    # Return the original result for the LLM to process
                    return result
                    
                except Exception as e:
                    # Stop the heartbeat audio in case of error
                    self._stop_heartbeat_audio()
                    self._processing_kb_query = False
                    print(f"Error in knowledge base function: {str(e)}")
                    # Re-raise the exception
                    raise
            
            # Register the wrapped function
            super().register_function(name, wrapped_func)
        else:
            # Register the original function for non-knowledge base functions
            super().register_function(name, func)""",
        
        """    def register_function(self, name: str, func: Callable):
        \"\"\"
        Register a function with the service and add special handling for knowledge base functions.
        
        Args:
            name: The name of the function
            func: The function to register
        \"\"\"
        original_func = func
        
        # For knowledge base functions, add special handling
        if name in ["query_knowledge_base", "get_document_by_id", "search_documents"]:
            async def wrapped_func(*args, **kwargs):
                # Set flag that we're processing a knowledge base query
                self._processing_kb_query = True
                
                # Start sending heartbeat audio frames to prevent buffer starvation
                self._start_heartbeat_audio()
                
                try:
                    # Extract the actual query from args or kwargs
                    # The LLM might pass multiple arguments, but we only need the query
                    query = ""
                    max_results = 5  # Default value
                    document_type = None
                    document_id = ""
                    
                    # Print the received arguments for debugging
                    print(f"Function {name} called with args: {args}, kwargs: {kwargs}")
                    
                    # Extract parameters based on function name
                    if name == "query_knowledge_base":
                        # Handle both positional and keyword arguments
                        if args and len(args) > 0:
                            query = args[0]
                        elif "query" in kwargs:
                            query = kwargs["query"]
                            
                        if len(args) > 1:
                            max_results = args[1]
                        elif "max_results" in kwargs:
                            max_results = kwargs["max_results"]
                            
                    elif name == "get_document_by_id":
                        if args and len(args) > 0:
                            document_id = args[0]
                        elif "document_id" in kwargs:
                            document_id = kwargs["document_id"]
                            
                    elif name == "search_documents":
                        if args and len(args) > 0:
                            query = args[0]  # keywords
                        elif "keywords" in kwargs:
                            query = kwargs["keywords"]
                            
                        if len(args) > 1:
                            document_type = args[1]
                        elif "document_type" in kwargs:
                            document_type = kwargs["document_type"]
                            
                        if len(args) > 2:
                            max_results = args[2]
                        elif "max_results" in kwargs:
                            max_results = kwargs["max_results"]
                    
                    # First send a processing notification to the frontend
                    await self._send_json_to_client({
                        "event": "kb_processing",
                        "data": json.dumps({
                            "status": "processing",
                            "message": f"Processing {name} request...",
                            "query": query or document_id
                        })
                    })
                    
                    # Call the original function with the correct parameters
                    start_time = time.time()
                    
                    # Handle different function signatures
                    if name == "query_knowledge_base":
                        print(f"Calling query_knowledge_base with query: '{query}', max_results: {max_results}")
                        result = original_func(query, max_results)
                    elif name == "get_document_by_id":
                        print(f"Calling get_document_by_id with document_id: '{document_id}'")
                        result = original_func(document_id)
                    elif name == "search_documents":
                        print(f"Calling search_documents with keywords: '{query}', document_type: {document_type}, max_results: {max_results}")
                        result = original_func(query, document_type, max_results)
                    else:
                        # Fallback
                        result = original_func(*args, **kwargs)
                        
                    processing_time = time.time() - start_time
                    
                    print(f"Knowledge base function {name} completed in {processing_time:.2f} seconds")
                    
                    # Format the result for frontend display
                    formatted_result = format_kb_response(result)
                    
                    # Send the formatted result to the frontend
                    await self._send_json_to_client({
                        "event": "knowledge_base",
                        "data": json.dumps(formatted_result)
                    })
                    
                    # Stop the heartbeat audio after sending the result
                    self._stop_heartbeat_audio()
                    self._processing_kb_query = False
                    
                    # Return the original result for the LLM to process
                    return result
                    
                except Exception as e:
                    # Stop the heartbeat audio in case of error
                    self._stop_heartbeat_audio()
                    self._processing_kb_query = False
                    print(f"Error in knowledge base function: {str(e)}")
                    traceback.print_exc()
                    # Re-raise the exception
                    raise
            
            # Register the wrapped function
            super().register_function(name, wrapped_func)
        else:
            # Register the original function for non-knowledge base functions
            super().register_function(name, func)"""
    )
    
    # Add traceback import if not already present
    if "import traceback" not in updated_content:
        updated_content = updated_content.replace(
            "import json\nimport time\nimport asyncio\nimport base64",
            "import json\nimport time\nimport asyncio\nimport base64\nimport traceback"
        )
    
    # Write the updated content
    with open(file_path, 'w') as f:
        f.write(updated_content)
    
    print(f"Updated {file_path}")

def main():
    """Main function to update the files"""
    update_custom_nova_sonic()
    print("Fix completed. Please redeploy the application using deploy_kb_fix.sh")

if __name__ == "__main__":
    main()
