#!/usr/bin/env python3
"""
Test script for AWS Account Service

This script tests the AWS Account Service functionality by performing various queries
on the AWS account data and printing the results.
"""

from aws_account_service import AWSAccountService

def main():
    """Main test function."""
    print("Testing AWS Account Service...")
    
    # Initialize the service
    service = AWSAccountService()
    
    # Test getting account by number
    print("\n1. Testing get_account_by_number:")
    account = service.get_account_by_number("550558532874")  # Vortex account
    if account:
        print(f"Found account: {account['AWS account Name']}")
        print(f"Account number as digits: {service.get_account_number_as_digits(account['AWS Account Number'])}")
    else:
        print("Account not found")
    
    # Test getting account by name
    print("\n2. Testing get_account_by_name:")
    account = service.get_account_by_name("Vortex")
    if account:
        print(f"Found account number: {account['AWS Account Number']}")
        print(f"Status: {account['Status']}")
        print(f"Cost: {account['Cost of Account in Indian Rupees']}")
    else:
        print("Account not found")
    
    # Test getting accounts by classification
    print("\n3. Testing get_accounts_by_classification:")
    accounts = service.get_accounts_by_classification("Class-1")
    print(f"Found {len(accounts)} accounts with Class-1 classification")
    if accounts:
        print(f"First account: {accounts[0]['AWS account Name']}")
    
    # Test getting total accounts by classification
    print("\n4. Testing get_total_accounts_by_classification:")
    classification_counts = service.get_total_accounts_by_classification()
    for classification, count in classification_counts.items():
        print(f"{classification}: {count} accounts")
    
    # Test getting total cost
    print("\n5. Testing get_total_cost:")
    total_cost = service.get_total_cost()
    print(f"Total cost of all accounts: ₹{total_cost}")
    
    # Test getting total cost by classification
    print("\n6. Testing get_total_cost_by_classification:")
    classification_costs = service.get_total_cost_by_classification()
    for classification, cost in classification_costs.items():
        print(f"{classification}: ₹{cost}")
    
    # Test getting total cost by management type
    print("\n7. Testing get_total_cost_by_management_type:")
    management_costs = service.get_total_cost_by_management_type()
    for management_type, cost in management_costs.items():
        print(f"{management_type}: ₹{cost}")
    
    print("\nAll tests completed!")

if __name__ == "__main__":
    main()
