# AWS Account Management Capabilities

This document provides a comprehensive overview of all AWS account management and cost analysis capabilities built into the Virtual Cloud Assistant.

## Data Source

The system uses a CSV file (`AWS_AccountDetails.csv`) containing 123 AWS accounts with the following information:
- **AWS Account Number**: Unique 12-digit account identifier
- **AWS Account Name**: Human-readable account name
- **Provisioning Date**: Date when account was created (DD-MMM-YY format)
- **Status**: Account status (ACTIVE, CLOSED, SUSPENDED)
- **Classification**: Account classification (Class-1, Class-2, Class-3)
- **Management Type**: How the account is managed (Managed Services, Self service)
- **Cost**: Account cost in Indian Rupees

## Architecture Overview

### Service Layer
- **AWSAccountService**: Core service class that handles all data operations
- **CSV Data Loading**: Automatic loading and preprocessing of account data
- **Data Validation**: Column name cleaning, data type conversion, and normalization

### Function Layer
- **aws_account_functions.py**: Async functions that interface with the voice bot
- **Parameter Validation**: Input validation and error handling
- **Response Formatting**: Structured responses for voice interaction

### Integration Layer
- **main.py**: Function registration and schema definition
- **Nova Sonic Integration**: Voice-enabled function calls
- **WebSocket Transport**: Real-time communication with frontend

## Current Capabilities

### 1. Account Lookup Functions

#### `get_account_details(account_number, account_name)`
- **Purpose**: Get detailed information about a specific AWS account
- **Parameters**: 
  - `account_number` (optional): 12-digit AWS account number
  - `account_name` (optional): Account name (exact or partial match)
- **Returns**: Complete account information including cost, status, classification
- **Voice Examples**: 
  - "Get details for account 550558532874"
  - "Show me information about Galaxy account"

#### `get_accounts_by_classification(classification)`
- **Purpose**: Filter accounts by classification level
- **Parameters**: 
  - `classification`: Class-1, Class-2, or Class-3
- **Returns**: List of all accounts in the specified classification
- **Voice Examples**: 
  - "Show me all Class-1 accounts"
  - "List Class-2 accounts"

### 2. Cost Analysis Functions

#### `calculate_total_cost_rupees()`
- **Purpose**: Get total cost of all AWS accounts
- **Parameters**: None
- **Returns**: Total cost in Indian Rupees (₹1,512,900)
- **Voice Examples**: 
  - "What's the total cost of all accounts?"
  - "How much do we spend on AWS accounts?"

#### `get_classification_summary()`
- **Purpose**: Cost breakdown by account classification
- **Parameters**: None
- **Returns**: Count and total cost for each classification
- **Voice Examples**: 
  - "Give me cost summary by classification"
  - "How much do Class-1 accounts cost?"

#### `get_management_type_summary()`
- **Purpose**: Cost breakdown by management type
- **Parameters**: None
- **Returns**: Count and total cost for Managed Services vs Self service
- **Voice Examples**: 
  - "Show management type cost breakdown"
  - "Compare managed services vs self service costs"

### 3. Account Statistics Functions

#### `count_all_aws_accounts()`
- **Purpose**: Get total number of AWS accounts
- **Parameters**: None
- **Returns**: Total account count (123 accounts)
- **Voice Examples**: 
  - "How many AWS accounts do we have?"
  - "What's the total account count?"

#### `get_account_status_summary()`
- **Purpose**: Account breakdown by status
- **Parameters**: None
- **Returns**: Count of ACTIVE, CLOSED, SUSPENDED accounts
- **Voice Examples**: 
  - "Show account status summary"
  - "How many active accounts do we have?"

### 4. Time-Based Analysis Functions

#### `get_accounts_by_year(year)`
- **Purpose**: Get accounts provisioned in a specific year
- **Parameters**: 
  - `year`: Year (e.g., 2019, 2020, 2021)
- **Returns**: List of accounts provisioned in that year
- **Voice Examples**: 
  - "Show accounts created in 2019"
  - "List 2020 accounts"

#### `get_accounts_by_year_summary()`
- **Purpose**: Account count breakdown by year
- **Parameters**: None
- **Returns**: Count of accounts provisioned each year
- **Voice Examples**: 
  - "Give me yearly account summary"
  - "How many accounts were created each year?"

## New Date-Based Capabilities (Added)

### 5. Advanced Date Filtering Functions

#### `get_accounts_by_date_range(start_date, end_date)`
- **Purpose**: Get accounts provisioned within a specific date range
- **Parameters**: 
  - `start_date`: Start date in DD-MMM-YY format (e.g., '01-Jan-19')
  - `end_date`: End date in DD-MMM-YY format (e.g., '31-Dec-19')
- **Returns**: List of accounts provisioned between the dates
- **Voice Examples**: 
  - "Show accounts created between 1st January 2019 and 31st March 2019"
  - "List accounts provisioned from April 1st 2020 to June 30th 2020"

#### `get_accounts_by_month_year(month, year)`
- **Purpose**: Get accounts provisioned in a specific month and year
- **Parameters**: 
  - `month`: Month number (1-12, where 1=January, 12=December)
  - `year`: Year (e.g., 2019, 2020)
- **Returns**: List of accounts provisioned in that specific month
- **Voice Examples**: 
  - "Show accounts created in April 2019"
  - "List accounts provisioned in December 2020"

#### `get_accounts_by_specific_date(date)`
- **Purpose**: Get accounts provisioned on a specific date
- **Parameters**: 
  - `date`: Specific date in DD-MMM-YY format (e.g., '31-Mar-19')
- **Returns**: List of accounts provisioned on that exact date
- **Voice Examples**: 
  - "Show accounts created on 31st March 2019"
  - "List accounts provisioned on 15th April 2020"

#### `get_provisioning_date_summary()`
- **Purpose**: Comprehensive summary of account provisioning patterns
- **Parameters**: None
- **Returns**: 
  - Earliest and latest provisioning dates
  - Total accounts and date range span
  - Monthly breakdown of account creation
- **Voice Examples**: 
  - "Give me provisioning date summary"
  - "Show account creation patterns over time"

## Data Insights

### Account Distribution
- **Total Accounts**: 123
- **Total Cost**: ₹1,512,900 (Indian Rupees)
- **Date Range**: March 31, 2019 to July 31, 2025 (2,314 days)

### Classification Breakdown
- **Class-1**: High-priority accounts
- **Class-2**: Medium-priority accounts  
- **Class-3**: Standard accounts

### Management Types
- **Managed Services**: Professionally managed accounts
- **Self Service**: Customer-managed accounts

### Status Types
- **ACTIVE**: Currently operational accounts
- **CLOSED**: Deactivated accounts
- **SUSPENDED**: Temporarily suspended accounts

## Usage Examples

### Voice Interaction Examples

1. **Basic Account Lookup**:
   - "What are the details of account Galaxy?"
   - "Show me account 550558532874"

2. **Cost Queries**:
   - "What's our total AWS spending?"
   - "How much do Class-1 accounts cost?"

3. **Time-Based Queries**:
   - "Show me accounts created in April 2019"
   - "List accounts provisioned between January and March 2020"
   - "How many accounts were created on 31st March 2019?"

4. **Summary Queries**:
   - "Give me account status breakdown"
   - "Show provisioning date summary"
   - "What's the classification cost summary?"

### Function Call Examples

```python
# Get account details
await get_account_details({"account_name": "Galaxy"})

# Get accounts by date range
await get_accounts_by_date_range({
    "start_date": "01-Jan-19", 
    "end_date": "31-Mar-19"
})

# Get monthly summary
await get_accounts_by_month_year({"month": "4", "year": "2019"})
```

## Error Handling

The system includes comprehensive error handling for:
- **Invalid Date Formats**: Provides format guidance (DD-MMM-YY)
- **Missing Parameters**: Clear error messages for required fields
- **Data Not Found**: Informative messages when no results match criteria
- **Invalid Ranges**: Validation for month numbers (1-12) and reasonable years

## Performance Considerations

- **In-Memory Processing**: All data loaded into pandas DataFrame for fast queries
- **Efficient Filtering**: Optimized date parsing and filtering operations
- **Caching**: Service instance reused across function calls
- **Error Recovery**: Graceful handling of data processing errors

## Future Enhancements

Potential areas for expansion:
1. **Cost Trending**: Historical cost analysis over time
2. **Predictive Analytics**: Account growth and cost forecasting
3. **Advanced Filtering**: Multi-criteria filtering (e.g., status + classification)
4. **Export Capabilities**: Generate reports in various formats
5. **Real-time Updates**: Dynamic data refresh from AWS APIs
6. **Visualization**: Charts and graphs for data representation

## Technical Implementation

### File Structure
```
backend/app/
├── AWS_AccountDetails.csv          # Data source
├── aws_account_service.py          # Core service layer
├── aws_account_functions.py        # Voice bot functions
├── main.py                        # Integration and registration
└── test_date_functions.py         # Test suite
```

### Dependencies
- **pandas**: Data manipulation and analysis
- **datetime**: Date parsing and formatting
- **typing**: Type hints for better code quality
- **asyncio**: Async function support for voice bot integration

This comprehensive system provides powerful AWS account management capabilities through natural voice interaction, making it easy for users to query, analyze, and understand their AWS account portfolio.
