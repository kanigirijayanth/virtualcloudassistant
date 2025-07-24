# Bedrock Knowledge Base Integration

This document explains how the Bedrock Knowledge Base integration works in the Virtual Cloud Assistant.

## Overview

The Virtual Cloud Assistant now includes integration with Amazon Bedrock Knowledge Base, allowing users to query project documentation including SOPs, LLDs, and HLDs stored in an S3 bucket. The knowledge base ID `CLRDOVZGIY` is used to access these documents.

## Components

1. **Bedrock Knowledge Base Functions** (`bedrock_kb_functions.py`)
   - `query_knowledge_base`: Query the knowledge base with a specific question
   - `get_document_by_id`: Retrieve a specific document by ID
   - `search_documents`: Search for documents based on keywords and document type
   - `format_kb_response`: Format knowledge base responses for frontend display

2. **Custom Nova Sonic Service** (`custom_nova_sonic.py`)
   - Extends the AWS Nova Sonic service to handle knowledge base responses
   - Sends knowledge base responses directly to the frontend

3. **Frontend Components**
   - `KnowledgeBaseResult.js`: React component for displaying knowledge base results
   - Updated `Content.js` to display chat messages and knowledge base results

## How It Works

1. When a user asks a question related to project documentation, the LLM determines that it should use one of the knowledge base functions.
2. The function queries the Bedrock knowledge base and returns the results.
3. The custom Nova Sonic service intercepts the function call, formats the results, and sends them to the frontend.
4. The frontend displays the results in a structured format using the KnowledgeBaseResult component.
5. The LLM also receives the results and can incorporate them into its spoken response.

## Usage Examples

Users can ask questions like:

- "What are the backup procedures for our databases?"
- "Show me the high-level design documents for the project"
- "What's the standard operating procedure for incident response?"
- "Find documents related to network security"

## Permissions

The CDK stack has been updated to include the necessary permissions for accessing the Bedrock knowledge base:

```python
task_role.add_to_policy(
    iam.PolicyStatement(
        effect=iam.Effect.ALLOW,
        actions=[
            "bedrock:Retrieve",
            "bedrock:RetrieveAndGenerate"
        ],
        resources=[
            "arn:aws:bedrock:us-east-1:*:knowledge-base/*"
        ]
    )
)
```

## Troubleshooting

If knowledge base responses are not appearing:

1. Check that the knowledge base ID (`CLRDOVZGIY`) is correct
2. Verify that the IAM permissions are properly configured
3. Check the CloudWatch logs for any errors in the Bedrock API calls
4. Ensure the frontend is correctly rendering the knowledge base responses

## Future Enhancements

Potential future enhancements include:

1. Adding support for multiple knowledge bases
2. Implementing document filtering by metadata
3. Adding document preview capabilities
4. Supporting document upload through the frontend
5. Implementing relevance feedback for search results
