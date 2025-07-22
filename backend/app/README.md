# Virtual Cloud Assistant Backend

This directory contains the backend code for the Virtual Cloud Assistant, which provides information about AWS accounts through a voice interface powered by Amazon Nova Sonic.

## Components

- **main.py**: Main application entry point that sets up the FastAPI WebSocket server and Nova Sonic integration
- **aws_account_service.py**: Service for handling AWS account data operations
- **aws_account_functions.py**: Functions that interface with the AWS account service to provide data to the voice assistant
- **base64_serializer.py**: Custom serializer for handling audio data over WebSockets
- **AWS_AccountDetails.csv**: CSV file containing AWS account data

## AWS Account Functions

The Virtual Cloud Assistant can provide the following information:

1. **Account Details**
   - AWS Account Number (read digit by digit)
   - AWS Account Name
   - Provisioning Date
   - Status
   - Classification
   - Management Type
   - Total Cost of Account in Indian Rupees

2. **Account Analysis**
   - List of all accounts as per classification
   - Total number of accounts under respective classification
   - Cost of each AWS Account
   - Cost of all AWS Accounts
   - Cost of AWS Account under each Classification or Management Type
   - Detailed information for a specific account by name or number

## Testing

You can test the AWS account service functionality using the `test_aws_service.py` script:

```bash
python test_aws_service.py
```

## Running the Application

To run the application:

```bash
python main.py
```

This will start the FastAPI WebSocket server on port 8000.

## Dependencies

See `requirements.txt` for a list of dependencies.