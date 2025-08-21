#!/usr/bin/env python3
"""
Test script for Archive Handler

This script tests the archive functionality by:
1. Showing current processed posts
2. Running the archive workflow
3. Verifying the results
"""

import sys
import logging
from pathlib import Path
from dotenv import load_dotenv

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from modules.sheets_handler import GoogleSheetsHandler
from modules.archive_handler import ArchiveHandler
import config

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()


def show_sheet_status(sheets_handler, sheet_name="Sheet1"):
    """Show current status of a sheet"""
    try:
        result = sheets_handler.service.spreadsheets().values().get(
            spreadsheetId=sheets_handler.sheet_id,
            range=sheet_name
        ).execute()
        
        data = result.get('values', [])
        
        if not data:
            print(f"  {sheet_name} is empty")
            return
        
        headers = data[0]
        rows = data[1:] if len(data) > 1 else []
        
        print(f"  {sheet_name}: {len(rows)} data rows")
        
        # Check for AI processed column
        if 'AI processed' in headers:
            ai_proc_idx = headers.index('AI processed')
            processed_count = 0
            for row in rows:
                if len(row) > ai_proc_idx and row[ai_proc_idx] and row[ai_proc_idx].upper() == 'TRUE':
                    processed_count += 1
            print(f"    - Posts with AI processed = TRUE: {processed_count}")
        
        # Show column names
        print(f"    - Columns: {', '.join(headers)}")
        
    except Exception as e:
        print(f"  Error reading {sheet_name}: {e}")


def test_archive_handler():
    """Test the archive handler functionality"""
    
    print("\n" + "="*70)
    print("ARCHIVE HANDLER TEST")
    print("="*70)
    
    # Check configuration
    if not config.validate_config():
        print("❌ Missing required configuration. Please check your .env file.")
        return False
    
    try:
        # Initialize sheets handler
        print("\n1. Connecting to Google Sheets...")
        sheets_handler = GoogleSheetsHandler(
            credentials_path=config.GOOGLE_SERVICE_ACCOUNT_FILE,
            sheet_id=config.GOOGLE_SHEETS_ID
        )
        print("✅ Connected to Google Sheets")
        
        # Show current sheet status
        print("\n2. Current Sheet Status:")
        show_sheet_status(sheets_handler, "Sheet1")
        show_sheet_status(sheets_handler, "Archives")
        
        # Initialize archive handler
        print("\n3. Initializing Archive Handler...")
        archive_handler = ArchiveHandler(sheets_handler)
        print("✅ Archive handler initialized")
        
        # Check for processed posts
        print("\n4. Checking for processed posts...")
        processed_posts = archive_handler.get_processed_posts()
        
        if not processed_posts:
            print("ℹ️  No posts found with AI processed = TRUE")
            print("   Please run the Gemini analyzer first to process some posts")
            return True
        
        print(f"📋 Found {len(processed_posts)} posts to archive:")
        for i, post in enumerate(processed_posts[:5], 1):  # Show first 5
            row_idx = post['row_index']
            headers = post['headers']
            data = post['data']
            
            # Get post details
            date_idx = headers.index('date') if 'date' in headers else -1
            time_idx = headers.index('time') if 'time' in headers else -1
            author_idx = headers.index('author') if 'author' in headers else -1
            
            date = data[date_idx] if date_idx >= 0 and len(data) > date_idx else 'N/A'
            time = data[time_idx] if time_idx >= 0 and len(data) > time_idx else 'N/A'
            author = data[author_idx] if author_idx >= 0 and len(data) > author_idx else 'N/A'
            
            print(f"   {i}. Row {row_idx}: {date} {time} by {author}")
        
        if len(processed_posts) > 5:
            print(f"   ... and {len(processed_posts) - 5} more")
        
        # Ask for confirmation
        print("\n" + "-"*50)
        confirm = input("\n🚀 Run archive workflow? This will:\n"
                       "   - Move processed posts to Archives sheet\n"
                       "   - Remove them from Sheet1\n"
                       "   - Clear processing columns\n"
                       "\nProceed? (yes/no): ")
        
        if confirm.lower() != 'yes':
            print("Archive cancelled.")
            return False
        
        # Run archive workflow
        print("\n5. Running archive workflow...")
        results = archive_handler.run_archive_workflow()
        
        # Show results
        print("\n" + "="*70)
        print("ARCHIVE RESULTS")
        print("="*70)
        
        if results['success']:
            print(f"✅ Archive successful!")
            print(f"   - Posts archived: {results['posts_archived']}")
        else:
            print(f"❌ Archive failed!")
            print(f"   - Errors: {results['errors']}")
        
        # Show updated sheet status
        print("\n6. Updated Sheet Status:")
        show_sheet_status(sheets_handler, "Sheet1")
        show_sheet_status(sheets_handler, "Archives")
        
        return results['success']
        
    except Exception as e:
        logger.error(f"Test failed: {e}", exc_info=True)
        print(f"❌ Error: {e}")
        return False


def view_archives():
    """View the contents of the Archives sheet"""
    
    print("\n" + "="*70)
    print("VIEW ARCHIVES")
    print("="*70)
    
    # Check configuration
    if not config.validate_config():
        print("❌ Missing required configuration. Please check your .env file.")
        return
    
    try:
        # Initialize sheets handler
        sheets_handler = GoogleSheetsHandler(
            credentials_path=config.GOOGLE_SERVICE_ACCOUNT_FILE,
            sheet_id=config.GOOGLE_SHEETS_ID
        )
        
        # Read Archives sheet
        result = sheets_handler.service.spreadsheets().values().get(
            spreadsheetId=sheets_handler.sheet_id,
            range="Archives"
        ).execute()
        
        data = result.get('values', [])
        
        if not data:
            print("Archives sheet is empty")
            return
        
        headers = data[0]
        rows = data[1:] if len(data) > 1 else []
        
        if not rows:
            print("No archived posts found")
            return
        
        print(f"\n📚 Archives contains {len(rows)} posts\n")
        print("-"*70)
        
        # Show last 5 archived posts
        for row in rows[-5:]:
            # Get column indices
            date_idx = headers.index('date') if 'date' in headers else -1
            time_idx = headers.index('time') if 'time' in headers else -1
            author_idx = headers.index('author') if 'author' in headers else -1
            ai_summary_idx = headers.index('AI Summary') if 'AI Summary' in headers else -1
            date_processed_idx = headers.index('Date Processed (UTC)') if 'Date Processed (UTC)' in headers else -1
            receipt_idx = headers.index('Publication Receipt') if 'Publication Receipt' in headers else -1
            
            print(f"Date: {row[date_idx] if date_idx >= 0 and len(row) > date_idx else 'N/A'} "
                  f"{row[time_idx] if time_idx >= 0 and len(row) > time_idx else ''}")
            print(f"Author: {row[author_idx] if author_idx >= 0 and len(row) > author_idx else 'N/A'}")
            
            if ai_summary_idx >= 0 and len(row) > ai_summary_idx and row[ai_summary_idx]:
                summary = row[ai_summary_idx][:100] + "..." if len(row[ai_summary_idx]) > 100 else row[ai_summary_idx]
                print(f"AI Summary: {summary}")
            
            if date_processed_idx >= 0 and len(row) > date_processed_idx and row[date_processed_idx]:
                print(f"Archived (UTC): {row[date_processed_idx]}")
            
            if receipt_idx >= 0 and len(row) > receipt_idx and row[receipt_idx]:
                print(f"Publication: {row[receipt_idx]}")
            
            print("-"*70)
        
        if len(rows) > 5:
            print(f"\n(Showing last 5 of {len(rows)} archived posts)")
        
    except Exception as e:
        print(f"❌ Error viewing archives: {e}")


def main():
    """Main test function"""
    
    print("\n" + "="*70)
    print("ARCHIVE HANDLER TEST SUITE")
    print("="*70)
    
    print("\nThis script tests the archive functionality.")
    print("It will archive posts marked with 'AI processed = TRUE'")
    
    print("\nOptions:")
    print("1. Run archive workflow")
    print("2. View archives")
    print("3. Run both")
    
    choice = input("\nSelect option (1-3): ").strip()
    
    if choice == '1':
        test_archive_handler()
    elif choice == '2':
        view_archives()
    elif choice == '3':
        if test_archive_handler():
            input("\nPress Enter to view archives...")
            view_archives()
    else:
        print("Invalid choice. Running archive workflow...")
        test_archive_handler()
    
    print("\n" + "="*70)
    print("TEST COMPLETE")
    print("="*70)
    
    print("\n📌 Next Steps:")
    print("1. Run the Gemini analyzer to process posts")
    print("2. Optionally publish with X/Typefully")
    print("3. Run this archive script to archive processed posts")
    print("4. Check the Archives sheet in Google Sheets")


if __name__ == "__main__":
    main()