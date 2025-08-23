#!/usr/bin/env python3
"""
Test Complete Workflow

This script tests the complete pipeline:
1. AI Analysis (optional)
2. Publishing (optional)
3. Archiving (always runs)
"""

import sys
import logging
from pathlib import Path
from dotenv import load_dotenv

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from modules.sheets_handler import GoogleSheetsHandler
from modules.workflow_orchestrator import WorkflowOrchestrator
import config

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()


def show_configuration():
    """Show current configuration status"""
    print("\n📋 Configuration Status:")
    print("-" * 50)
    
    # Google Sheets
    sheets_ok = config.validate_config()
    print(f"{'✅' if sheets_ok else '❌'} Google Sheets: "
          f"{'Configured' if sheets_ok else 'Not configured'}")
    
    # Gemini AI
    gemini_ok = config.GEMINI_API_KEY and config.GEMINI_API_KEY != 'your_gemini_api_key'
    print(f"{'✅' if gemini_ok else '⚠️'} Gemini AI: "
          f"{'Configured' if gemini_ok else 'Not configured (analysis will be skipped)'}")
    
    # X API
    x_api_ok = config.validate_x_api_config()
    print(f"{'✅' if x_api_ok else '⚠️'} X API: "
          f"{'Configured' if x_api_ok else 'Not configured'}")
    
    # Typefully
    typefully_ok = config.TYPEFULLY_API_KEY and config.TYPEFULLY_API_KEY != 'your_typefully_api_key'
    print(f"{'✅' if typefully_ok else '⚠️'} Typefully: "
          f"{'Configured' if typefully_ok else 'Not configured'}")
    
    # Publisher
    publisher_type = None
    if x_api_ok:
        publisher_type = "X API"
    elif typefully_ok:
        publisher_type = "Typefully"
    
    print(f"\n📢 Publisher: {publisher_type or 'Not configured (publishing will be skipped)'}")
    
    return sheets_ok, gemini_ok, x_api_ok, typefully_ok


def test_complete_workflow():
    """Test the complete workflow"""
    
    print("\n" + "="*70)
    print("COMPLETE WORKFLOW TEST")
    print("="*70)
    
    # Show configuration
    sheets_ok, gemini_ok, x_api_ok, typefully_ok = show_configuration()
    
    if not sheets_ok:
        print("\n❌ Google Sheets not configured. Cannot proceed.")
        print("Please check your .env file and credentials.")
        return False
    
    # Ask what to run
    print("\n🔧 Workflow Components:")
    components = []
    
    if gemini_ok:
        print("1. AI Analysis - Analyze posts and generate summaries")
        components.append("analysis")
    else:
        print("1. AI Analysis - SKIPPED (not configured)")
    
    if x_api_ok or typefully_ok:
        pub_type = "X API" if x_api_ok else "Typefully"
        print(f"2. Publishing - Publish daily draft via {pub_type}")
        components.append("publishing")
    else:
        print("2. Publishing - SKIPPED (not configured)")
    
    print("3. Archiving - Archive processed posts (always runs)")
    components.append("archiving")
    
    print("\n" + "-"*50)
    print("\nWhat would you like to run?")
    print("1. Complete workflow (all configured components)")
    print("2. Only archiving")
    print("3. Custom selection")
    
    choice = input("\nSelect option (1-3): ").strip()
    
    run_analysis = False
    run_publishing = False
    run_archiving = True  # Always run
    
    if choice == '1':
        run_analysis = gemini_ok
        run_publishing = x_api_ok or typefully_ok
    elif choice == '2':
        run_analysis = False
        run_publishing = False
    elif choice == '3':
        if gemini_ok:
            run_analysis = input("Run AI analysis? (yes/no): ").lower() == 'yes'
        if x_api_ok or typefully_ok:
            run_publishing = input("Run publishing? (yes/no): ").lower() == 'yes'
        run_archiving = input("Run archiving? (yes/no): ").lower() == 'yes'
    
    # Confirm
    print("\n📌 Will run:")
    if run_analysis:
        print("  ✓ AI Analysis")
    if run_publishing:
        print("  ✓ Publishing")
    if run_archiving:
        print("  ✓ Archiving")
    
    confirm = input("\nProceed? (yes/no): ")
    if confirm.lower() != 'yes':
        print("Cancelled.")
        return False
    
    try:
        # Initialize sheets handler
        print("\n🔄 Initializing...")
        sheets_handler = GoogleSheetsHandler(
            credentials_path=config.GOOGLE_SERVICE_ACCOUNT_FILE,
            sheet_id=config.GOOGLE_SHEETS_ID
        )
        
        # Prepare configuration
        gemini_key = config.GEMINI_API_KEY if run_analysis else None
        
        publisher_config = None
        if run_publishing:
            if x_api_ok:
                publisher_config = {
                    'type': 'twitter',
                    'api_key': config.X_API_KEY,
                    'api_secret': config.X_API_SECRET,
                    'access_token': config.X_ACCESS_TOKEN,
                    'access_token_secret': config.X_ACCESS_TOKEN_SECRET
                }
            elif typefully_ok:
                publisher_config = {
                    'type': 'typefully',
                    'api_key': config.TYPEFULLY_API_KEY,
                    'hours_delay': config.TYPEFULLY_HOURS_DELAY
                }
        
        # Initialize orchestrator
        orchestrator = WorkflowOrchestrator(
            sheets_handler=sheets_handler,
            gemini_api_key=gemini_key,
            publisher_config=publisher_config
        )
        
        # Run workflow
        print("\n🚀 Starting workflow...")
        print("="*60)
        
        if not (run_analysis or run_publishing):
            # Just run archiving
            results = orchestrator.run_archiving()
            
            print("\n" + "="*60)
            print("RESULTS")
            print("="*60)
            
            if results['success']:
                print(f"✅ Archiving successful!")
                print(f"   Posts archived: {results['posts_archived']}")
            else:
                print(f"❌ Archiving failed: {results['errors']}")
        else:
            # Run complete workflow
            results = orchestrator.run_complete_workflow()
            
            print("\n" + "="*60)
            print("WORKFLOW RESULTS")
            print("="*60)
            
            print(f"\n{'✅' if results['overall_success'] else '❌'} "
                  f"Overall: {'Success' if results['overall_success'] else 'Failed'}")
            
            print("\nSummary:")
            for line in results['summary']:
                print(f"  {line}")
            
            # Detailed results
            if results['analysis']:
                print(f"\n📊 Analysis: {results['analysis']['posts_analyzed']} posts, "
                      f"{results['analysis']['projects_found']} projects")
            
            if results['publishing'] and results['publishing']['published']:
                print(f"\n📢 Published: {results['publishing']['url'] or results['publishing']['post_id']}")
            
            if results['archiving']:
                print(f"\n📚 Archived: {results['archiving']['posts_archived']} posts")
        
        return True
        
    except Exception as e:
        logger.error(f"Workflow failed: {e}", exc_info=True)
        print(f"\n❌ Error: {e}")
        return False


def main():
    """Main test function"""
    
    print("\n" + "="*70)
    print("COMPLETE WORKFLOW TEST SUITE")
    print("="*70)
    
    print("\nThis script tests the complete pipeline:")
    print("• AI Analysis (if configured)")
    print("• Publishing (if configured)")
    print("• Archiving (always available)")
    
    test_complete_workflow()
    
    print("\n" + "="*70)
    print("TEST COMPLETE")
    print("="*70)
    
    print("\n📌 Next Steps:")
    print("1. Check your Google Sheets for results")
    print("2. View Archives sheet for archived posts")
    print("3. Check X/Typefully for published content")
    print("4. Schedule this workflow to run daily")


if __name__ == "__main__":
    main()