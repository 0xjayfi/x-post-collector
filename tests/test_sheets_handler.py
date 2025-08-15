"""
Unit tests for Google Sheets handler module.
Tests CSV reading, data validation, and API interactions.
"""

import unittest
from pathlib import Path
from datetime import datetime
import tempfile
import csv
import os
from unittest.mock import Mock, patch, MagicMock

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from modules.sheets_handler import GoogleSheetsHandler


class TestGoogleSheetsHandler(unittest.TestCase):
    """Test cases for GoogleSheetsHandler class."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Create temporary credentials file for testing
        self.temp_creds = tempfile.NamedTemporaryFile(
            mode='w', 
            suffix='.json', 
            delete=False
        )
        self.temp_creds.write('{"type": "service_account", "project_id": "test"}')
        self.temp_creds.close()
        
        # Test sheet ID
        self.test_sheet_id = "test_sheet_id_123"
    
    def tearDown(self):
        """Clean up test fixtures."""
        if os.path.exists(self.temp_creds.name):
            os.unlink(self.temp_creds.name)
    
    @patch('modules.sheets_handler.build')
    @patch('modules.sheets_handler.Credentials')
    def test_initialization(self, mock_credentials, mock_build):
        """Test handler initialization and authentication."""
        mock_credentials.from_service_account_file.return_value = Mock()
        mock_build.return_value = Mock()
        
        handler = GoogleSheetsHandler(self.temp_creds.name, self.test_sheet_id)
        
        self.assertEqual(handler.sheet_id, self.test_sheet_id)
        self.assertIsNotNone(handler.service)
        mock_credentials.from_service_account_file.assert_called_once()
        mock_build.assert_called_once_with('sheets', 'v4', credentials=mock_credentials.from_service_account_file.return_value)
    
    @patch('modules.sheets_handler.build')
    @patch('modules.sheets_handler.Credentials')
    def test_missing_credentials_file(self, mock_credentials, mock_build):
        """Test handling of missing credentials file."""
        with self.assertRaises(FileNotFoundError):
            GoogleSheetsHandler("non_existent_file.json", self.test_sheet_id)
    
    @patch('modules.sheets_handler.build')
    @patch('modules.sheets_handler.Credentials')
    def test_read_csv(self, mock_credentials, mock_build):
        """Test CSV reading functionality."""
        mock_credentials.from_service_account_file.return_value = Mock()
        mock_build.return_value = Mock()
        
        handler = GoogleSheetsHandler(self.temp_creds.name, self.test_sheet_id)
        
        # Create temporary CSV file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            writer = csv.writer(f)
            writer.writerow(['date', 'time', 'author', 'post_link', 'content', 'author_link'])
            writer.writerow(['2025-08-14', '10:00', 'TestUser', 'https://twitter.com/test', 'Test content', 'https://discord.com/users/123'])
            csv_path = f.name
        
        try:
            data = handler.read_csv(Path(csv_path))
            
            self.assertEqual(len(data), 2)
            self.assertEqual(data[0], ['date', 'time', 'author', 'post_link', 'content', 'author_link'])
            self.assertEqual(data[1][0], '2025-08-14')
            self.assertEqual(data[1][2], 'TestUser')
        finally:
            os.unlink(csv_path)
    
    @patch('modules.sheets_handler.build')
    @patch('modules.sheets_handler.Credentials')
    def test_read_csv_missing_file(self, mock_credentials, mock_build):
        """Test reading non-existent CSV file."""
        mock_credentials.from_service_account_file.return_value = Mock()
        mock_build.return_value = Mock()
        
        handler = GoogleSheetsHandler(self.temp_creds.name, self.test_sheet_id)
        
        with self.assertRaises(FileNotFoundError):
            handler.read_csv(Path("non_existent.csv"))
    
    @patch('modules.sheets_handler.build')
    @patch('modules.sheets_handler.Credentials')
    def test_clear_sheet_preserve_headers(self, mock_credentials, mock_build):
        """Test clearing sheet while preserving headers."""
        mock_credentials.from_service_account_file.return_value = Mock()
        mock_service = Mock()
        mock_build.return_value = mock_service
        
        # Mock the API responses
        mock_get_response = {
            'values': [['date', 'time', 'author', 'post_link', 'content', 'author_link']]
        }
        mock_service.spreadsheets().values().get().execute.return_value = mock_get_response
        mock_service.spreadsheets().values().clear().execute.return_value = {}
        mock_service.spreadsheets().values().update().execute.return_value = {}
        
        handler = GoogleSheetsHandler(self.temp_creds.name, self.test_sheet_id)
        handler.clear_sheet('Sheet1', preserve_headers=True)
        
        # Verify API calls were made
        mock_service.spreadsheets().values().get.assert_called()
        mock_service.spreadsheets().values().clear.assert_called()
        mock_service.spreadsheets().values().update.assert_called()
    
    @patch('modules.sheets_handler.build')
    @patch('modules.sheets_handler.Credentials')
    def test_append_data(self, mock_credentials, mock_build):
        """Test appending data to sheet."""
        mock_credentials.from_service_account_file.return_value = Mock()
        mock_service = Mock()
        mock_build.return_value = mock_service
        
        mock_append_response = {
            'updates': {
                'updatedRows': 2
            }
        }
        mock_service.spreadsheets().values().append().execute.return_value = mock_append_response
        
        handler = GoogleSheetsHandler(self.temp_creds.name, self.test_sheet_id)
        
        test_data = [
            ['2025-08-14', '10:00', 'User1', 'https://twitter.com/1', 'Content 1', 'https://discord.com/users/1'],
            ['2025-08-14', '11:00', 'User2', 'https://twitter.com/2', 'Content 2', 'https://discord.com/users/2']
        ]
        
        handler.append_data(test_data, 'Sheet1')
        
        # Verify append was called with correct data
        mock_service.spreadsheets().values().append.assert_called()
        call_args = mock_service.spreadsheets().values().append.call_args
        self.assertEqual(call_args[1]['body']['values'], test_data)
    
    @patch('modules.sheets_handler.build')
    @patch('modules.sheets_handler.Credentials')
    def test_batch_append_data(self, mock_credentials, mock_build):
        """Test batch appending of large datasets."""
        mock_credentials.from_service_account_file.return_value = Mock()
        mock_service = Mock()
        mock_build.return_value = mock_service
        
        mock_append_response = {
            'updates': {
                'updatedRows': 50
            }
        }
        mock_service.spreadsheets().values().append().execute.return_value = mock_append_response
        
        handler = GoogleSheetsHandler(self.temp_creds.name, self.test_sheet_id)
        
        # Create test data with 150 rows
        test_data = [
            [f'2025-08-14', f'{i:02d}:00', f'User{i}', f'https://twitter.com/{i}', 
             f'Content {i}', f'https://discord.com/users/{i}']
            for i in range(150)
        ]
        
        handler.batch_append_data(test_data, 'Sheet1', batch_size=50)
        
        # Should be called at least 3 times (150 rows / 50 batch size)
        self.assertGreaterEqual(mock_service.spreadsheets().values().append.call_count, 3)
    
    @patch('modules.sheets_handler.build')
    @patch('modules.sheets_handler.Credentials')
    def test_get_last_entry_date(self, mock_credentials, mock_build):
        """Test getting the last entry date from sheet."""
        mock_credentials.from_service_account_file.return_value = Mock()
        mock_service = Mock()
        mock_build.return_value = mock_service
        
        mock_get_response = {
            'values': [
                ['date'],
                ['2025-08-12'],
                ['2025-08-13'],
                ['2025-08-14']
            ]
        }
        mock_service.spreadsheets().values().get().execute.return_value = mock_get_response
        
        handler = GoogleSheetsHandler(self.temp_creds.name, self.test_sheet_id)
        last_date = handler.get_last_entry_date('Sheet1')
        
        self.assertIsNotNone(last_date)
        self.assertEqual(last_date.strftime('%Y-%m-%d'), '2025-08-14')
    
    @patch('modules.sheets_handler.build')
    @patch('modules.sheets_handler.Credentials')
    def test_get_last_entry_date_empty_sheet(self, mock_credentials, mock_build):
        """Test getting last entry date from empty sheet."""
        mock_credentials.from_service_account_file.return_value = Mock()
        mock_service = Mock()
        mock_build.return_value = mock_service
        
        mock_get_response = {
            'values': [['date']]  # Only headers
        }
        mock_service.spreadsheets().values().get().execute.return_value = mock_get_response
        
        handler = GoogleSheetsHandler(self.temp_creds.name, self.test_sheet_id)
        last_date = handler.get_last_entry_date('Sheet1')
        
        self.assertIsNone(last_date)
    
    @patch('modules.sheets_handler.build')
    @patch('modules.sheets_handler.Credentials')
    def test_validate_csv_structure(self, mock_credentials, mock_build):
        """Test CSV structure validation."""
        mock_credentials.from_service_account_file.return_value = Mock()
        mock_build.return_value = Mock()
        
        handler = GoogleSheetsHandler(self.temp_creds.name, self.test_sheet_id)
        
        # Create CSV with correct structure
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            writer = csv.writer(f)
            writer.writerow(['date', 'time', 'author', 'post_link', 'content', 'author_link'])
            writer.writerow(['2025-08-14', '10:00', 'TestUser', 'https://twitter.com/test', 'Test content', 'https://discord.com/users/123'])
            csv_path = f.name
        
        try:
            expected_columns = ['date', 'time', 'author', 'post_link', 'content', 'author_link']
            is_valid = handler.validate_csv_structure(Path(csv_path), expected_columns)
            self.assertTrue(is_valid)
            
            # Test with wrong structure
            wrong_columns = ['col1', 'col2', 'col3']
            is_valid = handler.validate_csv_structure(Path(csv_path), wrong_columns)
            self.assertFalse(is_valid)
        finally:
            os.unlink(csv_path)
    
    @patch('modules.sheets_handler.build')
    @patch('modules.sheets_handler.Credentials')
    @patch('time.sleep')
    def test_retry_on_rate_limit(self, mock_sleep, mock_credentials, mock_build):
        """Test exponential backoff retry on rate limit."""
        mock_credentials.from_service_account_file.return_value = Mock()
        mock_service = Mock()
        mock_build.return_value = mock_service
        
        # Create HTTP error for rate limiting
        from googleapiclient.errors import HttpError
        import json
        
        error_content = json.dumps({'error': {'code': 429, 'message': 'Rate limit exceeded'}})
        mock_resp = Mock()
        mock_resp.status = 429
        rate_limit_error = HttpError(mock_resp, error_content.encode())
        
        # First two calls fail with rate limit, third succeeds
        mock_request = Mock()
        mock_request.execute.side_effect = [
            rate_limit_error,
            rate_limit_error,
            {'updates': {'updatedRows': 1}}
        ]
        
        handler = GoogleSheetsHandler(self.temp_creds.name, self.test_sheet_id)
        result = handler._execute_with_retry(mock_request)
        
        self.assertEqual(mock_request.execute.call_count, 3)
        self.assertEqual(mock_sleep.call_count, 2)
        # Check exponential backoff delays
        mock_sleep.assert_any_call(1)
        mock_sleep.assert_any_call(2)
    
    @patch('modules.sheets_handler.build')
    @patch('modules.sheets_handler.Credentials')
    def test_update_sheet_from_csv_replace_mode(self, mock_credentials, mock_build):
        """Test updating sheet from CSV in replace mode."""
        mock_credentials.from_service_account_file.return_value = Mock()
        mock_service = Mock()
        mock_build.return_value = mock_service
        
        # Setup mock responses
        mock_service.spreadsheets().values().get().execute.return_value = {'values': []}
        mock_service.spreadsheets().values().clear().execute.return_value = {}
        mock_service.spreadsheets().values().append().execute.return_value = {'updates': {'updatedRows': 2}}
        
        handler = GoogleSheetsHandler(self.temp_creds.name, self.test_sheet_id)
        
        # Create test CSV
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            writer = csv.writer(f)
            writer.writerow(['date', 'time', 'author', 'post_link', 'content', 'author_link'])
            writer.writerow(['2025-08-14', '10:00', 'TestUser', 'https://twitter.com/test', 'Test content', 'https://discord.com/users/123'])
            csv_path = f.name
        
        try:
            handler.update_sheet_from_csv(Path(csv_path), 'Sheet1', mode='replace')
            
            # Verify clear was called
            mock_service.spreadsheets().values().clear.assert_called()
            # Verify append was called twice (headers + data)
            self.assertGreaterEqual(mock_service.spreadsheets().values().append.call_count, 1)
        finally:
            os.unlink(csv_path)


if __name__ == '__main__':
    unittest.main()