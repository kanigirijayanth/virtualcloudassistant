"""
Custom AWS Nova Sonic Service

This module extends the AWS Nova Sonic service to handle knowledge base responses.
It wraps the original service and adds functionality to send knowledge base responses to the frontend.
"""

import json
import time
import asyncio
import base64
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
        # Generate silent audio frames of different durations for keeping the audio buffer fed
        self._silent_audio_frames = self._generate_silent_audio_frames()
        # Flag to track if we're currently processing a knowledge base query
        self._processing_kb_query = False
    
    def set_transport(self, transport):
        """Set the transport to use for sending knowledge base responses."""
        self.transport = transport
    
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
    
    async def _send_json_to_client(self, data):
        """Send JSON data to the client using the transport's websocket send_text method."""
        if self.transport and hasattr(self.transport, 'websocket'):
            try:
                await self.transport.websocket.send_text(json.dumps(data))
                return True
            except Exception as e:
                print(f"Error sending JSON to client: {str(e)}")
                return False
        return False
    
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
            super().register_function(name, func)
    
    def _start_heartbeat_audio(self):
        """Start sending heartbeat audio frames to prevent buffer starvation."""
        if not hasattr(self, '_heartbeat_task') or self._heartbeat_task is None:
            self._heartbeat_running = True
            self._heartbeat_task = asyncio.create_task(self._send_heartbeat_audio())
    
    def _stop_heartbeat_audio(self):
        """Stop sending heartbeat audio frames."""
        self._heartbeat_running = False
        if hasattr(self, '_heartbeat_task') and self._heartbeat_task is not None:
            self._heartbeat_task.cancel()
            self._heartbeat_task = None
    
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
            print(f"Error in heartbeat audio task: {str(e)}")
    
    async def _send_silent_audio(self, duration_ms):
        """Send a silent audio frame of the specified duration."""
        if self.transport:
            try:
                await self._send_json_to_client({
                    "event": "media",
                    "data": self._silent_audio_frames[duration_ms]
                })
            except Exception as e:
                print(f"Error sending silent audio frame: {str(e)}")
                
    def is_processing_kb_query(self):
        """Check if we're currently processing a knowledge base query."""
        return self._processing_kb_query
