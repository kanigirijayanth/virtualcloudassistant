"""
Custom AWS Nova Sonic Service

This module extends the AWS Nova Sonic service to handle knowledge base responses.
It wraps the original service and adds functionality to send knowledge base responses to the frontend.
"""

import json
import time
import asyncio
import base64
import traceback
from typing import Dict, Any, Optional, List, Callable
from aws import AWSNovaSonicLLMService, Params
from bedrock_kb_functions import format_kb_response

# Import CloudWatch logger if available
try:
    from cloudwatch_logger import log_nova_sonic_input, log_error
    CLOUDWATCH_LOGGING_ENABLED = True
except ImportError:
    print("CloudWatch logger not available, logging will be disabled")
    CLOUDWATCH_LOGGING_ENABLED = False
    
    # Define dummy logging functions
    def log_nova_sonic_input(*args, **kwargs):
        pass
    
    def log_error(*args, **kwargs):
        pass

class CustomNovaSonicService(AWSNovaSonicLLMService):
    """
    Custom AWS Nova Sonic service that extends the original service to handle knowledge base responses.
    """
    
    def __init__(self, *args, **kwargs):
        """Initialize the custom service with the same parameters as the original."""
        super().__init__(*args, **kwargs)
        self.transport = None
        # Generate silent audio frames of different durations for keeping the audio buffer fed
        self._silent_audio_frames = self._generate_silent_audio_frames()
        # Flag to track if we're currently processing a knowledge base query
        self._processing_kb_query = False
        # Store the last knowledge base response
        self._last_kb_response = None
        # Flag to track if we need to send the knowledge base response to Nova Sonic
        self._kb_response_pending = False
        # Bedrock agent configuration
        self._bedrock_agent_id = None
        self._bedrock_agent_alias_id = None
        # Flag to track if we're currently processing a Bedrock agent query
        self._processing_agent_query = False
    
    def set_transport(self, transport):
        """Set the transport to use for sending knowledge base responses."""
        self.transport = transport
    
    def set_bedrock_agent_config(self, agent_id, agent_alias_id):
        """Set the Bedrock agent configuration."""
        self._bedrock_agent_id = agent_id
        self._bedrock_agent_alias_id = agent_alias_id
        print(f"Bedrock agent configuration set: agent_id={agent_id}, agent_alias_id={agent_alias_id}")
    
    def _generate_silent_audio_frames(self):
        """Generate silent audio frames of different durations."""
        frames = {}
        # Generate silent frames of 100ms, 200ms, 500ms, and 1000ms
        for duration_ms in [100, 200, 500, 1000]:
            # Calculate number of samples for the given duration at 16kHz
            num_samples = int(16000 * (duration_ms / 1000))
            # Create silent PCM data (16-bit)
            silent_pcm = bytes(num_samples * 2)  # 2 bytes per sample for 16-bit PCM
            # Encode as base64
            frames[duration_ms] = base64.b64encode(silent_pcm).decode('utf-8')
        return frames
    
    async def query_bedrock_agent(self, query: str):
        """
        Query the Bedrock agent with the given query.
        
        Args:
            query: The query to send to the agent
            
        Returns:
            The agent's response
        """
        if not self._bedrock_agent_id or not self._bedrock_agent_alias_id:
            error_msg = "Bedrock agent not configured"
            print(error_msg)
            return {
                'status': 'error',
                'message': error_msg
            }
        
        # Set flag that we're processing an agent query
        self._processing_agent_query = True
        
        # Don't start heartbeat audio - it can cause voice cracking
        # self._start_heartbeat_audio()
        
        try:
            # First send a processing notification to the frontend
            await self._send_json_to_client({
                "event": "kb_processing",
                "data": json.dumps({
                    "status": "processing",
                    "message": "Processing project documentation query with Bedrock agent...",
                    "query": query
                })
            })
            
            # Import the query_bedrock_agent function
            from bedrock_agent_functions import query_bedrock_agent
            
            # Call the function
            start_time = time.time()
            result = query_bedrock_agent(
                agent_id=self._bedrock_agent_id,
                agent_alias_id=self._bedrock_agent_alias_id,
                query=query
            )
            processing_time = time.time() - start_time
            
            print(f"Bedrock agent query completed in {processing_time:.2f} seconds")
            
            # Send the result to the frontend
            await self._send_json_to_client({
                "event": "knowledge_base",
                "data": json.dumps({
                    "title": "Project Documentation (Bedrock Agent)",
                    "content": result.get('completion', 'No response from agent'),
                    "source": "Generated by Bedrock Agent",
                    "metadata": {
                        "processing_time": {
                            "retrieval": "N/A",
                            "generation": f"{processing_time:.2f}s",
                            "total": f"{processing_time:.2f}s"
                        },
                        "agent_id": self._bedrock_agent_id,
                        "agent_alias_id": self._bedrock_agent_alias_id
                    }
                })
            })
            
            # Create a message for Nova Sonic
            nova_sonic_message = f"I found information about your project documentation query. The details are now displayed on the screen."
            
            # Log the message being sent to Nova Sonic
            if CLOUDWATCH_LOGGING_ENABLED:
                log_nova_sonic_input(nova_sonic_message)
            
            # Stop the heartbeat audio after sending the result
            self._stop_heartbeat_audio()
            self._processing_agent_query = False
            
            # Return the message for Nova Sonic
            return {
                'status': 'success',
                'message': nova_sonic_message,
                'original_result': result
            }
            
        except Exception as e:
            # Stop the heartbeat audio in case of error
            self._stop_heartbeat_audio()
            self._processing_agent_query = False
            
            error_msg = f"Error querying Bedrock agent: {str(e)}"
            print(error_msg)
            traceback.print_exc()
            
            if CLOUDWATCH_LOGGING_ENABLED:
                log_error(error_msg, {
                    "query": query,
                    "agent_id": self._bedrock_agent_id,
                    "agent_alias_id": self._bedrock_agent_alias_id,
                    "exception": str(e),
                    "traceback": traceback.format_exc()
                })
            
            # Send error to frontend
            await self._send_json_to_client({
                "event": "knowledge_base",
                "data": json.dumps({
                    "title": "Project Documentation (Bedrock Agent)",
                    "content": f"Error querying Bedrock agent: {str(e)}",
                    "source": "Error",
                    "metadata": {}
                })
            })
            
            # Create an error message for Nova Sonic
            nova_sonic_message = f"I encountered an error while trying to query the project documentation: {str(e)}"
            
            # Return an error result
            return {
                'status': 'error',
                'message': nova_sonic_message,
                'error': str(e)
            }
    
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
            async def wrapped_func(*args, **kwargs):
                # Check if this is a project documentation query
                is_project_doc_query = False
                query = ""
                
                # Extract the query from args or kwargs
                if args and len(args) > 0:
                    query = args[0]
                elif "query" in kwargs:
                    query = kwargs["query"]
                
                # Check if the query is about project documentation
                if query:
                    # Simple keyword check for project documentation
                    project_doc_keywords = [
                        'project', 'documentation', 'docs', 'document', 
                        'architecture', 'design', 'specification', 'spec',
                        'requirements', 'user guide', 'manual', 'handbook',
                        'technical doc', 'api doc', 'system doc'
                    ]
                    
                    # Convert query to lowercase for case-insensitive matching
                    lower_query = query.lower()
                    
                    # Check if any of the keywords are in the query
                    is_project_doc_query = any(keyword in lower_query for keyword in project_doc_keywords)
                
                # If this is a project documentation query and we have a Bedrock agent configured,
                # use the agent instead of the knowledge base
                if is_project_doc_query and self._bedrock_agent_id and self._bedrock_agent_alias_id:
                    print(f"Detected project documentation query: '{query}', routing to Bedrock agent")
                    return await self.query_bedrock_agent(query)
                
                # Otherwise, proceed with the original knowledge base query
                # Set flag that we're processing a knowledge base query
                self._processing_kb_query = True
                
                # Don't start heartbeat audio - it can cause voice cracking
                # self._start_heartbeat_audio()
                
                try:
                    # Extract the actual query from args or kwargs
                    # The LLM might pass multiple arguments, but we only need the query
                    query = ""
                    max_results = 5  # Default value
                    document_type = None
                    document_id = ""
                    
                    # Print the received arguments for debugging
                    print(f"Function {name} called with args: {args}, kwargs: {kwargs}")
                    
                    # Check if tool_call_id is being passed and remove it from kwargs
                    if "tool_call_id" in kwargs:
                        print(f"Removing tool_call_id from kwargs: {kwargs['tool_call_id']}")
                        tool_call_id = kwargs.pop("tool_call_id")
                    else:
                        tool_call_id = None
                        
                    # Extract parameters based on function name
                    if name == "query_knowledge_base":
                        # Handle both positional and keyword arguments
                        if args and len(args) > 0:
                            query = args[0]
                        elif "query" in kwargs:
                            query = kwargs["query"]
                        else:
                            query = ""
                            
                        # Set a default value for max_results
                        max_results = 5
                        
                        # Only use the second argument if it's actually an integer or can be converted to one
                        if len(args) > 1:
                            if isinstance(args[1], int):
                                max_results = args[1]
                            else:
                                try:
                                    max_results = int(args[1])
                                except (ValueError, TypeError):
                                    print(f"Warning: Invalid max_results value in args: {args[1]}, using default value of 5")
                        elif "max_results" in kwargs:
                            if isinstance(kwargs["max_results"], int):
                                max_results = kwargs["max_results"]
                            else:
                                try:
                                    max_results = int(kwargs["max_results"])
                                except (ValueError, TypeError):
                                    print(f"Warning: Invalid max_results value in kwargs: {kwargs['max_results']}, using default value of 5")
                            
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
                            # Ensure max_results is an integer
                            if isinstance(kwargs["max_results"], dict):
                                print(f"WARNING: max_results is a dictionary: {kwargs['max_results']}, using default value of 10")
                                max_results = 10
                            else:
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
                        # Remove tool_call_id from kwargs if present
                        if "tool_call_id" in kwargs:
                            print(f"Removing tool_call_id from kwargs for function {name}: {kwargs['tool_call_id']}")
                            kwargs.pop("tool_call_id")
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
                    
                    # Store the result for Nova Sonic to use
                    self._last_kb_response = result
                    self._kb_response_pending = True
                    
                    # Prepare a response for Nova Sonic
                    if name == "query_knowledge_base" and result.get('status') == 'success' and 'generated_answer' in result:
                        # Create a message for Nova Sonic that includes the generated answer
                        nova_sonic_message = f"I found information in the knowledge base about '{query}'.\n\n{result['generated_answer']}"
                        
                        # Log the message being sent to Nova Sonic
                        if CLOUDWATCH_LOGGING_ENABLED:
                            log_nova_sonic_input(nova_sonic_message)
                        
                        # Stop the heartbeat audio after sending the result
                        self._stop_heartbeat_audio()
                        self._processing_kb_query = False
                        
                        # Return the original result for the LLM to process
                        return {
                            'status': 'success',
                            'message': nova_sonic_message,
                            'original_result': result
                        }
                    else:
                        # For other cases or errors, create a generic message
                        if result.get('status') == 'error':
                            nova_sonic_message = f"I encountered an error while searching the knowledge base: {result.get('message', 'Unknown error')}"
                        elif result.get('status') == 'no_relevant_documents':
                            nova_sonic_message = f"I searched the knowledge base for information about '{query}', but couldn't find any relevant documents."
                        else:
                            nova_sonic_message = f"I found some information in the knowledge base that might be relevant to '{query}', but I couldn't generate a comprehensive answer."
                        
                        # Log the message being sent to Nova Sonic
                        if CLOUDWATCH_LOGGING_ENABLED:
                            log_nova_sonic_input(nova_sonic_message)
                        
                        # Stop the heartbeat audio after sending the result
                        self._stop_heartbeat_audio()
                        self._processing_kb_query = False
                        
                        # Return the original result for the LLM to process
                        return {
                            'status': result.get('status', 'unknown'),
                            'message': nova_sonic_message,
                            'original_result': result
                        }
                    
                except Exception as e:
                    # Stop the heartbeat audio in case of error
                    self._stop_heartbeat_audio()
                    self._processing_kb_query = False
                    
                    error_msg = f"Error in knowledge base function: {str(e)}"
                    print(error_msg)
                    traceback.print_exc()
                    
                    if CLOUDWATCH_LOGGING_ENABLED:
                        log_error(error_msg, {
                            "function": name,
                            "args": str(args),
                            "kwargs": str(kwargs),
                            "exception": str(e),
                            "traceback": traceback.format_exc()
                        })
                    
                    # Create an error message for Nova Sonic
                    nova_sonic_message = f"I encountered an error while trying to search the knowledge base: {str(e)}"
                    
                    # Return an error result
                    return {
                        'status': 'error',
                        'message': nova_sonic_message,
                        'error': str(e)
                    }
            
            # Register the wrapped function
            super().register_function(name, wrapped_func)
        else:
            # Register the original function for non-knowledge base functions
            super().register_function(name, func)
    
    def _start_heartbeat_audio(self):
        """Start sending heartbeat audio frames to prevent buffer starvation."""
        # DISABLED: Heartbeat audio can cause voice cracking issues
        # Commenting out to prevent interference with Nova Sonic audio stream
        pass
        # if not hasattr(self, '_heartbeat_task') or self._heartbeat_task is None:
        #     self._heartbeat_running = True
        #     self._heartbeat_task = asyncio.create_task(self._send_heartbeat_audio())
    
    def _stop_heartbeat_audio(self):
        """Stop sending heartbeat audio frames."""
        # DISABLED: Heartbeat audio can cause voice cracking issues
        pass
        # self._heartbeat_running = False
        # if hasattr(self, '_heartbeat_task') and self._heartbeat_task is not None:
        #     self._heartbeat_task.cancel()
        #     self._heartbeat_task = None
    
    async def _send_heartbeat_audio(self):
        """Send heartbeat audio frames at regular intervals to prevent buffer starvation."""
        try:
            # Send initial audio frame immediately
            await self._send_silent_audio(500)  # 500ms silent frame
            
            # Then send frames at regular intervals
            while self._heartbeat_running and self.transport:
                # Send a 200ms silent frame every 2 seconds
                await self._send_silent_audio(200)
                await asyncio.sleep(2)
                
                # Send a 500ms silent frame every 5 seconds
                await self._send_silent_audio(500)
                await asyncio.sleep(3)
                
                # Send a 1000ms silent frame every 10 seconds
                await self._send_silent_audio(1000)
                await asyncio.sleep(5)
        except asyncio.CancelledError:
            # Task was cancelled, clean up
            pass
        except Exception as e:
            error_msg = f"Error in heartbeat audio task: {str(e)}"
            print(error_msg)
            if CLOUDWATCH_LOGGING_ENABLED:
                log_error(error_msg, {"exception": str(e)})
    
    async def _send_silent_audio(self, duration_ms):
        """Send a silent audio frame of the specified duration."""
        if self.transport:
            try:
                await self._send_json_to_client({
                    "event": "media",
                    "data": self._silent_audio_frames[duration_ms]
                })
            except Exception as e:
                error_msg = f"Error sending silent audio frame: {str(e)}"
                print(error_msg)
                if CLOUDWATCH_LOGGING_ENABLED:
                    log_error(error_msg, {"exception": str(e)})
                
    async def _send_json_to_client(self, data):
        """Send JSON data to the client using the transport's websocket send_text method with improved error handling."""
        if self.transport and hasattr(self.transport, 'websocket'):
            try:
                # Check if websocket is still open
                if hasattr(self.transport.websocket, 'client_state') and self.transport.websocket.client_state.name != 'CONNECTED':
                    print(f"WebSocket not connected, state: {self.transport.websocket.client_state.name}")
                    return False
                
                # Add timeout to prevent hanging
                import asyncio
                await asyncio.wait_for(
                    self.transport.websocket.send_text(json.dumps(data)),
                    timeout=5.0  # 5 second timeout
                )
                return True
            except asyncio.TimeoutError:
                error_msg = "Timeout sending JSON to client"
                print(error_msg)
                if CLOUDWATCH_LOGGING_ENABLED:
                    log_error(error_msg, {"data": str(data)})
                return False
            except Exception as e:
                error_msg = f"Error sending JSON to client: {str(e)}"
                print(error_msg)
                if CLOUDWATCH_LOGGING_ENABLED:
                    log_error(error_msg, {"exception": str(e), "data": str(data)})
                return False
        return False
                
    def is_processing_kb_query(self):
        """Check if we're currently processing a knowledge base query."""
        return self._processing_kb_query
