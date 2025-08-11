from typing import Dict, List, Any
import json

# The AWS account service instance will be imported from main.py
aws_service = None

async def get_account_details(params):
    """Get account details by account number or name."""
    print(f"get_account_details called with arguments: {params.arguments}")
    account_number = params.arguments.get("account_number")
    account_name = params.arguments.get("account_name")
    
    print(f"Looking up account - number: {account_number}, name: {account_name}")
    
    if account_number:
        account = aws_service.get_account_by_number(account_number)
        if account:
            # Format account number as digits
            digit_representation = aws_service.get_account_number_as_digits(account["AWS Account Number"])
            
            await params.result_callback({
                "found": True,
                "account_number": account["AWS Account Number"],
                "account_number_as_digits": digit_representation,
                "account_name": account["AWS account Name"],
                "provisioning_date": account["Provisioning Date"],
                "status": account["Status"],
                "classification": account["Classification"],
                "management_type": account["Management Type"],
                "cost": int(account["Cost of Account in Indian Rupees"])
            })
        else:
            await params.result_callback({
                "found": False,
                "message": f"No account found with account number {account_number}."
            })
    elif account_name:
        account = aws_service.get_account_by_name(account_name)
        if account:
            # Format account number as digits
            digit_representation = aws_service.get_account_number_as_digits(account["AWS Account Number"])
            
            await params.result_callback({
                "found": True,
                "account_number": account["AWS Account Number"],
                "account_number_as_digits": digit_representation,
                "account_name": account["AWS account Name"],
                "provisioning_date": account["Provisioning Date"],
                "status": account["Status"],
                "classification": account["Classification"],
                "management_type": account["Management Type"],
                "cost": int(account["Cost of Account in Indian Rupees"])
            })
        else:
            await params.result_callback({
                "found": False,
                "message": f"No account found with name {account_name}."
            })
    else:
        await params.result_callback({
            "found": False,
            "message": "Please provide either an account number or account name."
        })

async def get_accounts_by_classification(params):
    """Get accounts by classification."""
    classification = params.arguments.get("classification")
    
    if not classification:
        await params.result_callback({
            "found": False,
            "message": "Please provide a classification."
        })
        return
    
    accounts = aws_service.get_accounts_by_classification(classification)
    
    if accounts:
        await params.result_callback({
            "found": True,
            "classification": classification,
            "count": len(accounts),
            "accounts": [
                {
                    "account_number": acc["AWS Account Number"],
                    "account_name": acc["AWS account Name"],
                    "status": acc["Status"],
                    "cost": int(acc["Cost of Account in Indian Rupees"])
                } for acc in accounts
            ]
        })
    else:
        await params.result_callback({
            "found": False,
            "message": f"No accounts found with classification {classification}."
        })

async def get_classification_summary(params):
    """Get summary of accounts by classification."""
    classification_counts = aws_service.get_total_accounts_by_classification()
    classification_costs = aws_service.get_total_cost_by_classification()
    
    summary = []
    for classification, count in classification_counts.items():
        cost = classification_costs.get(classification, 0)
        summary.append({
            "classification": classification,
            "count": count,
            "total_cost": int(cost)
        })
    
    await params.result_callback({
        "found": True,
        "summary": summary
    })

async def get_management_type_summary(params):
    """Get summary of accounts by management type."""
    management_counts = aws_service.get_total_accounts_by_management_type()
    management_costs = aws_service.get_total_cost_by_management_type()
    
    summary = []
    for management_type, count in management_counts.items():
        cost = management_costs.get(management_type, 0)
        summary.append({
            "management_type": management_type,
            "count": count,
            "total_cost": int(cost)
        })
    
    await params.result_callback({
        "found": True,
        "summary": summary
    })

async def count_all_aws_accounts(params):
    """Get the COUNT/NUMBER of AWS accounts (returns a number like 123, NOT cost/money)."""
    print("=== COUNT_ALL_AWS_ACCOUNTS FUNCTION CALLED ===")
    print(f"Function called with params: {params}")
    print(f"Function called with arguments: {getattr(params, 'arguments', 'No arguments')}")
    
    try:
        total_count = aws_service.get_total_account_count()
        print(f"Total account count retrieved: {total_count}")
        
        result = {
            "found": True,
            "account_count": total_count,
            "count_type": "number_of_accounts",
            "message": f"There are {total_count} AWS accounts in total. This is the count, not the cost."
        }
        
        print(f"Sending result: {result}")
        await params.result_callback(result)
        print("=== COUNT_ALL_AWS_ACCOUNTS FUNCTION COMPLETED ===")
        
    except Exception as e:
        print(f"ERROR in count_all_aws_accounts: {str(e)}")
        import traceback
        traceback.print_exc()
        
        error_result = {
            "found": False,
            "error": str(e),
            "message": f"Error getting account count: {str(e)}"
        }
        await params.result_callback(error_result)

async def calculate_total_cost_rupees(params):
    """Get the COST/EXPENSE of all AWS accounts in Indian Rupees (returns money like 1512900, NOT count)."""
    print("=== CALCULATE_TOTAL_COST_RUPEES FUNCTION CALLED ===")
    print(f"Function called with params: {params}")
    print(f"Function called with arguments: {getattr(params, 'arguments', 'No arguments')}")
    
    try:
        total_cost = aws_service.get_total_cost()
        print(f"Total cost retrieved: {total_cost}")
        
        result = {
            "found": True,
            "total_cost_rupees": int(total_cost),
            "cost_type": "money_in_rupees",
            "message": f"The total cost of all AWS accounts is {int(total_cost)} Indian Rupees. This is the cost, not the count."
        }
        
        print(f"Sending result: {result}")
        await params.result_callback(result)
        print("=== CALCULATE_TOTAL_COST_RUPEES FUNCTION COMPLETED ===")
        
    except Exception as e:
        print(f"ERROR in calculate_total_cost_rupees: {str(e)}")
        import traceback
        traceback.print_exc()
        
        error_result = {
            "found": False,
            "error": str(e),
            "message": f"Error getting total cost: {str(e)}"
        }
        await params.result_callback(error_result)


async def get_account_status_summary(params):
    """Get summary of accounts by status."""
    status_counts = aws_service.get_total_accounts_by_status()
    
    summary = []
    for status, count in status_counts.items():
        summary.append({
            "status": status,
            "count": count
        })
    
    await params.result_callback({
        "found": True,
        "summary": summary
    })

async def get_accounts_by_year(params):
    """Get accounts provisioned in a specific year."""
    year = params.arguments.get("year")
    
    if not year:
        await params.result_callback({
            "found": False,
            "message": "Please provide a year."
        })
        return
    
    try:
        year = int(year)
        accounts = aws_service.get_accounts_by_year(year)
        
        if accounts:
            await params.result_callback({
                "found": True,
                "year": year,
                "count": len(accounts),
                "accounts": [
                    {
                        "account_number": acc["AWS Account Number"],
                        "account_name": acc["AWS account Name"],
                        "provisioning_date": acc["Provisioning Date"],
                        "status": acc["Status"],
                        "cost": int(acc["Cost of Account in Indian Rupees"])
                    } for acc in accounts
                ]
            })
        else:
            await params.result_callback({
                "found": False,
                "message": f"No accounts found provisioned in year {year}."
            })
    except ValueError:
        await params.result_callback({
            "found": False,
            "message": f"Invalid year format: {year}. Please provide a valid year (e.g., 2023)."
        })

async def get_accounts_by_year_summary(params):
    """Get summary of accounts provisioned by year."""
    year_counts = aws_service.get_accounts_count_by_year()
    
    if not year_counts:
        await params.result_callback({
            "found": False,
            "message": "No account data available."
        })
        return
    
    summary = []
    for year, count in year_counts.items():
        summary.append({
            "year": year,
            "count": count
        })
    
    # Sort by year
    summary.sort(key=lambda x: x["year"])
    
    await params.result_callback({
        "found": True,
        "summary": summary
    })

async def get_accounts_by_date_range(params):
    """Get accounts provisioned within a specific date range."""
    start_date = params.arguments.get("start_date")
    end_date = params.arguments.get("end_date")
    
    if not start_date or not end_date:
        await params.result_callback({
            "found": False,
            "message": "Please provide both start_date and end_date in DD-MMM-YY format (e.g., '01-Jan-19')."
        })
        return
    
    try:
        accounts = aws_service.get_accounts_by_date_range(start_date, end_date)
        
        if accounts:
            await params.result_callback({
                "found": True,
                "start_date": start_date,
                "end_date": end_date,
                "count": len(accounts),
                "accounts": [
                    {
                        "account_number": acc["AWS Account Number"],
                        "account_name": acc["AWS account Name"],
                        "provisioning_date": acc["Provisioning Date"],
                        "status": acc["Status"],
                        "classification": acc["Classification"],
                        "management_type": acc["Management Type"],
                        "cost": int(acc["Cost of Account in Indian Rupees"])
                    } for acc in accounts
                ]
            })
        else:
            await params.result_callback({
                "found": False,
                "message": f"No accounts found provisioned between {start_date} and {end_date}."
            })
    except Exception as e:
        await params.result_callback({
            "found": False,
            "message": f"Error processing date range: {str(e)}. Please use DD-MMM-YY format (e.g., '01-Jan-19')."
        })

async def get_accounts_by_month_year(params):
    """Get accounts provisioned in a specific month and year."""
    month = params.arguments.get("month")
    year = params.arguments.get("year")
    
    if not month or not year:
        await params.result_callback({
            "found": False,
            "message": "Please provide both month (1-12) and year (e.g., 2019)."
        })
        return
    
    try:
        month = int(month)
        year = int(year)
        
        if month < 1 or month > 12:
            await params.result_callback({
                "found": False,
                "message": "Month must be between 1 and 12."
            })
            return
        
        accounts = aws_service.get_accounts_by_month_year(month, year)
        
        # Convert month number to name for better readability
        month_names = ["", "January", "February", "March", "April", "May", "June",
                      "July", "August", "September", "October", "November", "December"]
        month_name = month_names[month]
        
        if accounts:
            await params.result_callback({
                "found": True,
                "month": month,
                "month_name": month_name,
                "year": year,
                "count": len(accounts),
                "accounts": [
                    {
                        "account_number": acc["AWS Account Number"],
                        "account_name": acc["AWS account Name"],
                        "provisioning_date": acc["Provisioning Date"],
                        "status": acc["Status"],
                        "classification": acc["Classification"],
                        "management_type": acc["Management Type"],
                        "cost": int(acc["Cost of Account in Indian Rupees"])
                    } for acc in accounts
                ]
            })
        else:
            await params.result_callback({
                "found": False,
                "message": f"No accounts found provisioned in {month_name} {year}."
            })
    except ValueError:
        await params.result_callback({
            "found": False,
            "message": "Invalid month or year format. Please provide month as number (1-12) and year as number (e.g., 2019)."
        })

async def get_accounts_by_specific_date(params):
    """Get accounts provisioned on a specific date."""
    date = params.arguments.get("date")
    
    if not date:
        await params.result_callback({
            "found": False,
            "message": "Please provide a date in DD-MMM-YY format (e.g., '31-Mar-19')."
        })
        return
    
    try:
        accounts = aws_service.get_accounts_by_specific_date(date)
        
        if accounts:
            await params.result_callback({
                "found": True,
                "date": date,
                "count": len(accounts),
                "accounts": [
                    {
                        "account_number": acc["AWS Account Number"],
                        "account_name": acc["AWS account Name"],
                        "provisioning_date": acc["Provisioning Date"],
                        "status": acc["Status"],
                        "classification": acc["Classification"],
                        "management_type": acc["Management Type"],
                        "cost": int(acc["Cost of Account in Indian Rupees"])
                    } for acc in accounts
                ]
            })
        else:
            await params.result_callback({
                "found": False,
                "message": f"No accounts found provisioned on {date}."
            })
    except Exception as e:
        await params.result_callback({
            "found": False,
            "message": f"Error processing date: {str(e)}. Please use DD-MMM-YY format (e.g., '31-Mar-19')."
        })

async def get_provisioning_date_summary(params):
    """Get comprehensive summary of account provisioning dates."""
    try:
        summary = aws_service.get_provisioning_date_summary()
        
        if summary:
            await params.result_callback({
                "found": True,
                "summary": summary
            })
        else:
            await params.result_callback({
                "found": False,
                "message": "No provisioning date data available."
            })
    except Exception as e:
        await params.result_callback({
            "found": False,
            "message": f"Error generating provisioning date summary: {str(e)}"
        })
