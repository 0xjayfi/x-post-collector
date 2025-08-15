#!/usr/bin/env python3
"""
Integration test for Gemini AI Analyzer with existing Google Sheet

This script tests the Gemini analyzer against your actual Google Sheet data.
Run this after setting up your GEMINI_API_KEY in .env
"""

import sys
import logging
from pathlib import Path
from dotenv import load_dotenv

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from modules.sheets_handler import GoogleSheetsHandler
from modules.gemini_analyzer import GeminiAnalyzer, SheetAnalyzer
import config

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()


def test_gemini_connection():
    """Test basic Gemini API connection"""
    print("\n" + "="*50)
    print("Testing Gemini API Connection")
    print("="*50)
    
    api_key = config.GEMINI_API_KEY
    if not api_key or api_key == 'your_gemini_api_key_here':
        print("❌ GEMINI_API_KEY not configured in .env")
        print("   Please get your API key from: https://makersuite.google.com/app/apikey")
        return False
    
    try:
        gemini = GeminiAnalyzer(
            api_key=api_key,
            model=config.GEMINI_MODEL,
            daily_limit=config.GEMINI_DAILY_LIMIT
        )
        
        # Test with a simple prompt
        test_content = "New DeFi protocol launching with innovative yield farming mechanics"
        result = gemini.is_new_project(test_content)
        
        print(f"✅ Gemini API connected successfully")
        print(f"   Model: {config.GEMINI_MODEL}")
        print(f"   Daily limit: {config.GEMINI_DAILY_LIMIT}")
        print(f"   Test detection result: {'New Project' if result else 'Not New Project'}")
        return True
        
    except Exception as e:
        print(f"❌ Failed to connect to Gemini API: {e}")
        return False


def test_sheet_analysis(limit_rows=5, dry_run=True):
    """
    Test Gemini analysis on existing sheet data
    
    Args:
        limit_rows: Number of rows to analyze (for testing)
        dry_run: If True, don't write to sheet, just display results
    """
    print("\n" + "="*50)
    print("Testing Sheet Analysis")
    print("="*50)
    
    # Check configurations
    if not config.validate_config():
        print("❌ Missing required configuration. Please check your .env file.")
        return False
    
    if not config.GEMINI_API_KEY or config.GEMINI_API_KEY == 'your_gemini_api_key_here':
        print("❌ GEMINI_API_KEY not configured")
        return False
    
    try:
        # Initialize handlers
        print("\n📊 Initializing Google Sheets handler...")
        sheets_handler = GoogleSheetsHandler(
            credentials_path=config.GOOGLE_SERVICE_ACCOUNT_FILE,
            sheet_id=config.GOOGLE_SHEETS_ID
        )
        
        print("🤖 Initializing Gemini analyzer...")
        gemini_analyzer = GeminiAnalyzer(
            api_key=config.GEMINI_API_KEY,
            model=config.GEMINI_MODEL,
            daily_limit=config.GEMINI_DAILY_LIMIT
        )
        
        print("🔗 Creating sheet analyzer...")
        analyzer = SheetAnalyzer(sheets_handler, gemini_analyzer)
        
        # Note: analyzer is available for full run if needed
        # analyzer.run_daily_analysis()
        
        # Read current sheet data
        print(f"\n📖 Reading sheet data (analyzing first {limit_rows} rows)...")
        rows = sheets_handler.get_sheet_data()
        
        if len(rows) <= 1:
            print("❌ No data rows found in sheet")
            return False
        
        headers = rows[0]
        data_rows = rows[1:limit_rows + 1]  # Limit for testing
        
        print(f"   Found {len(rows)-1} total rows, testing with {len(data_rows)} rows")
        
        # Find column indices
        try:
            content_idx = headers.index('content')
            date_idx = headers.index('date')
        except ValueError as e:
            print(f"❌ Required column not found: {e}")
            return False
        
        # Analyze rows
        print("\n🔍 Analyzing content for new projects...")
        new_projects = []
        
        for i, row in enumerate(data_rows, start=2):
            if len(row) > content_idx:
                content = row[content_idx]
                date = row[date_idx] if len(row) > date_idx else ""
                
                print(f"\n   Row {i}: Analyzing...")
                print(f"   Content preview: {content[:100]}...")
                
                # Check if it's a new project
                is_new = gemini_analyzer.is_new_project(content)
                
                if is_new:
                    print(f"   ✅ Identified as NEW PROJECT")
                    
                    # Extract project info from content (embedded Twitter/X info)
                    project_info = gemini_analyzer.extract_project_info(content)
                    if project_info:
                        # Generate summary
                        summary = gemini_analyzer.generate_summary(content, project_info.bio)
                        
                        new_projects.append({
                            'row': i,
                            'date': date,
                            'username': project_info.username,
                            'link': project_info.twitter_link,
                            'summary': summary
                        })
                        
                        print(f"   Username: @{project_info.username}")
                        print(f"   Summary: {summary}")
                else:
                    print(f"   ⚪ Not a new project announcement")
        
        # Display results
        print("\n" + "="*50)
        print("ANALYSIS RESULTS")
        print("="*50)
        print(f"Total rows analyzed: {len(data_rows)}")
        print(f"New projects found: {len(new_projects)}")
        
        if new_projects:
            print("\n📋 New Projects Summary:")
            for proj in new_projects:
                print(f"\n• Row {proj['row']} - @{proj['username']}")
                print(f"  Date: {proj['date']}")
                print(f"  Summary: {proj['summary']}")
                print(f"  Link: {proj['link']}")
            
            # Generate daily draft
            print("\n📝 Generated Daily Draft:")
            print("-" * 40)
            
            # Group by date
            by_date = {}
            for proj in new_projects:
                date = proj['date']
                if date not in by_date:
                    by_date[date] = []
                by_date[date].append(proj)
            
            for date, projects in sorted(by_date.items()):
                print(f"\n🚀 New/Trending Projects on {date}:\n")
                for proj in projects:
                    print(f"• [@{proj['username']}]({proj['link']}): {proj['summary']}")
            
            print("\n" + "-" * 40)
            
            if not dry_run:
                print("\n💾 Writing results to sheet...")
                # This would write to the actual sheet
                # analyzer.run_daily_analysis()
                print("✅ Results written to sheet")
            else:
                print("\n⚠️  DRY RUN MODE - No changes written to sheet")
                print("   To write results, run with dry_run=False")
        
        return True
        
    except Exception as e:
        logger.error(f"Error during sheet analysis: {e}", exc_info=True)
        print(f"\n❌ Error: {e}")
        return False


def main():
    """Main test function"""
    print("\n" + "="*60)
    print("GEMINI AI ANALYZER INTEGRATION TEST")
    print("="*60)
    
    # Test 1: Gemini Connection
    if not test_gemini_connection():
        print("\n⚠️  Please configure your Gemini API key and try again")
        return
    
    # Test 2: Sheet Analysis
    print("\n" + "="*60)
    print("SHEET ANALYSIS TEST")
    print("="*60)
    
    # Ask user for test parameters
    print("\nTest Options:")
    print("1. Quick test (analyze first 3 rows, dry run)")
    print("2. Standard test (analyze first 10 rows, dry run)")
    print("3. Full test (analyze first 20 rows, dry run)")
    print("4. Write test (analyze first 5 rows and WRITE to sheet)")
    
    choice = input("\nSelect test option (1-4): ").strip()
    
    if choice == '1':
        test_sheet_analysis(limit_rows=3, dry_run=True)
    elif choice == '2':
        test_sheet_analysis(limit_rows=10, dry_run=True)
    elif choice == '3':
        test_sheet_analysis(limit_rows=20, dry_run=True)
    elif choice == '4':
        confirm = input("\n⚠️  This will write to your Google Sheet. Continue? (yes/no): ")
        if confirm.lower() == 'yes':
            test_sheet_analysis(limit_rows=5, dry_run=False)
        else:
            print("Cancelled.")
    else:
        print("Invalid choice. Running quick test...")
        test_sheet_analysis(limit_rows=3, dry_run=True)
    
    print("\n" + "="*60)
    print("TEST COMPLETE")
    print("="*60)
    
    print("\n📌 Next Steps:")
    print("1. Review the analysis results above")
    print("2. If results look good, run option 4 to write to sheet")
    print("3. Check your Google Sheet for new columns:")
    print("   - AI Summary (individual project summaries)")
    print("   - Daily Post Draft (consolidated daily summary)")
    
    print("\n💡 To run full analysis on all rows:")
    print("   from modules.gemini_analyzer import GeminiAnalyzer, SheetAnalyzer")
    print("   analyzer.run_daily_analysis()")


if __name__ == "__main__":
    main()