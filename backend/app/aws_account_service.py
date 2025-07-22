import csv
import os
import pandas as pd
from typing import Dict, List, Optional, Union, Tuple

class AWSAccountService:
    """Service for handling AWS account data operations."""
    
    def __init__(self, csv_path: str = "AWS_AccountDetails.csv"):
        """Initialize the service with the CSV data file path."""
        self.csv_path = csv_path
        self._data = None
        self._load_data()
    
    def _load_data(self):
        """Load data from CSV file into a pandas DataFrame."""
        try:
            self._data = pd.read_csv(self.csv_path)
            # Clean column names by stripping whitespace
            self._data.columns = self._data.columns.str.strip()
            # Clean classification values
            self._data['Classification'] = self._data['Classification'].str.strip()
            # Normalize classification format (ensure consistent format like "Class-1")
            self._data['Classification'] = self._data['Classification'].apply(
                lambda x: f"Class-{x.split('-')[-1]}" if "-" in x else f"Class-{x.split(' ')[-1]}" if " " in x else x
            )
            # Convert account numbers to strings to preserve leading zeros
            self._data['AWS Account Number'] = self._data['AWS Account Number'].astype(str)
        except Exception as e:
            print(f"Error loading CSV data: {e}")
            self._data = pd.DataFrame()
    
    def get_account_by_number(self, account_number: str) -> Dict:
        """Get account details by account number."""
        if self._data is None or self._data.empty:
            return {}
        
        account = self._data[self._data['AWS Account Number'] == account_number]
        if account.empty:
            return {}
        
        return account.iloc[0].to_dict()
    
    def get_account_by_name(self, account_name: str) -> Dict:
        """Get account details by account name."""
        if self._data is None or self._data.empty:
            return {}
        
        account = self._data[self._data['AWS account Name'] == account_name]
        if account.empty:
            return {}
        
        return account.iloc[0].to_dict()
    
    def get_accounts_by_classification(self, classification: str) -> List[Dict]:
        """Get all accounts with the specified classification."""
        if self._data is None or self._data.empty:
            return []
        
        accounts = self._data[self._data['Classification'] == classification]
        if accounts.empty:
            return []
        
        return accounts.to_dict('records')
    
    def get_accounts_by_management_type(self, management_type: str) -> List[Dict]:
        """Get all accounts with the specified management type."""
        if self._data is None or self._data.empty:
            return []
        
        accounts = self._data[self._data['Management Type'] == management_type]
        if accounts.empty:
            return []
        
        return accounts.to_dict('records')
    
    def get_accounts_by_status(self, status: str) -> List[Dict]:
        """Get all accounts with the specified status."""
        if self._data is None or self._data.empty:
            return []
        
        accounts = self._data[self._data['Status'] == status]
        if accounts.empty:
            return []
        
        return accounts.to_dict('records')
    
    def get_total_accounts_by_classification(self) -> Dict[str, int]:
        """Get the total number of accounts for each classification."""
        if self._data is None or self._data.empty:
            return {}
        
        return self._data['Classification'].value_counts().to_dict()
    
    def get_total_accounts_by_management_type(self) -> Dict[str, int]:
        """Get the total number of accounts for each management type."""
        if self._data is None or self._data.empty:
            return {}
        
        return self._data['Management Type'].value_counts().to_dict()
    
    def get_total_accounts_by_status(self) -> Dict[str, int]:
        """Get the total number of accounts for each status."""
        if self._data is None or self._data.empty:
            return {}
        
        return self._data['Status'].value_counts().to_dict()
    
    def get_total_cost(self) -> int:
        """Get the total cost of all accounts."""
        if self._data is None or self._data.empty:
            return 0
        
        return self._data['Total Cost of Account in Indian Rupees'].sum()
    
    def get_total_cost_by_classification(self) -> Dict[str, int]:
        """Get the total cost for each classification."""
        if self._data is None or self._data.empty:
            return {}
        
        return self._data.groupby('Classification')['Total Cost of Account in Indian Rupees'].sum().to_dict()
    
    def get_total_cost_by_management_type(self) -> Dict[str, int]:
        """Get the total cost for each management type."""
        if self._data is None or self._data.empty:
            return {}
        
        return self._data.groupby('Management Type')['Total Cost of Account in Indian Rupees'].sum().to_dict()
    
    def get_all_accounts(self) -> List[Dict]:
        """Get all accounts."""
        if self._data is None or self._data.empty:
            return []
        
        return self._data.to_dict('records')
    
    def get_account_number_as_digits(self, account_number: str) -> str:
        """Convert account number to digit-by-digit string representation."""
        digit_map = {
            '0': 'zero',
            '1': 'one',
            '2': 'two',
            '3': 'three',
            '4': 'four',
            '5': 'five',
            '6': 'six',
            '7': 'seven',
            '8': 'eight',
            '9': 'nine'
        }
        
        return ' '.join([digit_map.get(digit, digit) for digit in str(account_number)])