"""
Google Sheets handler for uploading Discord post data.
Handles authentication, CSV reading, and batch uploads to Google Sheets.
"""

import csv
import logging
import time
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Dict, Any

from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

logger = logging.getLogger(__name__)


class GoogleSheetsHandler:
    """Handler for Google Sheets operations."""
    
    SCOPES = ['https://www.googleapis.com/auth/spreadsheets']
    MAX_RETRIES = 3
    RETRY_DELAY = 1  # Initial delay in seconds
    
    def __init__(self, credentials_path: str, sheet_id: str):
        """
        Initialize Google Sheets handler.
        
        Args:
            credentials_path: Path to service account JSON credentials
            sheet_id: Google Sheets ID
        """
        self.credentials_path = Path(credentials_path)
        self.sheet_id = sheet_id
        self.service = None
        
        if not self.credentials_path.exists():
            raise FileNotFoundError(
                f"Credentials file not found: {self.credentials_path}\n"
                "Please follow the setup instructions in plan.md"
            )
        
        self._authenticate()
    
    def _authenticate(self) -> None:
        """Authenticate with Google Sheets API using service account."""
        try:
            credentials = Credentials.from_service_account_file(
                str(self.credentials_path),
                scopes=self.SCOPES
            )
            self.service = build('sheets', 'v4', credentials=credentials)
            logger.info("Successfully authenticated with Google Sheets API")
        except Exception as e:
            logger.error(f"Failed to authenticate with Google Sheets: {e}")
            raise
    
    def read_csv(self, file_path: Path) -> List[List[str]]:
        """
        Read CSV file and return as list of lists.
        
        Args:
            file_path: Path to CSV file
            
        Returns:
            List of rows from CSV file
        """
        if not file_path.exists():
            raise FileNotFoundError(f"CSV file not found: {file_path}")
        
        rows = []
        encodings = ['utf-8', 'latin-1', 'cp1252']
        
        for encoding in encodings:
            try:
                with open(file_path, 'r', encoding=encoding) as file:
                    reader = csv.reader(file)
                    rows = list(reader)
                    logger.info(f"Successfully read {len(rows)} rows from {file_path}")
                    return rows
            except UnicodeDecodeError:
                continue
            except Exception as e:
                logger.error(f"Error reading CSV with {encoding}: {e}")
                continue
        
        raise ValueError(f"Unable to read CSV file {file_path} with any encoding")
    
    def _execute_with_retry(self, request: Any) -> Any:
        """
        Execute API request with exponential backoff retry.
        
        Args:
            request: Google API request object
            
        Returns:
            API response
        """
        delay = self.RETRY_DELAY
        
        for attempt in range(self.MAX_RETRIES):
            try:
                return request.execute()
            except HttpError as e:
                if e.resp.status == 429:  # Rate limit
                    if attempt < self.MAX_RETRIES - 1:
                        logger.warning(f"Rate limited, retrying in {delay} seconds...")
                        time.sleep(delay)
                        delay *= 2  # Exponential backoff
                        continue
                logger.error(f"HTTP error occurred: {e}")
                raise
            except Exception as e:
                logger.error(f"Unexpected error: {e}")
                raise
        
        raise Exception(f"Failed after {self.MAX_RETRIES} retries")
    
    def clear_sheet(self, sheet_name: str = 'Sheet1', preserve_headers: bool = True) -> None:
        """
        Clear all data from sheet.
        
        Args:
            sheet_name: Name of the sheet tab
            preserve_headers: Whether to keep the first row
        """
        try:
            if preserve_headers:
                # Get the header row first
                range_name = f"{sheet_name}!1:1"
                result = self._execute_with_retry(
                    self.service.spreadsheets().values().get(
                        spreadsheetId=self.sheet_id,
                        range=range_name
                    )
                )
                headers = result.get('values', [[]])[0] if result.get('values') else []
                
                # Clear everything
                self._execute_with_retry(
                    self.service.spreadsheets().values().clear(
                        spreadsheetId=self.sheet_id,
                        range=sheet_name
                    )
                )
                
                # Restore headers if they existed
                if headers:
                    self._execute_with_retry(
                        self.service.spreadsheets().values().update(
                            spreadsheetId=self.sheet_id,
                            range=f"{sheet_name}!A1",
                            valueInputOption='RAW',
                            body={'values': [headers]}
                        )
                    )
                logger.info(f"Cleared sheet {sheet_name}, preserved headers")
            else:
                # Clear everything
                self._execute_with_retry(
                    self.service.spreadsheets().values().clear(
                        spreadsheetId=self.sheet_id,
                        range=sheet_name
                    )
                )
                logger.info(f"Cleared entire sheet {sheet_name}")
        except Exception as e:
            logger.error(f"Failed to clear sheet: {e}")
            raise
    
    def append_data(self, data: List[List[str]], sheet_name: str = 'Sheet1') -> None:
        """
        Append data rows to Google Sheet.
        
        Args:
            data: List of rows to append
            sheet_name: Name of the sheet tab
        """
        if not data:
            logger.warning("No data to append")
            return
        
        try:
            body = {'values': data}
            
            result = self._execute_with_retry(
                self.service.spreadsheets().values().append(
                    spreadsheetId=self.sheet_id,
                    range=f"{sheet_name}!A:Z",
                    valueInputOption='RAW',
                    insertDataOption='INSERT_ROWS',
                    body=body
                )
            )
            
            updates = result.get('updates', {})
            updated_rows = updates.get('updatedRows', 0)
            logger.info(f"Appended {updated_rows} rows to {sheet_name}")
            
        except Exception as e:
            logger.error(f"Failed to append data: {e}")
            raise
    
    def batch_append_data(self, data: List[List[str]], sheet_name: str = 'Sheet1', 
                         batch_size: int = 100) -> None:
        """
        Append data in batches for large datasets.
        
        Args:
            data: List of rows to append
            sheet_name: Name of the sheet tab
            batch_size: Number of rows per batch
        """
        total_rows = len(data)
        
        for i in range(0, total_rows, batch_size):
            batch = data[i:i + batch_size]
            self.append_data(batch, sheet_name)
            logger.info(f"Processed batch {i//batch_size + 1}/{(total_rows + batch_size - 1)//batch_size}")
            
            # Small delay between batches to avoid rate limits
            if i + batch_size < total_rows:
                time.sleep(0.5)
    
    def get_last_entry_date(self, sheet_name: str = 'Sheet1') -> Optional[datetime]:
        """
        Get the date of the last entry to avoid duplicates.
        
        Args:
            sheet_name: Name of the sheet tab
            
        Returns:
            DateTime of last entry or None if sheet is empty
        """
        try:
            # Get all values to find the last row
            result = self._execute_with_retry(
                self.service.spreadsheets().values().get(
                    spreadsheetId=self.sheet_id,
                    range=f"{sheet_name}!A:A"
                )
            )
            
            values = result.get('values', [])
            
            if len(values) <= 1:  # Only headers or empty
                logger.info("Sheet is empty or contains only headers")
                return None
            
            # Get the last row's date (first column)
            last_date_str = values[-1][0] if values[-1] else None
            
            if last_date_str:
                try:
                    # Parse date in format YYYY-MM-DD
                    return datetime.strptime(last_date_str, '%Y-%m-%d')
                except ValueError:
                    logger.warning(f"Unable to parse date: {last_date_str}")
                    return None
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to get last entry date: {e}")
            return None
    
    def update_sheet_from_csv(self, csv_path: Path, sheet_name: str = 'Sheet1',
                            mode: str = 'append', batch_size: int = 100) -> None:
        """
        Update Google Sheet from CSV file.
        
        Args:
            csv_path: Path to CSV file
            sheet_name: Name of the sheet tab
            mode: 'append' to add to existing data, 'replace' to clear and rewrite
            batch_size: Number of rows per batch for large files
        """
        logger.info(f"Updating sheet from {csv_path} in {mode} mode")
        
        # Read CSV data
        data = self.read_csv(csv_path)
        
        if not data:
            logger.warning("CSV file is empty")
            return
        
        # Separate headers and data rows
        headers = data[0] if data else []
        data_rows = data[1:] if len(data) > 1 else []
        
        if mode == 'replace':
            # Clear sheet and write everything
            self.clear_sheet(sheet_name, preserve_headers=False)
            if headers:
                self.append_data([headers], sheet_name)
            if data_rows:
                self.batch_append_data(data_rows, sheet_name, batch_size)
                
        elif mode == 'append':
            # Check if sheet is empty and needs headers
            result = self._execute_with_retry(
                self.service.spreadsheets().values().get(
                    spreadsheetId=self.sheet_id,
                    range=f"{sheet_name}!1:1"
                )
            )
            
            existing_headers = result.get('values', [[]])[0] if result.get('values') else []
            
            if not existing_headers and headers:
                # Add headers if sheet is empty
                self.append_data([headers], sheet_name)
            
            # Append data rows
            if data_rows:
                self.batch_append_data(data_rows, sheet_name, batch_size)
        
        else:
            raise ValueError(f"Invalid mode: {mode}. Use 'append' or 'replace'")
        
        logger.info(f"Successfully updated sheet with {len(data_rows)} data rows")
    
    def get_sheet_data(self, sheet_name: str = 'Sheet1', 
                      range_notation: str = 'A:Z') -> List[List[str]]:
        """
        Get data from Google Sheet.
        
        Args:
            sheet_name: Name of the sheet tab
            range_notation: A1 notation for the range to fetch
            
        Returns:
            List of rows from the sheet
        """
        try:
            range_name = f"{sheet_name}!{range_notation}"
            result = self._execute_with_retry(
                self.service.spreadsheets().values().get(
                    spreadsheetId=self.sheet_id,
                    range=range_name
                )
            )
            
            values = result.get('values', [])
            logger.info(f"Retrieved {len(values)} rows from {sheet_name}")
            return values
            
        except Exception as e:
            logger.error(f"Failed to get sheet data: {e}")
            raise
    
    def validate_csv_structure(self, csv_path: Path, 
                              expected_columns: List[str]) -> bool:
        """
        Validate that CSV has expected structure.
        
        Args:
            csv_path: Path to CSV file
            expected_columns: List of expected column names
            
        Returns:
            True if structure matches, False otherwise
        """
        try:
            data = self.read_csv(csv_path)
            if not data:
                logger.warning("CSV is empty")
                return False
            
            headers = data[0]
            
            if headers != expected_columns:
                logger.warning(
                    f"CSV structure mismatch. Expected: {expected_columns}, "
                    f"Found: {headers}"
                )
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to validate CSV: {e}")
            return False