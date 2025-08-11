#!/usr/bin/env python3
"""
Test script to simulate how the agent calls functions
"""

import os
import sys
import asyncio
import json
from aws_account_service import AWSAccountService

# Mock FunctionCallParams class
class MockFunctionCallParams:
    def __init__(self, arguments=None):
        self.arguments = arguments or {}
        self.results = []
    
    async def result_callback(self, result):
        self.results.append(result)
        print(f"Function result: {json.dumps(result, indent=2)}")

async def test_agent_function_calls():
    """Test how the agent would call the functions"""
    
    # Initialize the service
    csv_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "AWS_AccountDetails.csv")
    print(f"Using CSV path: {csv_path}")
    
    aws_service = AWSAccountService(csv_path)
    
    # Import the functions
    from aws_account_functions import count_all_aws_accounts, calculate_total_cost_rupees
    
    # Set the service
    import aws_account_functions
    aws_account_functions.aws_service = aws_service
    
    print("\n=== Simulating agent call to count_all_aws_accounts ===")
    print("User query: 'How many AWS accounts do we have?'")
    print("Agent should call: count_all_aws_accounts()")
    
    # Simulate the function call with empty arguments (as it should be)
    params1 = MockFunctionCallParams(arguments={})
    await count_all_aws_accounts(params1)
    
    print("\n=== Simulating agent call to calculate_total_cost_rupees ===")
    print("User query: 'What is the total cost of all AWS accounts?'")
    print("Agent should call: calculate_total_cost_rupees()")
    
    # Simulate the function call with empty arguments (as it should be)
    params2 = MockFunctionCallParams(arguments={})
    await calculate_total_cost_rupees(params2)
    
    print("\n=== Testing with various argument formats ===")
    
    # Test with None arguments
    print("\nTesting with None arguments:")
    params3 = MockFunctionCallParams(arguments=None)
    await count_all_aws_accounts(params3)
    
    # Test with extra arguments (should be ignored)
    print("\nTesting with extra arguments (should be ignored):")
    params4 = MockFunctionCallParams(arguments={"extra_param": "should_be_ignored"})
    await calculate_total_cost_rupees(params4)
    
    print("\n=== All tests completed successfully ===")

if __name__ == "__main__":
    asyncio.run(test_agent_function_calls())
