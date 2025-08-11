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
        print(f"Initializing AWSAccountService with CSV path: {self.csv_path}")
        self._load_data()
    
    def _load_data(self):
        """Load data from CSV file into a pandas DataFrame."""
        try:
            import os
            print(f"Current working directory: {os.getcwd()}")
            print(f"Checking if file exists: {os.path.exists(self.csv_path)}")
            
            # Try with absolute path if relative path doesn't work
            if not os.path.exists(self.csv_path):
                abs_path = os.path.join(os.getcwd(), self.csv_path)
                print(f"Trying absolute path: {abs_path}")
                if os.path.exists(abs_path):
                    self.csv_path = abs_path
            
            # Read CSV with UTF-8-sig encoding to handle BOM
            self._data = pd.read_csv(self.csv_path, encoding='utf-8-sig')
            print(f"Successfully loaded CSV with {len(self._data)} rows")
            
            # Clean column names by stripping whitespace and removing any BOM characters
            self._data.columns = self._data.columns.str.strip().str.replace('\ufeff', '')
            # Print column names for debugging
            print(f"CSV columns after cleaning: {self._data.columns.tolist()}")
            
            # Verify the cost column exists
            cost_column = 'Cost of Account in Indian Rupees'
            if cost_column not in self._data.columns:
                print(f"WARNING: Cost column '{cost_column}' not found!")
                print(f"Available columns: {self._data.columns.tolist()}")
                # Try to find a similar column
                for col in self._data.columns:
                    if 'cost' in col.lower() or 'rupees' in col.lower():
                        print(f"Found potential cost column: '{col}'")
            
            # Clean classification values
            self._data['Classification'] = self._data['Classification'].str.strip()
            # Normalize classification format (ensure consistent format like "Class-1")
            self._data['Classification'] = self._data['Classification'].apply(
                lambda x: f"Class-{str(x).split('-')[-1]}" if "-" in str(x) else f"Class-{str(x).split(' ')[-1]}" if " " in str(x) else x
            )
            # Normalize Management Type (ensure consistent capitalization)
            self._data['Management Type'] = self._data['Management Type'].str.strip()
            self._data['Management Type'] = self._data['Management Type'].apply(
                lambda x: "Self Service" if x.lower() == "self service" else x
            )
            # Convert account numbers to strings to preserve leading zeros
            self._data['AWS Account Number'] = self._data['AWS Account Number'].astype(str)
            
            # Print first few rows for debugging
            print("First 3 rows of data:")
            print(self._data.head(3).to_string())
            
            print("Data preprocessing completed successfully")
        except Exception as e:
            print(f"Error loading CSV data: {e}")
            import traceback
            traceback.print_exc()
            self._data = pd.DataFrame()
    
    def get_account_by_number(self, account_number: str) -> Dict:
        """Get account details by account number."""
        print(f"Looking up account by number: {account_number}")
        if self._data is None or self._data.empty:
            print("Data is None or empty")
            return {}
        
        print(f"Data has {len(self._data)} rows")
        print(f"First few account numbers in data: {self._data['AWS Account Number'].head().tolist()}")
        
        account = self._data[self._data['AWS Account Number'] == account_number]
        if account.empty:
            print(f"No account found with number: {account_number}")
            return {}
        
        print(f"Found account: {account.iloc[0]['AWS account Name']}")
        return account.iloc[0].to_dict()
    
    def get_account_by_name(self, account_name: str) -> Dict:
        """Get account details by account name."""
        print(f"Looking up account by name: {account_name}")
        if self._data is None or self._data.empty:
            print("Data is None or empty")
            return {}
        
        # Determine the correct column name for account name
        account_name_column = None
        for col in self._data.columns:
            if 'account name' in col.lower() or 'accountname' in col.lower():
                account_name_column = col
                break
        
        if not account_name_column:
            print("Could not find account name column")
            return {}
        
        print(f"Using column '{account_name_column}' for account name lookup")
        print(f"First few account names in data: {self._data[account_name_column].head().tolist()}")
        
        # Try exact match first
        account = self._data[self._data[account_name_column] == account_name]
        
        # If no exact match, try case-insensitive match
        if account.empty:
            print(f"No exact match for account name: {account_name}, trying case-insensitive match")
            account = self._data[self._data[account_name_column].str.lower() == account_name.lower()]
        
        # If still no match, try partial match
        if account.empty:
            print(f"No case-insensitive match, trying partial match")
            account = self._data[self._data[account_name_column].str.lower().str.contains(account_name.lower())]
        
        if account.empty:
            print(f"No account found with name: {account_name}")
            return {}
        
        print(f"Found account: {account.iloc[0]['AWS Account Number']}")
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
    
    def get_total_account_count(self) -> int:
        """Get the total number of accounts."""
        print(f"=== GET_TOTAL_ACCOUNT_COUNT CALLED ===")
        print(f"Data is None: {self._data is None}")
        print(f"Data is empty: {self._data.empty if self._data is not None else 'N/A'}")
        
        if self._data is None or self._data.empty:
            print("Returning 0 because data is None or empty")
            return 0
        
        count = len(self._data)
        print(f"Total account count: {count}")
        return count
    
    def get_total_cost(self) -> int:
        """Get the total cost of all accounts."""
        print(f"=== GET_TOTAL_COST CALLED ===")
        print(f"Data is None: {self._data is None}")
        print(f"Data is empty: {self._data.empty if self._data is not None else 'N/A'}")
        
        if self._data is None or self._data.empty:
            print("Returning 0 because data is None or empty")
            return 0
        
        cost_column = 'Cost of Account in Indian Rupees'
        if cost_column not in self._data.columns:
            print(f"Cost column '{cost_column}' not found in data columns: {self._data.columns.tolist()}")
            return 0
            
        total_cost = self._data[cost_column].sum()
        print(f"Total cost: {total_cost}")
        return total_cost
    
    def get_total_cost_by_classification(self) -> Dict[str, int]:
        """Get the total cost for each classification."""
        if self._data is None or self._data.empty:
            return {}
        
        return self._data.groupby('Classification')['Cost of Account in Indian Rupees'].sum().to_dict()
    
    def get_total_cost_by_management_type(self) -> Dict[str, int]:
        """Get the total cost for each management type."""
        if self._data is None or self._data.empty:
            return {}
        
        return self._data.groupby('Management Type')['Cost of Account in Indian Rupees'].sum().to_dict()
    
    def get_all_accounts(self) -> List[Dict]:
        """Get all accounts."""
        if self._data is None or self._data.empty:
            return []
        
        return self._data.to_dict('records')
    
    def get_account_number_as_digits(self, account_number: str) -> str:
        """Convert account number to digit-by-digit string representation.
        Returns each digit separately without converting to word form."""
        return ' '.join([digit for digit in str(account_number)])
        
    def get_accounts_by_year(self, year: int) -> List[Dict]:
        """Get all accounts provisioned in a specific year."""
        if self._data is None or self._data.empty:
            return []
        
        # Convert the Provisioning Date to datetime and extract year
        try:
            # Create a copy to avoid SettingWithCopyWarning
            df_copy = self._data.copy()
            # Parse the date format (assuming DD-MMM-YY format)
            df_copy['Provisioning_Year'] = pd.to_datetime(df_copy['Provisioning Date'], format='%d-%b-%y').dt.year
            
            # Filter accounts by the specified year
            accounts = df_copy[df_copy['Provisioning_Year'] == year]
            if accounts.empty:
                return []
            
            return accounts.to_dict('records')
        except Exception as e:
            print(f"Error processing dates: {e}")
            return []
            
    def get_accounts_count_by_year(self) -> Dict[int, int]:
        """Get the count of accounts provisioned in each year."""
        if self._data is None or self._data.empty:
            return {}
        
        try:
            # Create a copy to avoid SettingWithCopyWarning
            df_copy = self._data.copy()
            # Parse the date format (assuming DD-MMM-YY format)
            df_copy['Provisioning_Year'] = pd.to_datetime(df_copy['Provisioning Date'], format='%d-%b-%y').dt.year
            
            # Count accounts by year
            year_counts = df_copy['Provisioning_Year'].value_counts().to_dict()
            return {int(year): count for year, count in year_counts.items()}
        except Exception as e:
            print(f"Error counting accounts by year: {e}")
            return {}
    
    def get_accounts_by_date_range(self, start_date: str, end_date: str) -> List[Dict]:
        """Get all accounts provisioned within a specific date range.
        
        Args:
            start_date: Start date in DD-MMM-YY format (e.g., '01-Jan-19')
            end_date: End date in DD-MMM-YY format (e.g., '31-Dec-19')
            
        Returns:
            List of account dictionaries
        """
        if self._data is None or self._data.empty:
            return []
        
        try:
            # Create a copy to avoid SettingWithCopyWarning
            df_copy = self._data.copy()
            
            # Parse the provisioning dates
            df_copy['Provisioning_DateTime'] = pd.to_datetime(df_copy['Provisioning Date'], format='%d-%b-%y')
            
            # Parse the input date range
            start_datetime = pd.to_datetime(start_date, format='%d-%b-%y')
            end_datetime = pd.to_datetime(end_date, format='%d-%b-%y')
            
            # Filter accounts within the date range
            accounts = df_copy[
                (df_copy['Provisioning_DateTime'] >= start_datetime) & 
                (df_copy['Provisioning_DateTime'] <= end_datetime)
            ]
            
            if accounts.empty:
                return []
            
            return accounts.to_dict('records')
        except Exception as e:
            print(f"Error filtering accounts by date range: {e}")
            return []
    
    def get_accounts_by_month_year(self, month: int, year: int) -> List[Dict]:
        """Get all accounts provisioned in a specific month and year.
        
        Args:
            month: Month number (1-12)
            year: Year (e.g., 2019, 2020)
            
        Returns:
            List of account dictionaries
        """
        if self._data is None or self._data.empty:
            return []
        
        try:
            # Create a copy to avoid SettingWithCopyWarning
            df_copy = self._data.copy()
            
            # Parse the provisioning dates
            df_copy['Provisioning_DateTime'] = pd.to_datetime(df_copy['Provisioning Date'], format='%d-%b-%y')
            df_copy['Provisioning_Month'] = df_copy['Provisioning_DateTime'].dt.month
            df_copy['Provisioning_Year'] = df_copy['Provisioning_DateTime'].dt.year
            
            # Filter accounts by month and year
            accounts = df_copy[
                (df_copy['Provisioning_Month'] == month) & 
                (df_copy['Provisioning_Year'] == year)
            ]
            
            if accounts.empty:
                return []
            
            return accounts.to_dict('records')
        except Exception as e:
            print(f"Error filtering accounts by month/year: {e}")
            return []
    
    def get_accounts_by_specific_date(self, date: str) -> List[Dict]:
        """Get all accounts provisioned on a specific date.
        
        Args:
            date: Date in DD-MMM-YY format (e.g., '31-Mar-19')
            
        Returns:
            List of account dictionaries
        """
        if self._data is None or self._data.empty:
            return []
        
        try:
            # Create a copy to avoid SettingWithCopyWarning
            df_copy = self._data.copy()
            
            # Parse the provisioning dates
            df_copy['Provisioning_DateTime'] = pd.to_datetime(df_copy['Provisioning Date'], format='%d-%b-%y')
            
            # Parse the input date
            target_date = pd.to_datetime(date, format='%d-%b-%y')
            
            # Filter accounts by specific date
            accounts = df_copy[df_copy['Provisioning_DateTime'].dt.date == target_date.date()]
            
            if accounts.empty:
                return []
            
            return accounts.to_dict('records')
        except Exception as e:
            print(f"Error filtering accounts by specific date: {e}")
            return []
    
    def get_provisioning_date_summary(self) -> Dict[str, Union[str, int, List[Dict]]]:
        """Get a comprehensive summary of account provisioning dates.
        
        Returns:
            Dictionary containing date range, total accounts, and monthly breakdown
        """
        if self._data is None or self._data.empty:
            return {}
        
        try:
            # Create a copy to avoid SettingWithCopyWarning
            df_copy = self._data.copy()
            
            # Parse the provisioning dates
            df_copy['Provisioning_DateTime'] = pd.to_datetime(df_copy['Provisioning Date'], format='%d-%b-%y')
            
            # Get date range
            min_date = df_copy['Provisioning_DateTime'].min()
            max_date = df_copy['Provisioning_DateTime'].max()
            
            # Get monthly breakdown
            df_copy['Year_Month'] = df_copy['Provisioning_DateTime'].dt.to_period('M')
            monthly_counts = df_copy['Year_Month'].value_counts().sort_index()
            
            monthly_breakdown = []
            for period, count in monthly_counts.items():
                monthly_breakdown.append({
                    "month_year": str(period),
                    "count": count,
                    "month": period.month,
                    "year": period.year
                })
            
            return {
                "earliest_provisioning_date": min_date.strftime('%d-%b-%y'),
                "latest_provisioning_date": max_date.strftime('%d-%b-%y'),
                "total_accounts": len(df_copy),
                "date_range_days": (max_date - min_date).days,
                "monthly_breakdown": monthly_breakdown
            }
        except Exception as e:
            print(f"Error generating provisioning date summary: {e}")
            return {}
