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
Bedrock Agent Integration Functions

This module provides functions to interact with Amazon Bedrock Agents.
It allows querying a Bedrock agent for project documentation.
"""

import boto3
import json
import traceback
import time
from typing import Dict, Any, Optional

# Global variables for Bedrock clients
bedrock_agent_runtime = None
bedrock_region = None

def initialize_bedrock_agent_client(region: str) -> None:
    """
    Initialize the Bedrock agent runtime client.
    
    Args:
        region: AWS region for Bedrock
    """
    global bedrock_agent_runtime, bedrock_region
    
    try:
        bedrock_region = region
        bedrock_agent_runtime = boto3.client('bedrock-agent-runtime', region_name=region)
        print(f"Initialized Bedrock agent runtime client in region {region}")
    except Exception as e:
        print(f"Error initializing Bedrock agent runtime client: {str(e)}")
        traceback.print_exc()
        raise

def refresh_bedrock_agent_client() -> None:
    """
    Refresh the Bedrock agent runtime client with current credentials.
    """
    global bedrock_agent_runtime, bedrock_region
    
    if bedrock_region:
        try:
            bedrock_agent_runtime = boto3.client('bedrock-agent-runtime', region_name=bedrock_region)
            print(f"Refreshed Bedrock agent runtime client in region {bedrock_region}")
        except Exception as e:
            print(f"Error refreshing Bedrock agent runtime client: {str(e)}")
            traceback.print_exc()

def query_bedrock_agent(
    agent_id: str,
    agent_alias_id: str,
    query: str,
    session_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Query a Bedrock agent with a specific question.
    
    Args:
        agent_id: The ID of the Bedrock agent
        agent_alias_id: The alias ID of the Bedrock agent
        query: The query to send to the agent
        session_id: Optional session ID for conversation continuity
        
    Returns:
        Dict containing the agent's response
    """
    global bedrock_agent_runtime
    
    if not bedrock_agent_runtime:
        raise ValueError("Bedrock agent runtime client not initialized")
    
    try:
        # Generate a session ID if not provided
        if not session_id:
            session_id = f"session-{int(time.time())}"
        
        # Prepare the request
        request = {
            "inputText": query,
            "enableTrace": True
        }
        
        # Call the Bedrock agent
        print(f"Calling Bedrock agent {agent_id} (alias {agent_alias_id}) with query: '{query}'")
        response = bedrock_agent_runtime.invoke_agent(
            agentId=agent_id,
            agentAliasId=agent_alias_id,
            sessionId=session_id,
            inputText=query
        )
        
        # Process the response
        completion = ""
        trace_info = {}
        
        # Extract the completion from the response chunks
        for event in response.get('completion'):
            chunk = json.loads(event['chunk']['bytes'].decode())
            if 'completion' in chunk:
                completion += chunk['completion']
            if 'trace' in chunk:
                trace_info = chunk['trace']
        
        # Format the response
        result = {
            "status": "success",
            "completion": completion,
            "agentId": agent_id,
            "agentAliasId": agent_alias_id,
            "sessionId": session_id,
            "trace": trace_info
        }
        
        # Log the response
        print(f"Bedrock agent query successful. Response length: {len(completion)}")
        
        # Try to log to CloudWatch if available
        try:
            from cloudwatch_logger import log_bedrock_agent_response
            log_bedrock_agent_response(query, result)
        except ImportError:
            pass
        except Exception as e:
            print(f"Error logging to CloudWatch: {str(e)}")
        
        return result
        
    except Exception as e:
        error_message = f"Error querying Bedrock agent: {str(e)}"
        print(error_message)
        traceback.print_exc()
        
        # Try to log to CloudWatch if available
        try:
            from cloudwatch_logger import log_error
            log_error(error_message, {
                "query": query,
                "agent_id": agent_id,
                "agent_alias_id": agent_alias_id
            })
        except ImportError:
            pass
        except Exception as log_error:
            print(f"Error logging to CloudWatch: {str(log_error)}")
        
        return {
            "status": "error",
            "error": str(e),
            "agentId": agent_id,
            "agentAliasId": agent_alias_id
        }
