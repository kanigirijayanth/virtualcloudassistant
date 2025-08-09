# /*********************************************************************************************************************
# *  Copyright 2025 Amazon.com, Inc. or its affiliates. All Rights Reserved.                                           *
# *                                                                                                                    *
# *  Licensed under the Amazon Software License (the "License"). You may not use this file except in compliance        *
# *  with the License. A copy of the License is located at                                                             *
# *                                                                                                                    *
# *      http://aws.amazon.com/asl/                                                                                    *
# *                                                                                                                    *
# *  or in the "license" file accompanying this file. This file is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES *
# *  OR CONDITIONS OF ANY KIND, express or implied. See the License for the specific language governing permissions    *
# *  and limitations under the License.                                                                                *
# **********************************************************************************************************************/

"""
FastAPI WebSocket Server for Virtual Cloud Assistant

This module implements a WebSocket server using FastAPI that handles real-time audio communication
between clients and an AI cloud assistant powered by AWS Nova Sonic. It processes audio streams,
manages transcription, and coordinates responses through a pipeline architecture.

Key Components:
- WebSocket endpoint for real-time audio streaming
- Audio processing pipeline with VAD (Voice Activity Detection)
- Integration with AWS Nova Sonic LLM service
- Context management for conversation history
- Credential management for AWS services

Dependencies:
- FastAPI for WebSocket server
- Pipecat for audio processing pipeline
- AWS Bedrock for LLM services
- Silero VAD for voice activity detection

Environment Variables:
- AWS_CONTAINER_CREDENTIALS_RELATIVE_URI: URI for AWS container credentials
- AWS_ACCESS_KEY_ID: AWS access key
- AWS_SECRET_ACCESS_KEY: AWS secret key
- AWS_SESSION_TOKEN: AWS session token
"""

import asyncio
import json
import base64
import traceback
import boto3
import os
import pandas as pd
import psutil
import gc
from datetime import datetime
from pathlib import Path

import httpx
from fastapi import FastAPI, WebSocket, Request, Response
import uvicorn

from pipecat.adapters.schemas.function_schema import FunctionSchema
from pipecat.adapters.schemas.tools_schema import ToolsSchema
from pipecat.audio.vad.silero import SileroVADAnalyzer, VADParams
from pipecat.pipeline.pipeline import Pipeline
from pipecat.pipeline.runner import PipelineRunner
from pipecat.pipeline.task import PipelineParams, PipelineTask
from pipecat.processors.aggregators.openai_llm_context import OpenAILLMContext
# from pipecat.services.aws_nova_sonic.aws import AWSNovaSonicLLMService, Params
from aws import AWSNovaSonicLLMService, Params
from pipecat.services.llm_service import FunctionCallParams
from pipecat.transports.base_transport import BaseTransport, TransportParams
from pipecat.transports.network.fastapi_websocket import FastAPIWebsocketTransport, FastAPIWebsocketParams
from pipecat.serializers.plivo import PlivoFrameSerializer
from pipecat.processors.logger import FrameLogger
from pipecat.processors.transcript_processor import TranscriptProcessor

from base64_serializer import Base64AudioSerializer
from custom_nova_sonic import CustomNovaSonicService

SAMPLE_RATE = 16000
API_KEY = "sk_live_51NzQWHSIANER2vP8kTGkZQBfwwQCzVQT"

# Global variable to track last credential refresh time
_last_credential_refresh = 0
_credential_refresh_interval = 300  # 5 minutes

def update_dredentials():
    """
    Updates AWS credentials by fetching from ECS container metadata endpoint.
    Used in containerized environments to maintain fresh credentials.
    Now includes caching to prevent excessive refresh calls.
    """
    global _last_credential_refresh
    import time
    
    current_time = time.time()
    
    # Only refresh if more than 5 minutes have passed since last refresh
    if current_time - _last_credential_refresh < _credential_refresh_interval:
        print(f"Skipping credential refresh - last refresh was {current_time - _last_credential_refresh:.1f} seconds ago")
        return
    
    try:
        uri = os.environ.get("AWS_CONTAINER_CREDENTIALS_RELATIVE_URI")
        if uri:
            print("Fetching fresh AWS credentials for Bedrock client", flush=True)
            with httpx.Client() as client:
                response = client.get(f"http://169.254.170.2{uri}")
                if response.status_code == 200:
                    creds = response.json()
                    os.environ["AWS_ACCESS_KEY_ID"] = creds["AccessKeyId"]
                    os.environ["AWS_SECRET_ACCESS_KEY"] = creds["SecretAccessKey"]
                    os.environ["AWS_SESSION_TOKEN"] = creds["Token"]
                    _last_credential_refresh = current_time
                    print("AWS credentials refreshed successfully", flush=True)
                else:
                    print(f"Failed to fetch fresh credentials: {response.status_code}", flush=True)
    except Exception as e:
        print(f"Error refreshing credentials: {str(e)}", flush=True)

import os
from aws_account_service import AWSAccountService
from aws_account_functions import (
    get_account_details,
    get_accounts_by_classification,
    get_classification_summary,
    get_management_type_summary,
    get_total_cost,
    get_account_status_summary,
    get_accounts_by_year,
    get_accounts_by_year_summary
)

# Import Bedrock agent functions
from bedrock_agent_functions import (
    query_bedrock_agent,
    initialize_bedrock_agent_client,
    refresh_bedrock_agent_client
)

# Import Bedrock knowledge base functions
from bedrock_kb_functions import (
    query_knowledge_base,
    get_document_by_id,
    search_documents
)

# Update the AWS account service with the absolute path to the CSV file
csv_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "AWS_AccountDetails.csv")
print(f"Setting AWS account service CSV path to: {csv_path}")
aws_service = AWSAccountService(csv_path)

# Set the aws_service in aws_account_functions
import aws_account_functions
aws_account_functions.aws_service = aws_service

# Define function schemas for AWS account operations
account_details_function = FunctionSchema(
    name="get_account_details",
    description="Get detailed information about an AWS account by account number or name. You must provide either account_number or account_name.",
    properties={
        "account_number": {
            "type": "string",
            "description": "The AWS account number to look up (e.g., '100942612345').",
        },
        "account_name": {
            "type": "string",
            "description": "The AWS account name to look up (e.g., 'AWS Project 10').",
        }
    },
    required=[]  # Neither parameter is required individually, but one must be provided
)

accounts_by_classification_function = FunctionSchema(
    name="get_accounts_by_classification",
    description="Get all AWS accounts with a specific classification.",
    properties={
        "classification": {
            "type": "string",
            "description": "The classification to filter accounts by (e.g., Class-1, Class-2, Class-3).",
        }
    },
    required=["classification"]
)

classification_summary_function = FunctionSchema(
    name="get_classification_summary",
    description="Get a summary of AWS accounts by classification, including count and total cost.",
    properties={},
    required=[]
)

management_type_summary_function = FunctionSchema(
    name="get_management_type_summary",
    description="Get a summary of AWS accounts by management type, including count and total cost.",
    properties={},
    required=[]
)

total_cost_function = FunctionSchema(
    name="get_total_cost",
    description="Get the total cost of all AWS accounts in Indian Rupees.",
    properties={},
    required=[]
)

account_status_summary_function = FunctionSchema(
    name="get_account_status_summary",
    description="Get a summary of AWS accounts by status (ACTIVE, CLOSED, SUSPENDED, etc.).",
    properties={},
    required=[]
)

accounts_by_year_function = FunctionSchema(
    name="get_accounts_by_year",
    description="Get all AWS accounts provisioned in a specific year.",
    properties={
        "year": {
            "type": "string",
            "description": "The year to filter accounts by (e.g., 2019, 2020, 2021).",
        }
    },
    required=["year"]
)

accounts_by_year_summary_function = FunctionSchema(
    name="get_accounts_by_year_summary",
    description="Get a summary of AWS accounts provisioned by year, showing count for each year.",
    properties={},
    required=[]
)

# Define function schemas for Bedrock knowledge base operations
query_kb_function = FunctionSchema(
    name="query_knowledge_base",
    description="Query the Bedrock knowledge base with a specific question about SOPs, LLDs, HLDs, or project operations.",
    properties={
        "query": {
            "type": "string",
            "description": "The question to ask the knowledge base (e.g., 'What is the backup procedure for the database?').",
        },
        "max_results": {
            "type": "integer",
            "description": "Maximum number of results to return (default: 5).",
        }
    },
    required=["query"]
)

get_document_function = FunctionSchema(
    name="get_document_by_id",
    description="Retrieve a specific document from the knowledge base by its ID.",
    properties={
        "document_id": {
            "type": "string",
            "description": "The ID of the document to retrieve.",
        }
    },
    required=["document_id"]
)

search_documents_function = FunctionSchema(
    name="search_documents",
    description="Search for documents in the knowledge base based on keywords and optional document type.",
    properties={
        "keywords": {
            "type": "string",
            "description": "Keywords to search for in the documents.",
        },
        "document_type": {
            "type": "string",
            "description": "Optional filter for document type (SOP, LLD, HLD).",
        },
        "max_results": {
            "type": "integer",
            "description": "Maximum number of results to return (default: 10).",
        }
    },
    required=["keywords"]
)

# Create tools schema with all AWS account and knowledge base functions
tools = ToolsSchema(standard_tools=[
    # AWS Account functions
    account_details_function,
    accounts_by_classification_function,
    classification_summary_function,
    management_type_summary_function,
    total_cost_function,
    account_status_summary_function,
    accounts_by_year_function,
    accounts_by_year_summary_function,
    
    # Bedrock Knowledge Base functions
    query_kb_function,
    get_document_function,
    search_documents_function
])

async def setup(websocket: WebSocket):
    """
    Sets up the audio processing pipeline and WebSocket connection.
    
    Args:
        websocket: The WebSocket connection to set up

    Configures:
    - Audio transport with VAD and transcription
    - AWS Nova Sonic LLM service
    - Context management
    - Event handlers for client connection/disconnection
    """
    update_dredentials()
    
    # Refresh Bedrock agent client
    refresh_bedrock_agent_client()
    
    # Initialize CloudWatch logger if available
    try:
        from cloudwatch_logger import initialize_cloudwatch_client, ensure_log_group_exists, create_log_stream
        print("Initializing CloudWatch logger...")
        initialize_cloudwatch_client()
        ensure_log_group_exists()
        log_stream = create_log_stream()
        print(f"CloudWatch logging enabled with log stream: {log_stream}")
    except ImportError:
        print("CloudWatch logger not available, logging will be disabled")
    except Exception as e:
        print(f"Error initializing CloudWatch logger: {str(e)}")
        traceback.print_exc()
    
    system_instruction = Path('prompt.txt').read_text() + f"\n{AWSNovaSonicLLMService.AWAIT_TRIGGER_ASSISTANT_RESPONSE_INSTRUCTION}"

    # Configure WebSocket transport with audio processing capabilities
    transport = FastAPIWebsocketTransport(websocket, FastAPIWebsocketParams(
        serializer=Base64AudioSerializer(),
        audio_in_enabled=True,
        audio_out_enabled=True,
        add_wav_header=False,
        vad_analyzer=SileroVADAnalyzer(
            params=VADParams(stop_secs=0.5)
        ),
        transcription_enabled=True
    ))

    # Configure AWS Nova Sonic parameters
    params = Params()
    params.input_sample_rate = SAMPLE_RATE
    params.output_sample_rate = SAMPLE_RATE

    # Initialize LLM service
    llm = CustomNovaSonicService(
        secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
        access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
        session_token=os.getenv("AWS_SESSION_TOKEN"),
        region='us-east-1',
        voice_id="tiffany",  # Available voices: matthew, tiffany, amy
        params=params
    )
    
    # Set the transport for the custom service
    llm.set_transport(transport)

    # Register AWS account functions
    llm.register_function("get_account_details", get_account_details)
    llm.register_function("get_accounts_by_classification", get_accounts_by_classification)
    llm.register_function("get_classification_summary", get_classification_summary)
    llm.register_function("get_management_type_summary", get_management_type_summary)
    llm.register_function("get_total_cost", get_total_cost)
    llm.register_function("get_account_status_summary", get_account_status_summary)
    llm.register_function("get_accounts_by_year", get_accounts_by_year)
    llm.register_function("get_accounts_by_year_summary", get_accounts_by_year_summary)
    
    # Define wrapper functions that handle credential refresh with improved logging
    def wrapped_query_knowledge_base(query, max_results=5):
        try:
            print(f"KNOWLEDGE BASE QUERY CALLED: '{query}'")
            refresh_bedrock_agent_client()  # Refresh credentials before calling
            
            print(f"Calling query_knowledge_base with query: '{query}', max_results: {max_results}")
            result = query_knowledge_base(query, max_results)
            
            print(f"Knowledge base query result status: {result.get('status')}")
            if result.get('status') == 'success':
                print(f"Found {len(result.get('results', []))} documents")
                if 'generated_answer' in result:
                    print(f"Generated answer length: {len(result.get('generated_answer', ''))}")
                    print(f"Generated answer preview: {result.get('generated_answer', '')[:100]}...")
                    
                    # Log the full generated answer for debugging
                    print(f"FULL GENERATED ANSWER: {result.get('generated_answer', '')}")
                    
                    # Import CloudWatch logger if available
                    try:
                        from cloudwatch_logger import log_knowledge_base_response
                        log_knowledge_base_response(query, result)
                    except ImportError:
                        pass
            
            return result
        except Exception as e:
            print(f"ERROR in wrapped_query_knowledge_base: {str(e)}")
            traceback.print_exc()
            
            # Log the error to CloudWatch if available
            try:
                from cloudwatch_logger import log_error
                log_error(f"Error in wrapped_query_knowledge_base: {str(e)}", {
                    "query": query,
                    "max_results": max_results,
                    "exception": str(e),
                    "traceback": traceback.format_exc()
                })
            except ImportError:
                pass
                
            return {
                'status': 'error',
                'message': f"Knowledge base query failed: {str(e)}",
                'query': query,
                'results': []
            }

    def wrapped_get_document_by_id(document_id):
        try:
            print(f"GET DOCUMENT CALLED with ID: {document_id}")
            refresh_bedrock_agent_client()  # Refresh credentials before calling
            
            print(f"Calling get_document_by_id with document_id: {document_id}")
            result = get_document_by_id(document_id)
            
            print(f"Get document result status: {result.get('status')}")
            if result.get('status') == 'success':
                print(f"Document content length: {len(result.get('content', ''))}")
                print(f"Document source: {result.get('source', 'Unknown')}")
                
                # Log the document retrieval to CloudWatch if available
                try:
                    from cloudwatch_logger import log_knowledge_base_response
                    log_knowledge_base_response(f"document_id:{document_id}", result)
                except ImportError:
                    pass
            
            return result
        except Exception as e:
            print(f"ERROR in wrapped_get_document_by_id: {str(e)}")
            traceback.print_exc()
            
            # Log the error to CloudWatch if available
            try:
                from cloudwatch_logger import log_error
                log_error(f"Error in wrapped_get_document_by_id: {str(e)}", {
                    "document_id": document_id,
                    "exception": str(e),
                    "traceback": traceback.format_exc()
                })
            except ImportError:
                pass
                
            return {
                'status': 'error',
                'message': f"Document retrieval failed: {str(e)}",
                'document_id': document_id
            }

    def wrapped_search_documents(keywords, document_type=None, max_results=10):
        try:
            print(f"SEARCH DOCUMENTS CALLED with keywords: '{keywords}', type: {document_type}")
            refresh_bedrock_agent_client()  # Refresh credentials before calling
            
            print(f"Calling search_documents with keywords: '{keywords}', document_type: {document_type}, max_results: {max_results}")
            result = search_documents(keywords, document_type, max_results)
            
            print(f"Search documents result status: {result.get('status')}")
            if result.get('status') == 'success':
                print(f"Found {len(result.get('results', []))} documents")
                for i, doc in enumerate(result.get('results', [])[:2]):
                    print(f"Document {i+1}: {doc.get('title', 'Unknown')} - {doc.get('source', 'Unknown')}")
                
                # Log the search results to CloudWatch if available
                try:
                    from cloudwatch_logger import log_knowledge_base_response
                    log_knowledge_base_response(f"search:{keywords}", result)
                except ImportError:
                    pass
            
            return result
        except Exception as e:
            print(f"ERROR in wrapped_search_documents: {str(e)}")
            traceback.print_exc()
            
            # Log the error to CloudWatch if available
            try:
                from cloudwatch_logger import log_error
                log_error(f"Error in wrapped_search_documents: {str(e)}", {
                    "keywords": keywords,
                    "document_type": document_type,
                    "max_results": max_results,
                    "exception": str(e),
                    "traceback": traceback.format_exc()
                })
            except ImportError:
                pass
                
            return {
                'status': 'error',
                'message': f"Document search failed: {str(e)}",
                'keywords': keywords,
                'results': []
            }

    # Register Bedrock knowledge base functions using wrapper functions
    llm.register_function("query_knowledge_base", wrapped_query_knowledge_base)
    llm.register_function("get_document_by_id", wrapped_get_document_by_id)
    llm.register_function("search_documents", wrapped_search_documents)

    # Set up conversation context with message limits to prevent memory bloat
    context = OpenAILLMContext(
        messages=[
            {"role": "system", "content": f"{system_instruction}"},
        ],
        tools=tools,
        max_messages=20  # Limit to last 20 messages to prevent memory accumulation
    )
    context_aggregator = llm.create_context_aggregator(context)

    # Create transcript processor
    transcript = TranscriptProcessor()

    # Configure processing pipeline
    pipeline = Pipeline(
        [
            transport.input(),  # Transport user input
            context_aggregator.user(),
            llm, 
            transport.output(),  # Transport bot output
            transcript.user(),
            transcript.assistant(), 
            context_aggregator.assistant(),
        ]
    )
    
    # Set up message handler for configuration messages
    async def handle_config_message(message):
        try:
            # Parse the message as JSON
            config = json.loads(message)
            
            # Check if this is a configuration message
            if config.get('type') == 'config':
                print(f"Processing configuration message: {config}")
                
                # Extract Bedrock agent configuration
                agent_id = config.get('bedrockAgentId')
                agent_alias_id = config.get('bedrockAgentAliasId')
                
                # Configure the Bedrock agent in the LLM service
                if agent_id and agent_alias_id:
                    print(f"Setting Bedrock agent configuration: agent_id={agent_id}, agent_alias_id={agent_alias_id}")
                    llm.set_bedrock_agent_config(agent_id, agent_alias_id)
        except Exception as e:
            print(f"Error handling configuration message: {e}")
            traceback.print_exc()
    
    # Register the message handler with the transport
    if hasattr(transport, 'websocket'):
        # Set up a message handler for the WebSocket
        original_receive = transport.websocket.receive
        
        async def receive_wrapper():
            message = await original_receive()
            
            # Check if this is a text message that might be a configuration
            if message.get('type') == 'websocket.receive' and 'text' in message:
                text = message.get('text', '')
                if text.startswith('{'):
                    try:
                        await handle_config_message(text)
                    except Exception as e:
                        print(f"Error in receive_wrapper: {e}")
                        traceback.print_exc()
            
            return message
        
        # Replace the receive method with our wrapper
        transport.websocket.receive = receive_wrapper

    # Create pipeline task with memory management
    task = PipelineTask(
        pipeline,
        params=PipelineParams(
            allow_interruptions=True,
            enable_metrics=True,
            enable_usage_metrics=True,
            audio_in_sample_rate=SAMPLE_RATE,
            audio_out_sample_rate=SAMPLE_RATE
        ),
    )

    @transport.event_handler("on_client_connected")
    async def on_client_connected(transport, client):
        """Handles new client connections and initiates conversation."""
        print(f"Client connected")
        await task.queue_frames([context_aggregator.user().get_context_frame()])
        await llm.trigger_assistant_response()

    @transport.event_handler("on_client_disconnected")
    async def on_client_disconnected(transport, client):
        """Handles client disconnection and cleanup."""
        print(f"Client disconnected")
        
        # Cancel the task
        await task.cancel()
        
        # Force cleanup
        try:
            # Stop any ongoing heartbeat tasks in the custom service
            if hasattr(llm, '_stop_heartbeat_audio'):
                llm._stop_heartbeat_audio()
            
            # Force garbage collection
            gc.collect()
            
            # Log final memory state
            memory_percent = psutil.virtual_memory().percent
            print(f"Client disconnected - Final memory usage: {memory_percent:.1f}%")
            
        except Exception as e:
            print(f"Error during cleanup: {str(e)}")

    # Counter for tracking interactions for memory management
    interaction_counter = 0

    @transcript.event_handler("on_transcript_update")
    async def handle_transcript_update(processor, frame):
        """Logs transcript updates with timestamps and manages memory."""
        nonlocal interaction_counter
        
        for message in frame.messages:
            print(f"Transcript: [{message.timestamp}] {message.role}: {message.content}")
            
            # Increment interaction counter for memory management
            if message.role in ["user", "assistant"]:
                interaction_counter += 1
                
                # Force garbage collection every 5 interactions
                if interaction_counter % 5 == 0:
                    gc.collect()
                    
                    # Monitor memory usage
                    try:
                        memory_percent = psutil.virtual_memory().percent
                        memory_used_mb = psutil.virtual_memory().used / (1024 * 1024)
                        print(f"Memory usage: {memory_percent:.1f}% ({memory_used_mb:.1f} MB) - Interaction #{interaction_counter}")
                        
                        if memory_percent > 80:
                            print(f"WARNING: High memory usage detected: {memory_percent:.1f}%")
                            # Force additional cleanup
                            gc.collect()
                            
                        # Reset counter to prevent overflow
                        if interaction_counter >= 100:
                            interaction_counter = 0
                            
                    except Exception as e:
                        print(f"Error monitoring memory: {str(e)}")
            
            # Check if this is a knowledge base related message
            if message.role == "assistant" and any(kb_term in message.content.lower() for kb_term in 
                                                ["knowledge base", "documentation", "found information", "sop", "lld", "hld"]):
                try:
                    from cloudwatch_logger import log_nova_sonic_input
                    log_nova_sonic_input(f"Nova Sonic response: {message.content}")
                except ImportError:
                    pass

    runner = PipelineRunner(handle_sigint=False, force_gc=True)
    await runner.run(task)

# Initialize FastAPI application
app = FastAPI()

@app.get('/health')
async def health(request: Request):
    """Health check endpoint."""
    return 'ok'

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """
    WebSocket endpoint handling client connections.
    Validates API key and sets up the audio processing pipeline.
    """
    protocol = websocket.headers.get('sec-websocket-protocol')
    print('protocol ', protocol)

    await websocket.accept(subprotocol=API_KEY)
    await setup(websocket)

# Configure and start uvicorn server
server = uvicorn.Server(uvicorn.Config(
    app=app,
    host='0.0.0.0',
    port=8000,
    log_level="error"
))

async def serve():
    """Starts the FastAPI server."""
    await server.serve()

# Run the server
asyncio.run(serve())
