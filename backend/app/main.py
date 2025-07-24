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

SAMPLE_RATE = 16000
API_KEY = "sk_live_51NzQWHSIANER2vP8kTGkZQBfwwQCzVQT"

def update_dredentials():
    """
    Updates AWS credentials by fetching from ECS container metadata endpoint.
    Used in containerized environments to maintain fresh credentials.
    """
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

# Create tools schema with all AWS account functions
tools = ToolsSchema(standard_tools=[
    account_details_function,
    accounts_by_classification_function,
    classification_summary_function,
    management_type_summary_function,
    total_cost_function,
    account_status_summary_function,
    accounts_by_year_function,
    accounts_by_year_summary_function
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
    llm = AWSNovaSonicLLMService(
        secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
        access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
        session_token=os.getenv("AWS_SESSION_TOKEN"),
        region='us-east-1',
        voice_id="tiffany",  # Available voices: matthew, tiffany, amy
        params=params
    )

    # Register AWS account functions
    llm.register_function("get_account_details", get_account_details)
    llm.register_function("get_accounts_by_classification", get_accounts_by_classification)
    llm.register_function("get_classification_summary", get_classification_summary)
    llm.register_function("get_management_type_summary", get_management_type_summary)
    llm.register_function("get_total_cost", get_total_cost)
    llm.register_function("get_account_status_summary", get_account_status_summary)
    llm.register_function("get_accounts_by_year", get_accounts_by_year)
    llm.register_function("get_accounts_by_year_summary", get_accounts_by_year_summary)

    # Set up conversation context
    context = OpenAILLMContext(
        messages=[
            {"role": "system", "content": f"{system_instruction}"},
        ],
        tools=tools,
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

    # Create pipeline task
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
        await task.cancel()

    @transcript.event_handler("on_transcript_update")
    async def handle_transcript_update(processor, frame):
        """Logs transcript updates with timestamps."""
        for message in frame.messages:
            print(f"Transcript: [{message.timestamp}] {message.role}: {message.content}")

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
