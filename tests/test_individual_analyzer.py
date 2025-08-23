#!/usr/bin/env python3
"""
Test script for individual row analysis in GeminiAnalyzer
This tests the new sequential processing approach with 6-second delays
"""

import sys
import time
import logging
from pathlib import Path
from typing import List, Dict, Tuple
from datetime import datetime

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


class TestIndividualAnalyzer:
    """Test class for individual row analysis"""
    
    def __init__(self):
        """Initialize test components"""
        self.sheets_handler = None
        self.gemini_analyzer = None
        self.sheet_analyzer = None
        self.test_results = []
        
    def setup(self) -> bool:
        """Setup test components"""
        print("\n" + "="*60)
        print("SETUP: Initializing Components")
        print("="*60)
        
        try:
            # Check API key
            if not config.GEMINI_API_KEY or config.GEMINI_API_KEY == 'your_gemini_api_key_here':
                print("❌ GEMINI_API_KEY not configured in .env")
                return False
            
            # Initialize handlers
            print("📊 Initializing Google Sheets handler...")
            self.sheets_handler = GoogleSheetsHandler(
                credentials_path=config.GOOGLE_SERVICE_ACCOUNT_FILE,
                sheet_id=config.GOOGLE_SHEETS_ID
            )
            
            print("🤖 Initializing Gemini analyzer...")
            self.gemini_analyzer = GeminiAnalyzer(
                api_key=config.GEMINI_API_KEY,
                model=config.GEMINI_MODEL,
                daily_limit=config.GEMINI_DAILY_LIMIT
            )
            
            print("🔗 Creating sheet analyzer...")
            self.sheet_analyzer = SheetAnalyzer(
                self.sheets_handler, 
                self.gemini_analyzer
            )
            
            print("✅ All components initialized successfully")
            return True
            
        except Exception as e:
            print(f"❌ Setup failed: {e}")
            return False
    
    def test_single_row(self, row_idx: int, post_data: Dict) -> Dict:
        """Test analysis of a single row"""
        print(f"\n  Testing Row {row_idx}:")
        print(f"  Content: {post_data['content'][:80]}...")
        
        start_time = time.time()
        
        try:
            # Analyze the row
            project_summary, ai_summary = self.gemini_analyzer.analyze_single_row(
                row_idx, post_data
            )
            
            elapsed = time.time() - start_time
            
            result = {
                'row': row_idx,
                'success': True,
                'is_project': project_summary is not None,
                'summary': ai_summary,
                'username': project_summary.project_info.username if project_summary else None,
                'time': elapsed,
                'error': None
            }
            
            # Display result
            if project_summary:
                print(f"  ✅ NEW PROJECT: @{project_summary.project_info.username}")
                print(f"  Summary: {ai_summary[:80]}...")
            else:
                print(f"  ⚪ Not a new project: {ai_summary}")
            
            print(f"  ⏱️  Time: {elapsed:.1f} seconds")
            
        except Exception as e:
            elapsed = time.time() - start_time
            result = {
                'row': row_idx,
                'success': False,
                'is_project': False,
                'summary': None,
                'username': None,
                'time': elapsed,
                'error': str(e)
            }
            
            if "RATE_LIMITED" in str(e):
                print(f"  ⚠️  RATE LIMITED after {elapsed:.1f} seconds")
            else:
                print(f"  ❌ ERROR: {e}")
        
        self.test_results.append(result)
        return result
    
    def test_multiple_rows(self, limit: int = 5) -> None:
        """Test multiple rows sequentially"""
        print("\n" + "="*60)
        print(f"TEST 1: Individual Row Analysis (First {limit} Rows)")
        print("="*60)
        
        try:
            # Get sheet data
            rows = self.sheets_handler.get_sheet_data()
            
            if len(rows) <= 1:
                print("❌ No data rows in sheet to test")
                return
            
            headers = rows[0]
            data_rows = rows[1:limit + 1]  # Get first N rows
            
            print(f"Found {len(rows)-1} total rows, testing {len(data_rows)} rows")
            
            # Find column indices
            content_idx = headers.index('content') if 'content' in headers else 4
            post_link_idx = headers.index('post_link') if 'post_link' in headers else 3
            date_idx = headers.index('date') if 'date' in headers else 0
            
            # Test each row
            for i, row in enumerate(data_rows, start=2):
                if len(row) > content_idx:
                    post_data = {
                        'content': row[content_idx],
                        'post_link': row[post_link_idx] if len(row) > post_link_idx else '',
                        'date': row[date_idx] if len(row) > date_idx else ''
                    }
                    
                    result = self.test_single_row(i, post_data)
                    
                    # Stop if rate limited
                    if not result['success'] and 'RATE_LIMITED' in str(result['error']):
                        print("\n⚠️  Stopping test due to rate limit")
                        break
            
        except Exception as e:
            print(f"❌ Test failed: {e}")
    
    def test_analyze_all_rows(self, max_rows: int = 10) -> None:
        """Test the analyze_all_rows method"""
        print("\n" + "="*60)
        print(f"TEST 2: Analyze All Rows Method (Max {max_rows} Rows)")
        print("="*60)
        
        try:
            # Temporarily limit rows for testing
            original_data = self.sheets_handler.get_sheet_data()
            
            if len(original_data) <= 1:
                print("❌ No data rows in sheet to test")
                return
            
            # Create a limited dataset
            limited_data = [original_data[0]] + original_data[1:max_rows + 1]
            
            # Mock the get_sheet_data to return limited data
            self.sheets_handler.get_sheet_data = lambda: limited_data
            
            print(f"Testing with {len(limited_data) - 1} rows...")
            
            start_time = time.time()
            
            # Run the actual analyze_all_rows method
            summaries, all_processed = self.sheet_analyzer.analyze_all_rows()
            
            elapsed = time.time() - start_time
            
            # Restore original method
            self.sheets_handler.get_sheet_data = lambda: original_data
            
            # Display results
            print(f"\n✅ Analysis completed in {elapsed:.1f} seconds")
            print(f"   Total rows processed: {len(all_processed)}")
            print(f"   New projects found: {len(summaries)}")
            print(f"   Average time per row: {elapsed / max(len(all_processed), 1):.1f} seconds")
            
            if summaries:
                print("\n📋 Projects Found:")
                for summary in summaries[:5]:  # Show first 5
                    print(f"   • @{summary.project_info.username}: {summary.ai_summary[:60]}...")
            
            print("\n📊 Processing Summary:")
            for row_idx, ai_summary in all_processed[:5]:  # Show first 5
                status = "🆕 Project" if any(s.row_index == row_idx for s in summaries) else "⚪ Not Project"
                print(f"   Row {row_idx}: {status} - {ai_summary[:40]}...")
            
        except Exception as e:
            print(f"❌ Test failed: {e}")
    
    def test_rate_limit_handling(self) -> None:
        """Test rate limit handling"""
        print("\n" + "="*60)
        print("TEST 3: Rate Limit Handling")
        print("="*60)
        
        print("Creating test data for rapid API calls...")
        
        test_posts = [
            {'content': 'Just launched @TestProject1 - DeFi protocol', 'date': '2024-01-01', 'post_link': 'https://x.com/1'},
            {'content': 'New NFT collection @TestNFT dropping soon', 'date': '2024-01-01', 'post_link': 'https://x.com/2'},
            {'content': 'Introducing @TestDAO governance token', 'date': '2024-01-01', 'post_link': 'https://x.com/3'},
        ]
        
        print(f"Testing {len(test_posts)} rows in rapid succession...")
        
        for i, post_data in enumerate(test_posts, start=1):
            print(f"\n  Quick test {i}:")
            
            try:
                # No delay between tests to trigger rate limit
                _, summary = self.gemini_analyzer.analyze_single_row(100 + i, post_data)
                print(f"  ✅ Processed: {summary}")
            except Exception as e:
                if "RATE_LIMITED" in str(e):
                    print(f"  ⚠️  Rate limited as expected")
                    print("  Rate limit handling working correctly!")
                    break
                else:
                    print(f"  ❌ Unexpected error: {e}")
    
    def display_summary(self) -> None:
        """Display test summary"""
        print("\n" + "="*60)
        print("TEST SUMMARY")
        print("="*60)
        
        if not self.test_results:
            print("No test results to display")
            return
        
        # Calculate statistics
        successful = sum(1 for r in self.test_results if r['success'])
        failed = len(self.test_results) - successful
        projects_found = sum(1 for r in self.test_results if r['is_project'])
        avg_time = sum(r['time'] for r in self.test_results) / len(self.test_results)
        
        print(f"Total tests run: {len(self.test_results)}")
        print(f"✅ Successful: {successful}")
        print(f"❌ Failed: {failed}")
        print(f"🆕 Projects found: {projects_found}")
        print(f"⏱️  Average time per row: {avg_time:.1f} seconds")
        
        # Show errors if any
        errors = [r for r in self.test_results if r['error']]
        if errors:
            print("\n⚠️  Errors encountered:")
            for error in errors[:3]:  # Show first 3 errors
                print(f"   Row {error['row']}: {error['error']}")
        
        # Recommendations
        print("\n" + "="*60)
        print("RECOMMENDATIONS")
        print("="*60)
        
        if failed > 0 and any('RATE_LIMITED' in str(r['error']) for r in errors):
            print("""
⚠️  Rate limiting detected. Consider:
   1. Increasing delay between API calls (currently 6 seconds)
   2. Processing fewer rows per session
   3. Using SKIP_AI_ON_RATE_LIMIT=true in .env
   4. Waiting for daily quota reset
""")
        elif avg_time > 10:
            print("""
⏱️  Processing is slow but stable. This is expected with:
   - 6-second delays between API calls
   - Individual row processing
   - Multiple API calls per new project
""")
        else:
            print("✅ System is working as expected!")


def main():
    """Main test runner"""
    print("\n" + "="*60)
    print("GEMINI INDIVIDUAL ROW ANALYZER TEST")
    print("="*60)
    print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Model: {config.GEMINI_MODEL}")
    print(f"Daily Limit: {config.GEMINI_DAILY_LIMIT}")
    
    # Create tester
    tester = TestIndividualAnalyzer()
    
    # Setup
    if not tester.setup():
        print("\n❌ Setup failed. Please check configuration.")
        return
    
    # Run tests based on user choice
    print("\n" + "="*60)
    print("TEST OPTIONS")
    print("="*60)
    print("1. Quick Test (3 rows)")
    print("2. Standard Test (5 rows)")
    print("3. Extended Test (10 rows)")
    print("4. Test analyze_all_rows() method")
    print("5. Test rate limit handling")
    print("6. Run all tests")
    
    choice = input("\nSelect test option (1-6): ").strip()
    
    if choice == '1':
        tester.test_multiple_rows(3)
    elif choice == '2':
        tester.test_multiple_rows(5)
    elif choice == '3':
        tester.test_multiple_rows(10)
    elif choice == '4':
        tester.test_analyze_all_rows(5)
    elif choice == '5':
        tester.test_rate_limit_handling()
    elif choice == '6':
        print("\n🔄 Running all tests...")
        tester.test_multiple_rows(3)
        time.sleep(2)
        tester.test_analyze_all_rows(5)
        time.sleep(2)
        tester.test_rate_limit_handling()
    else:
        print("Invalid choice. Running quick test...")
        tester.test_multiple_rows(3)
    
    # Display summary
    tester.display_summary()
    
    print("\n" + "="*60)
    print("TEST COMPLETE")
    print("="*60)


if __name__ == "__main__":
    main()