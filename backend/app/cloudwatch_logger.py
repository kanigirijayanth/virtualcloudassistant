"""
CloudWatch Logger for Virtual Cloud Assistant

This module provides functions to log messages to AWS CloudWatch Logs.
It's used to track knowledge base responses and debugging information.
"""

import boto3
import json
import time
import os
import uuid
import traceback
from datetime import datetime

# Initialize CloudWatch Logs client
logs_client = None

# Log group and stream names
LOG_GROUP_NAME = "/virtualcloudassistant/knowledge-base"
LOG_STREAM_PREFIX = "kb-responses-"

def initialize_cloudwatch_client():
    """Initialize the CloudWatch Logs client with the latest credentials."""
    global logs_client
    try:
        # Get credentials from environment variables
        access_key = os.environ.get("AWS_ACCESS_KEY_ID")
        secret_key = os.environ.get("AWS_SECRET_ACCESS_KEY")
        session_token = os.environ.get("AWS_SESSION_TOKEN")
        
        if not access_key or not secret_key:
            print("WARNING: Missing AWS credentials for CloudWatch Logs client")
            return False
            
        # Create new client with the latest credentials
        logs_client = boto3.client(
            service_name='logs',
            region_name='us-east-1',
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
            aws_session_token=session_token
        )
        
        print("CloudWatch Logs client initialized successfully")
        return True
        
    except Exception as e:
        print(f"ERROR initializing CloudWatch Logs client: {str(e)}")
        traceback.print_exc()
        return False

def ensure_log_group_exists():
    """Ensure the log group exists, creating it if necessary."""
    if not logs_client:
        if not initialize_cloudwatch_client():
            return False
    
    try:
        # Check if log group exists
        response = logs_client.describe_log_groups(
            logGroupNamePrefix=LOG_GROUP_NAME
        )
        
        # Create log group if it doesn't exist
        if not any(log_group['logGroupName'] == LOG_GROUP_NAME for log_group in response.get('logGroups', [])):
            logs_client.create_log_group(
                logGroupName=LOG_GROUP_NAME
            )
            print(f"Created log group: {LOG_GROUP_NAME}")
            
            # Set retention policy to 30 days
            logs_client.put_retention_policy(
                logGroupName=LOG_GROUP_NAME,
                retentionInDays=30
            )
            print(f"Set retention policy to 30 days for log group: {LOG_GROUP_NAME}")
        
        return True
        
    except Exception as e:
        print(f"ERROR ensuring log group exists: {str(e)}")
        traceback.print_exc()
        return False

def create_log_stream():
    """Create a new log stream with timestamp and random ID."""
    if not logs_client:
        if not initialize_cloudwatch_client():
            return None
    
    if not ensure_log_group_exists():
        return None
    
    try:
        # Create log stream with timestamp and random ID
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        random_id = str(uuid.uuid4())[:8]
        log_stream_name = f"{LOG_STREAM_PREFIX}{timestamp}-{random_id}"
        
        logs_client.create_log_stream(
            logGroupName=LOG_GROUP_NAME,
            logStreamName=log_stream_name
        )
        
        print(f"Created log stream: {log_stream_name}")
        return log_stream_name
        
    except Exception as e:
        print(f"ERROR creating log stream: {str(e)}")
        traceback.print_exc()
        return None

def log_to_cloudwatch(log_stream_name, message, level="INFO"):
    """
    Log a message to CloudWatch Logs.
    
    Args:
        log_stream_name: The name of the log stream
        message: The message to log (string or dict)
        level: The log level (INFO, WARNING, ERROR, DEBUG)
    """
    if not logs_client:
        if not initialize_cloudwatch_client():
            return False
    
    if not log_stream_name:
        log_stream_name = create_log_stream()
        if not log_stream_name:
            return False
    
    try:
        # Convert message to string if it's a dict
        if isinstance(message, dict):
            message = json.dumps(message, default=str)
        
        # Add timestamp and log level
        timestamp = int(time.time() * 1000)  # Milliseconds since epoch
        formatted_message = f"[{level}] {message}"
        
        # Get the sequence token if needed
        try:
            response = logs_client.describe_log_streams(
                logGroupName=LOG_GROUP_NAME,
                logStreamNamePrefix=log_stream_name
            )
            
            sequence_token = None
            for stream in response.get('logStreams', []):
                if stream['logStreamName'] == log_stream_name and 'uploadSequenceToken' in stream:
                    sequence_token = stream['uploadSequenceToken']
                    break
            
            # Put log event
            if sequence_token:
                logs_client.put_log_events(
                    logGroupName=LOG_GROUP_NAME,
                    logStreamName=log_stream_name,
                    logEvents=[
                        {
                            'timestamp': timestamp,
                            'message': formatted_message
                        }
                    ],
                    sequenceToken=sequence_token
                )
            else:
                logs_client.put_log_events(
                    logGroupName=LOG_GROUP_NAME,
                    logStreamName=log_stream_name,
                    logEvents=[
                        {
                            'timestamp': timestamp,
                            'message': formatted_message
                        }
                    ]
                )
            
            return True
            
        except logs_client.exceptions.ResourceNotFoundException:
            # Log stream doesn't exist, create it
            create_log_stream()
            return log_to_cloudwatch(log_stream_name, message, level)
            
        except logs_client.exceptions.InvalidSequenceTokenException as e:
            # Get the correct sequence token from the exception message
            import re
            match = re.search(r'sequenceToken is: (\S+)', str(e))
            if match:
                sequence_token = match.group(1)
                logs_client.put_log_events(
                    logGroupName=LOG_GROUP_NAME,
                    logStreamName=log_stream_name,
                    logEvents=[
                        {
                            'timestamp': timestamp,
                            'message': formatted_message
                        }
                    ],
                    sequenceToken=sequence_token
                )
                return True
            return False
            
    except Exception as e:
        print(f"ERROR logging to CloudWatch: {str(e)}")
        traceback.print_exc()
        return False

# Create a session-specific log stream for the current run
current_log_stream = None

def log_knowledge_base_request(query, max_results=5):
    """Log a knowledge base request to CloudWatch."""
    global current_log_stream
    if not current_log_stream:
        current_log_stream = create_log_stream()
    
    log_to_cloudwatch(current_log_stream, {
        "event_type": "kb_request",
        "timestamp": datetime.now().isoformat(),
        "query": query,
        "max_results": max_results
    })

def log_knowledge_base_response(query, result):
    """Log a knowledge base response to CloudWatch."""
    global current_log_stream
    if not current_log_stream:
        current_log_stream = create_log_stream()
    
    # Create a simplified version of the result for logging
    simplified_result = {
        "status": result.get("status"),
        "query": query,
        "num_results": len(result.get("results", [])),
        "has_generated_answer": "generated_answer" in result,
        "generated_answer_length": len(result.get("generated_answer", "")) if "generated_answer" in result else 0,
        "processing_time": result.get("processing_time")
    }
    
    # Add the first few results if available
    if "results" in result and result["results"]:
        simplified_result["first_result_preview"] = result["results"][0].get("content", "")[:200] + "..."
    
    # Add the generated answer preview if available
    if "generated_answer" in result:
        simplified_result["generated_answer_preview"] = result["generated_answer"][:200] + "..."
    
    log_to_cloudwatch(current_log_stream, {
        "event_type": "kb_response",
        "timestamp": datetime.now().isoformat(),
        "result": simplified_result
    })

def log_nova_sonic_input(message):
    """Log the input being sent to Nova Sonic."""
    global current_log_stream
    if not current_log_stream:
        current_log_stream = create_log_stream()
    
    log_to_cloudwatch(current_log_stream, {
        "event_type": "nova_sonic_input",
        "timestamp": datetime.now().isoformat(),
        "message": message[:500] + "..." if len(message) > 500 else message
    })

def log_error(error_message, context=None):
    """Log an error to CloudWatch."""
    global current_log_stream
    if not current_log_stream:
        current_log_stream = create_log_stream()
    
    log_data = {
        "event_type": "error",
        "timestamp": datetime.now().isoformat(),
        "error_message": error_message
    }
    
    if context:
        log_data["context"] = context
    
    log_to_cloudwatch(current_log_stream, log_data, level="ERROR")

# Initialize the CloudWatch client when the module is imported
initialize_cloudwatch_client()
