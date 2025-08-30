#!/usr/bin/env python3
"""
Integration test script for Google Sheets handler.
This script demonstrates how to upload CSV data to Google Sheets.
"""

import sys
from pathlib import Path
import logging

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from modules.sheets_handler import GoogleSheetsHandler
import config

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def main():
    """Main function to test Google Sheets integration."""
    
    # Check configuration
    if not config.validate_config():
        logger.error("Configuration validation failed")
        return 1
    
    try:
        # Initialize handler
        logger.info("Initializing Google Sheets handler...")
        handler = GoogleSheetsHandler(
            credentials_path=config.GOOGLE_SERVICE_ACCOUNT_FILE,
            sheet_id=config.GOOGLE_SHEETS_ID
        )
        
        # Find a CSV file to upload
        csv_files = list(Path('.').glob('*.csv'))
        
        if not csv_files:
            logger.warning("No CSV files found in current directory")
            return 1
        
        # Use the most recent CSV file
        csv_file = sorted(csv_files, key=lambda x: x.stat().st_mtime)[-1]
        logger.info(f"Using CSV file: {csv_file}")
        
        # Validate CSV structure
        expected_columns = ['date', 'time', 'author', 'post_link', 'content', 'author_link']
        if handler.validate_csv_structure(csv_file, expected_columns):
            logger.info("CSV structure is valid")
        else:
            logger.warning("CSV structure doesn't match expected format")
            logger.info("Proceeding anyway...")
        
        # Get last entry date before upload
        last_date = handler.get_last_entry_date(config.GOOGLE_SHEET_NAME)
        if last_date:
            logger.info(f"Last entry in sheet dated: {last_date.strftime('%Y-%m-%d')}")
        else:
            logger.info("Sheet appears to be empty or new")
        
        # Upload CSV to Google Sheets
        logger.info(f"Uploading {csv_file} to Google Sheets...")
        handler.update_sheet_from_csv(
            csv_path=csv_file,
            sheet_name=config.GOOGLE_SHEET_NAME,
            mode='append',  # Use 'replace' to clear sheet first
            batch_size=config.SHEETS_BATCH_SIZE
        )
        
        logger.info("Upload completed successfully!")
        
        # Verify by getting row count
        sheet_data = handler.get_sheet_data(config.GOOGLE_SHEET_NAME, 'A:A')
        row_count = len(sheet_data)
        logger.info(f"Sheet now contains {row_count} rows (including headers)")
        
        return 0
        
    except FileNotFoundError as e:
        logger.error(f"File not found: {e}")
        logger.info("Please ensure credentials.json exists in the project directory")
        logger.info("Follow the setup instructions in plan.md")
        return 1
        
    except Exception as e:
        logger.error(f"Error during execution: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())