#!/usr/bin/env python3
import boto3
import json
import os

# Initialize Bedrock Runtime client
bedrock_runtime = boto3.client(
    service_name='bedrock-runtime',
    region_name='us-east-1'
)

# Nova Lite model ID
NOVA_LITE_MODEL_ID = "amazon.nova-lite-v1:0"

# Test prompt
prompt = "What is Amazon Bedrock?"

# Try different request formats
request_formats = [
    # Format 1: Using messages with content as array
    {
        "messages": [
            {
                "role": "user", 
                "content": [
                    {"text": prompt}
                ]
            }
        ]
    },
    
    # Format 2: Using messages with content as array and inference parameters
    {
        "messages": [
            {
                "role": "user", 
                "content": [
                    {"text": prompt}
                ]
            }
        ],
        "inference_config": {
            "temperature": 0.7,
            "top_p": 0.9,
            "max_tokens": 500
        }
    },
    
    # Format 3: Using messages with content as array and Amazon format parameters
    {
        "messages": [
            {
                "role": "user", 
                "content": [
                    {"text": prompt}
                ]
            }
        ],
        "inferenceConfig": {
            "temperature": 0.7,
            "topP": 0.9,
            "maxTokens": 500
        }
    }
]

# Try each format
for i, request_body in enumerate(request_formats):
    print(f"\nTrying format {i+1}:")
    print(json.dumps(request_body, indent=2))
    
    try:
        response = bedrock_runtime.invoke_model(
            modelId=NOVA_LITE_MODEL_ID,
            body=json.dumps(request_body)
        )
        
        # Parse the response
        response_body = json.loads(response['body'].read().decode('utf-8'))
        print("\nSuccess! Response:")
        print(json.dumps(response_body, indent=2))
        print("\nResponse structure keys:", list(response_body.keys()))
        
        # Break after first successful format
        break
        
    except Exception as e:
        print(f"\nError with format {i+1}: {str(e)}")
        continue

print("\nTest completed.")
