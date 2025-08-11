#!/usr/bin/env python3
"""
Test script for new date-based AWS account functions.
This script tests all the new date-based filtering capabilities.
"""

import os
import sys
from aws_account_service import AWSAccountService

def test_date_functions():
    """Test all new date-based functions."""
    
    # Initialize the service
    csv_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "AWS_AccountDetails.csv")
    print(f"Testing with CSV file: {csv_path}")
    print(f"CSV file exists: {os.path.exists(csv_path)}")
    
    aws_service = AWSAccountService(csv_path)
    
    print(f"\n=== BASIC SERVICE INFO ===")
    print(f"Total accounts: {aws_service.get_total_account_count()}")
    print(f"Total cost: {aws_service.get_total_cost()}")
    
    print(f"\n=== TEST 1: Get accounts by date range ===")
    # Test date range (first quarter of 2019)
    accounts = aws_service.get_accounts_by_date_range("01-Jan-19", "31-Mar-19")
    print(f"Accounts from 01-Jan-19 to 31-Mar-19: {len(accounts)}")
    for acc in accounts[:3]:  # Show first 3
        print(f"  - {acc['AWS account Name']} ({acc['AWS Account Number']}) - {acc['Provisioning Date']}")
    
    print(f"\n=== TEST 2: Get accounts by month/year ===")
    # Test specific month (April 2019)
    accounts = aws_service.get_accounts_by_month_year(4, 2019)
    print(f"Accounts from April 2019: {len(accounts)}")
    for acc in accounts[:3]:  # Show first 3
        print(f"  - {acc['AWS account Name']} ({acc['AWS Account Number']}) - {acc['Provisioning Date']}")
    
    print(f"\n=== TEST 3: Get accounts by specific date ===")
    # Test specific date
    accounts = aws_service.get_accounts_by_specific_date("31-Mar-19")
    print(f"Accounts from 31-Mar-19: {len(accounts)}")
    for acc in accounts:
        print(f"  - {acc['AWS account Name']} ({acc['AWS Account Number']}) - {acc['Provisioning Date']}")
    
    print(f"\n=== TEST 4: Get provisioning date summary ===")
    summary = aws_service.get_provisioning_date_summary()
    if summary:
        print(f"Earliest provisioning date: {summary.get('earliest_provisioning_date')}")
        print(f"Latest provisioning date: {summary.get('latest_provisioning_date')}")
        print(f"Total accounts: {summary.get('total_accounts')}")
        print(f"Date range (days): {summary.get('date_range_days')}")
        print(f"Monthly breakdown (first 5):")
        for month_data in summary.get('monthly_breakdown', [])[:5]:
            print(f"  - {month_data['month_year']}: {month_data['count']} accounts")
    
    print(f"\n=== TEST 5: Test edge cases ===")
    # Test invalid date range
    try:
        accounts = aws_service.get_accounts_by_date_range("invalid-date", "31-Dec-19")
        print(f"Invalid date range test: {len(accounts)} accounts (should be 0)")
    except Exception as e:
        print(f"Invalid date range test: Error caught - {str(e)}")
    
    # Test future date
    accounts = aws_service.get_accounts_by_specific_date("01-Jan-30")
    print(f"Future date test: {len(accounts)} accounts (should be 0)")
    
    # Test invalid month
    accounts = aws_service.get_accounts_by_month_year(13, 2019)
    print(f"Invalid month test: {len(accounts)} accounts (should be 0)")
    
    print(f"\n=== TEST 6: Compare with existing year function ===")
    # Compare new functions with existing year function
    accounts_2019_old = aws_service.get_accounts_by_year(2019)
    accounts_2019_new = aws_service.get_accounts_by_date_range("01-Jan-19", "31-Dec-19")
    print(f"2019 accounts (old function): {len(accounts_2019_old)}")
    print(f"2019 accounts (new function): {len(accounts_2019_new)}")
    print(f"Results match: {len(accounts_2019_old) == len(accounts_2019_new)}")

if __name__ == "__main__":
    test_date_functions()
