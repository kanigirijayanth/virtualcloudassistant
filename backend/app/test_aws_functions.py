#!/usr/bin/env python3
"""
Test script for AWS Account Service with direct function calls

This script tests the AWS Account Service functionality by directly calling
the functions that would be called by the LLM.
"""

import asyncio
import os
from aws_account_service import AWSAccountService

class MockParams:
    def __init__(self, arguments):
        self.arguments = arguments
        self.results = None
    
    async def result_callback(self, result):
        self.results = result
        print(f"Result: {result}")

async def test_get_account_details():
    """Test the get_account_details function."""
    from aws_account_functions import get_account_details
    
    # Set up the AWS account service
    csv_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "AWS_AccountDetails.csv")
    print(f"Using CSV path: {csv_path}")
    aws_service = AWSAccountService(csv_path)
    
    # Set the aws_service in aws_account_functions
    import aws_account_functions
    aws_account_functions.aws_service = aws_service
    
    # Test with account number
    print("\nTesting get_account_details with account number:")
    params = MockParams({"account_number": "100942612345"})
    await get_account_details(params)
    
    # Test with account name
    print("\nTesting get_account_details with account name:")
    params = MockParams({"account_name": "AWS Project 10"})
    await get_account_details(params)
    
    # Test with invalid account number
    print("\nTesting get_account_details with invalid account number:")
    params = MockParams({"account_number": "999999999999"})
    await get_account_details(params)
    
    # Test with invalid account name
    print("\nTesting get_account_details with invalid account name:")
    params = MockParams({"account_name": "Nonexistent Account"})
    await get_account_details(params)
    
    # Test with no parameters
    print("\nTesting get_account_details with no parameters:")
    params = MockParams({})
    await get_account_details(params)

async def main():
    """Main test function."""
    print("Testing AWS Account Functions...")
    await test_get_account_details()
    print("\nAll tests completed!")

if __name__ == "__main__":
    asyncio.run(main())