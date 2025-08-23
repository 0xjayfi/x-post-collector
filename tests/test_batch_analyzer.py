#!/usr/bin/env python3
"""
Test script for optimizing GeminiAnalyzer.batch_analyze_projects() method
This tests the batch processing to identify and fix rate limiting issues
"""

import sys
import time
import logging
from pathlib import Path
from typing import List, Tuple, Dict

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from modules.sheets_handler import GoogleSheetsHandler
from modules.gemini_analyzer import GeminiAnalyzer
import config

# Setup logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def test_single_post_analysis():
    """Test analyzing a single post to establish baseline"""
    print("\n" + "="*60)
    print("TEST 1: Single Post Analysis")
    print("="*60)
    
    try:
        gemini = GeminiAnalyzer(
            api_key=config.GEMINI_API_KEY,
            model=config.GEMINI_MODEL,
            daily_limit=config.GEMINI_DAILY_LIMIT
        )
        
        # Test post
        test_content = """New project:[@boom_protocol](https://twitter.com/boom_protocol)
(follower 339)
Bio:The best trading venue on-chain. Natively built on RISE. Coming sooner than you think."""
        
        start_time = time.time()
        is_project = gemini.is_new_project(test_content)
        elapsed = time.time() - start_time
        
        print(f"✅ Single post analyzed in {elapsed:.2f} seconds")
        print(f"   Result: {'New Project' if is_project else 'Not a Project'}")
        
        return True
        
    except Exception as e:
        print(f"❌ Single post analysis failed: {e}")
        return False


def test_batch_analysis_current():
    """Test current batch_analyze_projects implementation"""
    print("\n" + "="*60)
    print("TEST 2: Current Batch Analysis Implementation")
    print("="*60)
    
    try:
        gemini = GeminiAnalyzer(
            api_key=config.GEMINI_API_KEY,
            model=config.GEMINI_MODEL,
            daily_limit=config.GEMINI_DAILY_LIMIT
        )
        
        # Create test batch
        test_posts = [
            (2, {'content': 'Just launched a new DeFi protocol with innovative yield farming'}),
            (3, {'content': 'Good morning crypto fam! Another day in the markets'}),
            (4, {'content': 'New project: @TestProtocol - Revolutionary blockchain solution'}),
            (5, {'content': 'Check out this analysis of Bitcoin price action'}),
            (6, {'content': 'Introducing @NewDAO - Decentralized governance platform'})
        ]
        
        print(f"Testing batch of {len(test_posts)} posts...")
        
        start_time = time.time()
        try:
            results = gemini.batch_analyze_projects(test_posts)
            elapsed = time.time() - start_time
            
            print(f"✅ Batch analyzed in {elapsed:.2f} seconds")
            print(f"   Results: {results}")
            
            # Calculate efficiency
            time_per_post = elapsed / len(test_posts)
            print(f"   Time per post: {time_per_post:.2f} seconds")
            
        except Exception as e:
            elapsed = time.time() - start_time
            if "RATE_LIMITED" in str(e):
                print(f"⚠️  Rate limited after {elapsed:.2f} seconds")
            else:
                print(f"❌ Batch analysis failed: {e}")
            return False
            
        return True
        
    except Exception as e:
        print(f"❌ Test setup failed: {e}")
        return False


def test_optimized_batch_analysis():
    """Test optimized batch analysis with better rate limiting"""
    print("\n" + "="*60)
    print("TEST 3: Optimized Batch Analysis")
    print("="*60)
    
    try:
        # Create a custom optimized version
        class OptimizedGeminiAnalyzer(GeminiAnalyzer):
            def batch_analyze_projects_optimized(self, posts: List[Tuple[int, Dict]]) -> List[Tuple[int, bool]]:
                """Optimized batch analysis with better rate limiting"""
                if not posts:
                    return []
                
                results = []
                
                # Process in smaller chunks with delays
                chunk_size = 3  # Smaller chunks
                chunks = [posts[i:i+chunk_size] for i in range(0, len(posts), chunk_size)]
                
                for i, chunk in enumerate(chunks):
                    if i > 0:
                        # Add delay between chunks
                        delay = 2  # 2 seconds between chunks
                        logger.info(f"Waiting {delay}s before next chunk...")
                        time.sleep(delay)
                    
                    # Build combined prompt for chunk
                    prompt = "Analyze these posts and identify which are about NEW crypto/Web3 projects:\n\n"
                    
                    for idx, (row_idx, post) in enumerate(chunk):
                        content = post.get('content', '')[:150]
                        prompt += f"Post {idx + 1}: {content}\n\n"
                    
                    prompt += """For each post, respond ONLY with:
Post 1: YES or NO
Post 2: YES or NO
etc.

YES = New project announcement
NO = Not a new project"""
                    
                    try:
                        response = self._make_request(prompt, temperature=0.1)
                        
                        # Parse response
                        for idx, (row_idx, _) in enumerate(chunk):
                            # Look for Post N: YES/NO pattern
                            import re
                            pattern = f"Post {idx + 1}:? *(YES|NO|yes|no)"
                            match = re.search(pattern, response, re.IGNORECASE)
                            
                            if match:
                                is_project = match.group(1).upper() == "YES"
                            else:
                                is_project = False
                            
                            results.append((row_idx, is_project))
                            
                    except Exception as e:
                        logger.error(f"Error in chunk {i}: {e}")
                        # Default to False for failed chunks
                        for row_idx, _ in chunk:
                            results.append((row_idx, False))
                        
                        if "RATE_LIMITED" in str(e):
                            raise  # Re-raise rate limit errors
                
                return results
        
        gemini = OptimizedGeminiAnalyzer(
            api_key=config.GEMINI_API_KEY,
            model=config.GEMINI_MODEL,
            daily_limit=config.GEMINI_DAILY_LIMIT
        )
        
        # Test batch
        test_posts = [
            (2, {'content': 'Just launched a new DeFi protocol with innovative yield farming'}),
            (3, {'content': 'Good morning crypto fam! Another day in the markets'}),
            (4, {'content': 'New project: @TestProtocol - Revolutionary blockchain solution'}),
            (5, {'content': 'Check out this analysis of Bitcoin price action'}),
            (6, {'content': 'Introducing @NewDAO - Decentralized governance platform'}),
            (7, {'content': 'Market update: BTC holding strong above 50k'}),
            (8, {'content': 'Excited to announce @Web3Game - Play to earn gaming platform'})
        ]
        
        print(f"Testing optimized batch of {len(test_posts)} posts...")
        
        start_time = time.time()
        try:
            results = gemini.batch_analyze_projects_optimized(test_posts)
            elapsed = time.time() - start_time
            
            print(f"✅ Optimized batch analyzed in {elapsed:.2f} seconds")
            print(f"   Results:")
            for row_idx, is_project in results:
                post_content = test_posts[row_idx-2][1]['content'][:50]
                print(f"   Row {row_idx}: {'✅ Project' if is_project else '❌ Not Project'} - {post_content}...")
            
            # Calculate efficiency
            time_per_post = elapsed / len(test_posts)
            print(f"\n   Time per post: {time_per_post:.2f} seconds")
            print(f"   Total API calls: {len([c for c in [test_posts[i:i+3] for i in range(0, len(test_posts), 3)]])}")
            
        except Exception as e:
            elapsed = time.time() - start_time
            if "RATE_LIMITED" in str(e):
                print(f"⚠️  Rate limited after {elapsed:.2f} seconds")
                print("   Consider reducing chunk size or increasing delays")
            else:
                print(f"❌ Optimized batch analysis failed: {e}")
            return False
            
        return True
        
    except Exception as e:
        print(f"❌ Test setup failed: {e}")
        return False


def test_with_sheet_data():
    """Test with actual Google Sheets data"""
    print("\n" + "="*60)
    print("TEST 4: Analysis with Real Sheet Data")
    print("="*60)
    
    try:
        # Load sheet data
        sheets = GoogleSheetsHandler(
            config.GOOGLE_SERVICE_ACCOUNT_FILE,
            config.GOOGLE_SHEETS_ID
        )
        
        rows = sheets.get_sheet_data()
        if len(rows) <= 1:
            print("❌ No data in sheet")
            return False
        
        headers = rows[0]
        content_idx = headers.index('Content') if 'Content' in headers else 2
        
        # Get first 10 unprocessed rows
        test_batch = []
        for i, row in enumerate(rows[1:11], start=2):
            if len(row) > content_idx:
                test_batch.append((i, {'content': row[content_idx]}))
        
        print(f"Testing with {len(test_batch)} rows from sheet...")
        
        gemini = GeminiAnalyzer(
            api_key=config.GEMINI_API_KEY,
            model=config.GEMINI_MODEL,
            daily_limit=config.GEMINI_DAILY_LIMIT
        )
        
        # Test different batch sizes
        for batch_size in [2, 3, 5]:
            print(f"\n  Testing batch size: {batch_size}")
            
            chunk = test_batch[:batch_size]
            start_time = time.time()
            
            try:
                results = gemini.batch_analyze_projects(chunk)
                elapsed = time.time() - start_time
                
                print(f"  ✅ Batch size {batch_size}: {elapsed:.2f}s ({elapsed/batch_size:.2f}s per post)")
                
                # Add delay to avoid rate limiting
                time.sleep(3)
                
            except Exception as e:
                if "RATE_LIMITED" in str(e):
                    print(f"  ⚠️  Batch size {batch_size}: Rate limited")
                    break
                else:
                    print(f"  ❌ Batch size {batch_size}: {e}")
        
        return True
        
    except Exception as e:
        print(f"❌ Sheet data test failed: {e}")
        return False


def main():
    """Main test runner"""
    print("\n" + "="*60)
    print("GEMINI BATCH ANALYZER OPTIMIZATION TEST")
    print("="*60)
    
    # Check API key
    if not config.GEMINI_API_KEY or config.GEMINI_API_KEY == 'your_gemini_api_key_here':
        print("❌ GEMINI_API_KEY not configured in .env")
        return
    
    print("\nThis test will help identify optimal batch processing settings")
    print("to avoid rate limiting issues.\n")
    
    # Run tests
    tests = [
        ("Single Post Baseline", test_single_post_analysis),
        ("Current Batch Implementation", test_batch_analysis_current),
        ("Optimized Batch Implementation", test_optimized_batch_analysis),
        ("Real Sheet Data", test_with_sheet_data)
    ]
    
    results = []
    for name, test_func in tests:
        print(f"\nRunning: {name}")
        print("-" * 40)
        
        success = test_func()
        results.append((name, success))
        
        # Delay between tests
        if success:
            print("Waiting 5 seconds before next test...")
            time.sleep(5)
    
    # Summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    
    for name, success in results:
        status = "✅ PASSED" if success else "❌ FAILED"
        print(f"{name}: {status}")
    
    print("\n" + "="*60)
    print("RECOMMENDATIONS")
    print("="*60)
    
    print("""
Based on the test results, here are the optimizations to implement:

1. **Reduce Batch Size**: Process 2-3 posts per API call instead of 5
2. **Add Delays**: Wait 2-3 seconds between API calls
3. **Implement Caching**: Cache results for already analyzed content
4. **Use Exponential Backoff**: When rate limited, wait progressively longer
5. **Process Incrementally**: Save progress after each successful batch

To implement these optimizations:
1. Update batch_analyze_projects() in gemini_analyzer.py
2. Reduce chunk size from 5 to 3
3. Add time.sleep(2) between chunks
4. Implement better error handling for partial results
""")


if __name__ == "__main__":
    main()