"""
Custom AWS Nova Sonic Service

This module extends the AWS Nova Sonic service to handle knowledge base responses.
It wraps the original service and adds functionality to send knowledge base responses to the frontend.
"""

import json
from typing import Dict, Any, Optional, List, Callable
from aws import AWSNovaSonicLLMService, Params
from bedrock_kb_functions import format_kb_response

class CustomNovaSonicService(AWSNovaSonicLLMService):
    """
    Custom AWS Nova Sonic service that extends the original service to handle knowledge base responses.
    """
    
    def __init__(self, *args, **kwargs):
        """Initialize the custom service with the same parameters as the original."""
        super().__init__(*args, **kwargs)
        self.transport = None
    
    def set_transport(self, transport):
        """Set the transport to use for sending knowledge base responses."""
        self.transport = transport
    
    def register_function(self, name: str, func: Callable):
        """
        Register a function with the service and add special handling for knowledge base functions.
        
        Args:
            name: The name of the function
            func: The function to register
        """
        original_func = func
        
        # For knowledge base functions, add special handling
        if name in ["query_knowledge_base", "get_document_by_id", "search_documents"]:
            def wrapped_func(*args, **kwargs):
                # Call the original function
                result = original_func(*args, **kwargs)
                
                # Format the result for frontend display
                formatted_result = format_kb_response(result)
                
                # Send the formatted result to the frontend if transport is available
                if self.transport:
                    try:
                        self.transport.send_json({
                            "event": "knowledge_base",
                            "data": json.dumps(formatted_result)
                        })
                    except Exception as e:
                        print(f"Error sending knowledge base response to frontend: {str(e)}")
                
                # Return the original result for the LLM to process
                return result
            
            # Register the wrapped function
            super().register_function(name, wrapped_func)
        else:
            # Register the original function for non-knowledge base functions
            super().register_function(name, func)
