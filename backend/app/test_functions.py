#!/usr/bin/env python3
"""
Test script to verify AWS account functions work correctly
"""

import os
import sys
import asyncio
from aws_account_service import AWSAccountService

# Mock params class for testing
class MockParams:
    def __init__(self):
        self.arguments = {}
        self.results = []
    
    async def result_callback(self, result):
        self.results.append(result)
        print(f"Function result: {result}")

async def test_functions():
    """Test the AWS account functions"""
    
    # Initialize the service
    csv_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "AWS_AccountDetails.csv")
    print(f"Using CSV path: {csv_path}")
    print(f"CSV file exists: {os.path.exists(csv_path)}")
    
    aws_service = AWSAccountService(csv_path)
    
    # Import the functions
    from aws_account_functions import count_all_aws_accounts, calculate_total_cost_rupees
    
    # Set the service
    import aws_account_functions
    aws_account_functions.aws_service = aws_service
    
    print("\n=== Testing count_all_aws_accounts ===")
    params1 = MockParams()
    await count_all_aws_accounts(params1)
    
    print("\n=== Testing calculate_total_cost_rupees ===")
    params2 = MockParams()
    await calculate_total_cost_rupees(params2)
    
    print("\n=== Direct service tests ===")
    print(f"Direct service count: {aws_service.get_total_account_count()}")
    print(f"Direct service cost: {aws_service.get_total_cost()}")
    
    print("\n=== Test completed ===")

if __name__ == "__main__":
    asyncio.run(test_functions())
