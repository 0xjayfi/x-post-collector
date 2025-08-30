"""
Archive Handler Module

This module handles archiving processed posts from Sheet1 to Archives sheet.
It archives posts marked with AI processed = TRUE and cleans up the source sheet.
"""

from datetime import datetime, timezone
from typing import List, Dict, Optional
import logging
from utils.timezone_utils import get_time_column_header

logger = logging.getLogger(__name__)


class ArchiveHandler:
    """Handle archiving of processed posts to Archives sheet"""
    
    def __init__(self, sheets_handler):
        """
        Initialize the archive handler
        
        Args:
            sheets_handler: GoogleSheetsHandler instance
        """
        self.sheets = sheets_handler
        self.archive_sheet_name = "Archives"
        self.source_sheet_name = "Sheet1"
    
    def ensure_archive_sheet_exists(self) -> bool:
        """
        Create Archives sheet if it doesn't exist and ensure headers are present
        
        Returns:
            True if sheet exists or was created successfully
        """
        try:
            # Get all sheet names
            spreadsheet = self.sheets.service.spreadsheets().get(
                spreadsheetId=self.sheets.sheet_id
            ).execute()
            
            sheet_names = [sheet['properties']['title'] 
                          for sheet in spreadsheet.get('sheets', [])]
            
            sheet_exists = self.archive_sheet_name in sheet_names
            
            if not sheet_exists:
                # Create new sheet
                request_body = {
                    'requests': [{
                        'addSheet': {
                            'properties': {
                                'title': self.archive_sheet_name
                            }
                        }
                    }]
                }
                
                self.sheets.service.spreadsheets().batchUpdate(
                    spreadsheetId=self.sheets.sheet_id,
                    body=request_body
                ).execute()
                
                logger.info(f"Created Archives sheet")
            
            # Define expected headers with dynamic timezone
            time_header = get_time_column_header()
            expected_headers = [
                'Date', time_header, 'Author', 'Post Link', 
                'Content', 'AI Summary',
                'Date Processed (UTC)', 'Publication Receipt'
            ]
            
            # Check if headers exist
            try:
                result = self.sheets.service.spreadsheets().values().get(
                    spreadsheetId=self.sheets.sheet_id,
                    range=f"{self.archive_sheet_name}!A1:H1"
                ).execute()
                
                existing_headers = result.get('values', [[]])[0] if result.get('values') else []
                
                # If headers don't match expected, update them
                if existing_headers != expected_headers:
                    self.sheets.service.spreadsheets().values().update(
                        spreadsheetId=self.sheets.sheet_id,
                        range=f"{self.archive_sheet_name}!A1:H1",
                        valueInputOption='RAW',
                        body={'values': [expected_headers]}
                    ).execute()
                    logger.info(f"Updated Archives sheet headers")
                    
            except Exception:
                # No headers exist, add them
                self.sheets.service.spreadsheets().values().update(
                    spreadsheetId=self.sheets.sheet_id,
                    range=f"{self.archive_sheet_name}!A1:H1",
                    valueInputOption='RAW',
                    body={'values': [expected_headers]}
                ).execute()
                logger.info(f"Added headers to Archives sheet")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to ensure archive sheet: {e}")
            return False
    
    def get_processed_posts(self) -> List[Dict]:
        """
        Get all posts where AI processed = TRUE
        
        Returns:
            List of dictionaries with post data and row indices
        """
        try:
            # Read all data from Sheet1
            result = self.sheets.service.spreadsheets().values().get(
                spreadsheetId=self.sheets.sheet_id,
                range=self.source_sheet_name
            ).execute()
            
            source_data = result.get('values', [])
            
            if len(source_data) <= 1:
                return []
            
            headers = source_data[0]
            data_rows = source_data[1:]
            
            # Find required column indices (case-insensitive)
            ai_processed_idx = -1
            for idx, header in enumerate(headers):
                if header.lower() == 'ai processed':
                    ai_processed_idx = idx
                    break
            
            if ai_processed_idx == -1:
                logger.warning("AI processed column not found")
                return []
            
            # Collect processed posts
            processed_posts = []
            
            for idx, row in enumerate(data_rows, start=2):  # Start from row 2 (after header)
                # Ensure row has enough columns
                while len(row) <= ai_processed_idx:
                    row.append('')
                
                # Check if AI processed = TRUE
                if row[ai_processed_idx] and row[ai_processed_idx].upper() == 'TRUE':
                    post_data = {
                        'row_index': idx,
                        'data': row,
                        'headers': headers
                    }
                    processed_posts.append(post_data)
            
            logger.info(f"Found {len(processed_posts)} posts with AI processed = TRUE")
            return processed_posts
            
        except Exception as e:
            logger.error(f"Failed to get processed posts: {e}")
            return []
    
    def archive_posts(self, posts: List[Dict]) -> int:
        """
        Archive the processed posts to Archives sheet
        
        Args:
            posts: List of post dictionaries from get_processed_posts()
        
        Returns:
            Number of posts archived
        """
        if not posts:
            return 0
            
        try:
            archived_rows = []
            
            # First, find the Publication Receipt value (should be the same for all posts in this batch)
            publication_receipt = ''
            for post in posts:
                headers = post['headers']
                row = post['data']
                # Find publication receipt column (case-insensitive)
                publication_receipt_idx = -1
                for idx, header in enumerate(headers):
                    if 'publication receipt' in header.lower():
                        publication_receipt_idx = idx
                        break
                
                if publication_receipt_idx >= 0 and len(row) > publication_receipt_idx:
                    receipt_value = row[publication_receipt_idx]
                    if receipt_value and receipt_value.strip():
                        publication_receipt = receipt_value.strip()
                        logger.info(f"Found publication receipt: {publication_receipt}")
                        break
            
            # Now build archive rows with the found publication receipt
            for post in posts:
                headers = post['headers']
                row = post['data']
                
                # Find column indices for required data (case-insensitive)
                headers_lower = [h.lower() for h in headers]
                date_idx = headers_lower.index('date') if 'date' in headers_lower else -1
                # Look for either 'time' or 'time (local time zone)'
                time_idx = -1
                for idx, header in enumerate(headers_lower):
                    if 'time' in header:  # This will match both 'time' and 'time (local time zone)'
                        time_idx = idx
                        break
                author_idx = headers_lower.index('author') if 'author' in headers_lower else -1
                post_link_idx = headers_lower.index('post link') if 'post link' in headers_lower else -1
                content_idx = headers_lower.index('content') if 'content' in headers_lower else -1
                
                # Find AI Summary column (case-insensitive)
                ai_summary_idx = -1
                for idx, header in enumerate(headers):
                    if header.lower() == 'ai summary':
                        ai_summary_idx = idx
                        break
                
                # Build archive row with only required columns
                archive_row = [
                    row[date_idx] if date_idx >= 0 and len(row) > date_idx else '',
                    row[time_idx] if time_idx >= 0 and len(row) > time_idx else '',
                    row[author_idx] if author_idx >= 0 and len(row) > author_idx else '',
                    row[post_link_idx] if post_link_idx >= 0 and len(row) > post_link_idx else '',
                    row[content_idx] if content_idx >= 0 and len(row) > content_idx else '',
                    row[ai_summary_idx] if ai_summary_idx >= 0 and len(row) > ai_summary_idx else '',
                    datetime.now(timezone.utc).isoformat(),  # Date Processed (UTC)
                    publication_receipt  # Use the same publication receipt for all rows
                ]
                
                archived_rows.append(archive_row)
            
            if archived_rows:
                # Get the next available row in Archives sheet
                result = self.sheets.service.spreadsheets().values().get(
                    spreadsheetId=self.sheets.sheet_id,
                    range=f"{self.archive_sheet_name}!A:A"
                ).execute()
                
                existing_rows = len(result.get('values', []))
                next_row = existing_rows + 1
                
                # Append to Archives sheet
                self.sheets.service.spreadsheets().values().update(
                    spreadsheetId=self.sheets.sheet_id,
                    range=f"{self.archive_sheet_name}!A{next_row}",
                    valueInputOption='RAW',
                    body={'values': archived_rows}
                ).execute()
                
                logger.info(f"Archived {len(archived_rows)} posts to Archives sheet")
                
            return len(archived_rows)
            
        except Exception as e:
            logger.error(f"Failed to archive posts: {e}")
            raise
    
    def clear_archived_rows(self, row_indices: List[int]) -> bool:
        """
        Remove archived rows from Sheet1
        
        Args:
            row_indices: List of row numbers to delete (1-based)
        
        Returns:
            True if successful
        """
        try:
            # Read current data
            result = self.sheets.service.spreadsheets().values().get(
                spreadsheetId=self.sheets.sheet_id,
                range=self.source_sheet_name
            ).execute()
            
            source_data = result.get('values', [])
            
            # Keep header and unarchived rows
            new_data = [source_data[0]]  # Keep header
            
            for idx, row in enumerate(source_data[1:], start=2):
                if idx not in row_indices:
                    new_data.append(row)
            
            # Clear the sheet
            self.sheets.service.spreadsheets().values().clear(
                spreadsheetId=self.sheets.sheet_id,
                range=self.source_sheet_name
            ).execute()
            
            # Write back the filtered data
            if new_data:
                self.sheets.service.spreadsheets().values().update(
                    spreadsheetId=self.sheets.sheet_id,
                    range=f"{self.source_sheet_name}!A1",
                    valueInputOption='RAW',
                    body={'values': new_data}
                ).execute()
            
            logger.info(f"Removed {len(row_indices)} archived rows from Sheet1")
            return True
            
        except Exception as e:
            logger.error(f"Failed to clear archived rows: {e}")
            return False
    
    def clear_processing_columns(self) -> bool:
        """
        Clear content from processing columns:
        - AI Summary
        - AI processed
        - Daily Post Draft
        - Publication receipt
        
        Returns:
            True if successful
        """
        try:
            # Read current data
            result = self.sheets.service.spreadsheets().values().get(
                spreadsheetId=self.sheets.sheet_id,
                range=self.source_sheet_name
            ).execute()
            
            data = result.get('values', [])
            
            if len(data) <= 1:
                return True  # No data to clear
                
            headers = data[0]
            
            # Find column indices to clear
            columns_to_clear = ['AI Summary', 'AI processed', 'Daily Post Draft', 'Publication receipt']
            clear_indices = []
            
            for col_name in columns_to_clear:
                if col_name in headers:
                    clear_indices.append(headers.index(col_name))
            
            if not clear_indices:
                logger.info("No processing columns found to clear")
                return True
            
            # Clear the columns (except header)
            for i in range(1, len(data)):
                for col_idx in clear_indices:
                    if len(data[i]) > col_idx:
                        data[i][col_idx] = ''
            
            # Clear the sheet
            self.sheets.service.spreadsheets().values().clear(
                spreadsheetId=self.sheets.sheet_id,
                range=self.source_sheet_name
            ).execute()
            
            # Write back the updated data
            self.sheets.service.spreadsheets().values().update(
                spreadsheetId=self.sheets.sheet_id,
                range=f"{self.source_sheet_name}!A1",
                valueInputOption='RAW',
                body={'values': data}
            ).execute()
            
            logger.info(f"Cleared processing columns: {columns_to_clear}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to clear processing columns: {e}")
            return False
    
    def run_archive_workflow(self) -> Dict:
        """
        Complete archive workflow:
        1. Get processed posts (AI processed = TRUE)
        2. Archive them to Archives sheet
        3. Remove archived rows from Sheet1
        4. Clear processing columns for remaining rows
        
        Returns:
            Dictionary with results
        """
        results = {
            'success': False,
            'posts_archived': 0,
            'errors': []
        }
        
        try:
            # Ensure archive sheet exists
            if not self.ensure_archive_sheet_exists():
                results['errors'].append("Failed to ensure Archives sheet exists")
                return results
            
            # Get posts to archive
            processed_posts = self.get_processed_posts()
            
            if not processed_posts:
                logger.info("No posts to archive (no posts with AI processed = TRUE)")
                results['success'] = True
                return results
            
            logger.info(f"Found {len(processed_posts)} posts to archive")
            
            # Archive the posts
            archived_count = self.archive_posts(processed_posts)
            results['posts_archived'] = archived_count
            
            if archived_count > 0:
                # Get row indices to delete
                row_indices = [post['row_index'] for post in processed_posts]
                
                # Remove archived rows from Sheet1
                if self.clear_archived_rows(row_indices):
                    logger.info("Successfully removed archived rows from Sheet1")
                else:
                    results['errors'].append("Failed to remove archived rows")
                
                # Clear processing columns for remaining rows
                if self.clear_processing_columns():
                    logger.info("Successfully cleared processing columns")
                else:
                    results['errors'].append("Failed to clear processing columns")
            
            results['success'] = len(results['errors']) == 0
            
            if results['success']:
                logger.info(f"Archive workflow completed successfully. Archived {archived_count} posts.")
            else:
                logger.error(f"Archive workflow completed with errors: {results['errors']}")
            
        except Exception as e:
            logger.error(f"Archive workflow failed: {e}")
            results['errors'].append(str(e))
        
        return results