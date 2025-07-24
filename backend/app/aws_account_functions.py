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

async def get_total_cost(params):
    """Get total cost of all accounts."""
    total_cost = aws_service.get_total_cost()
    
    await params.result_callback({
        "found": True,
        "total_cost": int(total_cost)
    })

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
