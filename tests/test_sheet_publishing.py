#!/usr/bin/env python3
"""
Test script for publishing directly from Google Sheet

This script reads the Daily Post Draft from your Google Sheet
and publishes it using either X API or Typefully.
"""

import sys
import logging
from pathlib import Path
from dotenv import load_dotenv

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from modules.sheets_handler import GoogleSheetsHandler
from modules.x_publisher import create_publisher, SheetPublisher
import config

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()


def test_direct_publishing():
    """Test publishing with a simple test message"""
    print("\n" + "="*60)
    print("DIRECT PUBLISHING TEST")
    print("="*60)
    
    # Check configurations
    if not config.validate_config():
        print("❌ Missing required configuration. Please check your .env file.")
        return False
    
    print("\nSelect publishing method:")
    print("1. X API (Twitter) - Publish immediately")
    print("2. Typefully - Schedule for later")
    
    choice = input("\nSelect option (1-2): ").strip()
    
    if choice == '1':
        # Use X API
        if not all([config.X_API_KEY, config.X_API_SECRET, 
                   config.X_ACCESS_TOKEN, config.X_ACCESS_TOKEN_SECRET]):
            print("❌ X API credentials not configured in .env")
            return False
        
        print("\n🐦 Creating X API publisher...")
        publisher = create_publisher(
            'twitter',
            api_key=config.X_API_KEY,
            api_secret=config.X_API_SECRET,
            access_token=config.X_ACCESS_TOKEN,
            access_token_secret=config.X_ACCESS_TOKEN_SECRET
        )
        
    elif choice == '2':
        # Use Typefully
        if not config.TYPEFULLY_API_KEY:
            print("❌ Typefully API key not configured in .env")
            return False
        
        hours_delay = config.TYPEFULLY_HOURS_DELAY
        print(f"\n📅 Creating Typefully publisher (scheduling {hours_delay} hours from now)...")
        publisher = create_publisher(
            'typefully',
            api_key=config.TYPEFULLY_API_KEY,
            hours_delay=hours_delay
        )
    else:
        print("Invalid choice")
        return False
    
    if not publisher:
        print("❌ Failed to create publisher")
        return False
    
    # Test with a simple message
    test_content = """🚀 Test Post from Discord-to-Sheets Bot

This is a test message to verify the publishing pipeline is working correctly.

#Test #CryptoBot"""
    
    print(f"\n📝 Test content:")
    print("-" * 40)
    print(test_content)
    print("-" * 40)
    
    confirm = input("\nPublish this test message? (yes/no): ")
    if confirm.lower() != 'yes':
        print("Cancelled.")
        return False
    
    print("\n🚀 Publishing...")
    result = publisher.publish(test_content)
    
    if result.success:
        print(f"✅ Successfully published!")
        if result.url:
            print(f"   URL: {result.url}")
        if result.post_id:
            print(f"   ID: {result.post_id}")
    else:
        print(f"❌ Publishing failed: {result.error_msg}")
    
    return result.success


def test_sheet_publishing():
    """Test publishing from Google Sheet with receipt update"""
    print("\n" + "="*60)
    print("SHEET PUBLISHING TEST")
    print("="*60)
    
    # Check configurations
    if not config.validate_config():
        print("❌ Missing required configuration. Please check your .env file.")
        return False
    
    try:
        # Initialize sheets handler
        print("\n📊 Connecting to Google Sheet...")
        sheets_handler = GoogleSheetsHandler(
            credentials_path=config.GOOGLE_SERVICE_ACCOUNT_FILE,
            sheet_id=config.GOOGLE_SHEETS_ID
        )
        
        # Read current sheet data to show available content
        print("📖 Reading sheet data...")
        sheet_data = sheets_handler.get_sheet_data()
        
        if len(sheet_data) < 2:
            print("❌ No data rows found in sheet")
            return False
        
        headers = sheet_data[0]
        
        # Find Daily Post Draft column
        draft_col = -1
        for i, header in enumerate(headers):
            if header == 'Daily Post Draft':
                draft_col = i
                break
        
        if draft_col == -1:
            print("❌ 'Daily Post Draft' column not found in sheet")
            print("   Please run the Gemini analyzer first to generate drafts")
            return False
        
        # Show available drafts
        print("\n📋 Available drafts in sheet:")
        print("-" * 60)
        
        available_rows = []
        for i, row in enumerate(sheet_data[1:], start=2):  # Skip header
            if len(row) > draft_col and row[draft_col] and row[draft_col].strip():
                content_preview = row[draft_col][:100] + "..." if len(row[draft_col]) > 100 else row[draft_col]
                print(f"Row {i}: {content_preview}")
                available_rows.append(i)
        
        if not available_rows:
            print("No drafts found. Please run the Gemini analyzer first.")
            return False
        
        print("-" * 60)
        
        # Select row to publish
        row_num = input(f"\nEnter row number to publish (e.g., {available_rows[0]}): ").strip()
        
        try:
            row_num = int(row_num)
            if row_num not in available_rows:
                print(f"❌ Row {row_num} doesn't have a draft")
                return False
        except ValueError:
            print("❌ Invalid row number")
            return False
        
        # Get the full content
        full_content = sheet_data[row_num - 1][draft_col]
        
        print(f"\n📝 Content from row {row_num}:")
        print("-" * 60)
        print(full_content)
        print("-" * 60)
        
        # Select publishing method
        print("\nSelect publishing method:")
        print("1. X API (Twitter) - Publish immediately")
        print("2. Typefully - Schedule for later")
        
        choice = input("\nSelect option (1-2): ").strip()
        
        if choice == '1':
            # Use X API
            if not all([config.X_API_KEY, config.X_API_SECRET, 
                       config.X_ACCESS_TOKEN, config.X_ACCESS_TOKEN_SECRET]):
                print("❌ X API credentials not configured in .env")
                return False
            
            print("\n🐦 Creating X API publisher...")
            publisher = create_publisher(
                'twitter',
                api_key=config.X_API_KEY,
                api_secret=config.X_API_SECRET,
                access_token=config.X_ACCESS_TOKEN,
                access_token_secret=config.X_ACCESS_TOKEN_SECRET
            )
            
        elif choice == '2':
            # Use Typefully
            if not config.TYPEFULLY_API_KEY:
                print("❌ Typefully API key not configured in .env")
                return False
            
            hours_delay = config.TYPEFULLY_HOURS_DELAY
            print(f"\n📅 Creating Typefully publisher (scheduling {hours_delay} hours from now)...")
            publisher = create_publisher(
                'typefully',
                api_key=config.TYPEFULLY_API_KEY,
                hours_delay=hours_delay
            )
        else:
            print("Invalid choice")
            return False
        
        if not publisher:
            print("❌ Failed to create publisher")
            return False
        
        # Create sheet publisher wrapper
        print("\n🔗 Creating sheet publisher...")
        sheet_publisher = SheetPublisher(publisher, sheets_handler)
        
        confirm = input(f"\nPublish content from row {row_num}? (yes/no): ")
        if confirm.lower() != 'yes':
            print("Cancelled.")
            return False
        
        print(f"\n🚀 Publishing from row {row_num}...")
        result = sheet_publisher.publish_from_sheet(row_num)
        
        if result.success:
            print(f"✅ Successfully published!")
            if result.url:
                print(f"   URL: {result.url}")
            if result.post_id:
                print(f"   ID: {result.post_id}")
            print(f"   ✅ Sheet updated with publication receipt")
            
            # Show the receipt that was written
            print("\n📋 Checking sheet for receipt...")
            updated_sheet = sheets_handler.get_sheet_data()
            receipt_col = -1
            for i, header in enumerate(updated_sheet[0]):
                if header == 'Publication receipt':
                    receipt_col = i
                    break
            
            if receipt_col >= 0 and len(updated_sheet[row_num - 1]) > receipt_col:
                receipt = updated_sheet[row_num - 1][receipt_col]
                print(f"   Receipt: {receipt}")
        else:
            print(f"❌ Publishing failed: {result.error_msg}")
        
        return result.success
        
    except Exception as e:
        logger.error(f"Error in sheet publishing test: {e}", exc_info=True)
        print(f"❌ Error: {e}")
        return False


def main():
    """Main test function"""
    print("\n" + "="*70)
    print("X/TWITTER PUBLISHER TEST WITH SHEET INTEGRATION")
    print("="*70)
    
    print("\nThis script tests the publishing functionality.")
    print("It can publish content to X/Twitter via:")
    print("  - X API v2 (immediate posting)")
    print("  - Typefully API (scheduled posting)")
    
    print("\nTest Options:")
    print("1. Test direct publishing (simple test message)")
    print("2. Test sheet publishing (read from Google Sheet and update receipt)")
    print("3. Run both tests")
    
    choice = input("\nSelect test option (1-3): ").strip()
    
    if choice == '1':
        test_direct_publishing()
    elif choice == '2':
        test_sheet_publishing()
    elif choice == '3':
        print("\n" + "="*60)
        print("TEST 1: DIRECT PUBLISHING")
        print("="*60)
        if test_direct_publishing():
            print("\n✅ Direct publishing test passed")
        else:
            print("\n❌ Direct publishing test failed")
        
        input("\nPress Enter to continue to sheet publishing test...")
        
        print("\n" + "="*60)
        print("TEST 2: SHEET PUBLISHING")
        print("="*60)
        if test_sheet_publishing():
            print("\n✅ Sheet publishing test passed")
        else:
            print("\n❌ Sheet publishing test failed")
    else:
        print("Invalid choice. Running sheet publishing test...")
        test_sheet_publishing()
    
    print("\n" + "="*70)
    print("TEST COMPLETE")
    print("="*70)
    
    print("\n📌 Next Steps:")
    print("1. Check your X/Twitter account or Typefully dashboard")
    print("2. Verify the published content appears correctly")
    print("3. Check your Google Sheet for the 'Publication receipt' column")
    print("4. The receipt should contain:")
    print("   - For X API: The tweet URL")
    print("   - For Typefully: The draft ID")
    
    print("\n💡 To use in production:")
    print("   from modules.x_publisher import create_publisher, SheetPublisher")
    print("   sheet_publisher = SheetPublisher(publisher, sheets_handler)")
    print("   result = sheet_publisher.publish_from_sheet(row_number)")


if __name__ == "__main__":
    main()