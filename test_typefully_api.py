#!/usr/bin/env python3
"""
Test script for Typefully API authentication and draft creation
"""

import sys
from pathlib import Path
from datetime import datetime, timedelta
sys.path.insert(0, str(Path(__file__).parent))

from modules.x_publisher import create_publisher
import config

def test_typefully_api():
    """Test Typefully API authentication and draft creation"""
    
    print("=" * 60)
    print("TYPEFULLY API TEST")
    print("=" * 60)
    
    # Check configuration
    print("\n1. Checking configuration...")
    if not config.TYPEFULLY_API_KEY or config.TYPEFULLY_API_KEY == 'your_typefully_api_key':
        print("❌ TYPEFULLY_API_KEY not configured in .env")
        print("   Please add your Typefully API key to .env file")
        return False
    
    print("✅ Typefully API key found in .env")
    print(f"   API Key: {config.TYPEFULLY_API_KEY[:10]}...")
    
    # Display scheduling configuration
    print("\n2. Scheduling configuration:")
    if config.TYPEFULLY_HOURS_DELAY > 0:
        scheduled_time_utc = datetime.utcnow() + timedelta(hours=config.TYPEFULLY_HOURS_DELAY)
        scheduled_time_local = datetime.now() + timedelta(hours=config.TYPEFULLY_HOURS_DELAY)
        print(f"   ⏰ Posts will be scheduled for:")
        print(f"      UTC: {scheduled_time_utc.strftime('%Y-%m-%d %H:%M:%S')} UTC")
        print(f"      Local: {scheduled_time_local.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"   (In {config.TYPEFULLY_HOURS_DELAY} hours from now)")
    else:
        print(f"   ⏰ Using schedule: {config.TYPEFULLY_SCHEDULE}")
    
    # Test authentication
    print("\n3. Testing authentication...")
    try:
        publisher = create_publisher(
            'typefully',
            api_key=config.TYPEFULLY_API_KEY,
            schedule=config.TYPEFULLY_SCHEDULE,
            hours_delay=config.TYPEFULLY_HOURS_DELAY
        )
        
        if publisher:
            print("✅ Authentication successful!")
            
            # Test with a sample draft
            print("\n4. Testing draft creation...")
            
            # Ask user for confirmation
            print("\n⚠️  This will create a draft in your Typefully account.")
            confirm = input("Do you want to continue? (yes/no): ")
            
            if confirm.lower() != 'yes':
                print("Test cancelled.")
                return False
            
            # Create test content
            test_content = f"""🧪 Test Draft from Discord-to-Sheets Bot

This is an automated test draft created at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

🚀 New/Trending Projects:
• @TestProject1: This is a sample project description
• @TestProject2: Another test project for validation

#Test #CryptoBot #Automation"""
            
            print("\nCreating draft with content:")
            print("-" * 40)
            print(test_content)
            print("-" * 40)
            
            result = publisher.publish(test_content)
            
            if result.success:
                print(f"\n✅ Draft created successfully!")
                print(f"   Draft URL: {result.url}")
                print(f"   Draft ID: {result.post_id}")
                
                if config.TYPEFULLY_HOURS_DELAY > 0:
                    scheduled_time_utc = datetime.utcnow() + timedelta(hours=config.TYPEFULLY_HOURS_DELAY)
                    scheduled_time_local = datetime.now() + timedelta(hours=config.TYPEFULLY_HOURS_DELAY)
                    print(f"   Scheduled for:")
                    print(f"      UTC: {scheduled_time_utc.strftime('%Y-%m-%d %H:%M:%S')} UTC")
                    print(f"      Local: {scheduled_time_local.strftime('%Y-%m-%d %H:%M:%S')}")
                else:
                    print(f"   Schedule: {config.TYPEFULLY_SCHEDULE}")
                
                print("\n📝 Next steps:")
                print("   1. Visit Typefully to review the draft")
                print("   2. You can edit or delete the draft from Typefully dashboard")
                print("   3. The draft will be published according to the schedule")
                
            else:
                print(f"\n❌ Failed to create draft")
                print(f"   Error: {result.error_msg}")
                
                if "401" in str(result.error_msg) or "unauthorized" in result.error_msg.lower():
                    print("\n🔧 SOLUTION: Check API Key")
                    print("-" * 40)
                    print("Your API key may be invalid.")
                    print("\nTo get a valid API key:")
                    print("1. Log in to Typefully: https://typefully.com")
                    print("2. Go to Settings → API")
                    print("3. Generate a new API key")
                    print("4. Update TYPEFULLY_API_KEY in your .env file")
                
                return False
        else:
            print("❌ Failed to create publisher")
            print("   Check your API key and try again")
            return False
            
    except ImportError:
        print("❌ requests library not installed")
        print("   Run: pip install requests")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False
    
    return True

def test_schedule_options():
    """Test different scheduling options"""
    
    print("\n" + "=" * 60)
    print("SCHEDULING OPTIONS TEST")
    print("=" * 60)
    
    print("\nAvailable scheduling options:")
    print("1. Immediate: 'next-free-slot'")
    print("2. Hours delay: Set TYPEFULLY_HOURS_DELAY in .env (e.g., 2, 4, 8)")
    print("3. Specific time: ISO format (e.g., '2025-08-17T15:00:00Z')")
    
    print("\nCurrent configuration:")
    print(f"TYPEFULLY_SCHEDULE: {config.TYPEFULLY_SCHEDULE}")
    print(f"TYPEFULLY_HOURS_DELAY: {config.TYPEFULLY_HOURS_DELAY}")
    
    if config.TYPEFULLY_HOURS_DELAY > 0:
        scheduled_time_utc = datetime.utcnow() + timedelta(hours=config.TYPEFULLY_HOURS_DELAY)
        scheduled_time_local = datetime.now() + timedelta(hours=config.TYPEFULLY_HOURS_DELAY)
        print(f"\n📅 Posts will be scheduled for:")
        print(f"   UTC: {scheduled_time_utc.strftime('%Y-%m-%d %H:%M:%S')} UTC")
        print(f"   Local: {scheduled_time_local.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"   (In {config.TYPEFULLY_HOURS_DELAY} hours from now)")
    else:
        print(f"\n📅 Using schedule: {config.TYPEFULLY_SCHEDULE}")
    
    print("\nTo change scheduling:")
    print("1. Edit .env file")
    print("2. Set TYPEFULLY_HOURS_DELAY to desired hours (0 to disable)")
    print("3. Or set TYPEFULLY_SCHEDULE to 'next-free-slot' or ISO datetime")

def main():
    """Main test function"""
    
    print("\nTypefully API Test Suite\n")
    
    # Show scheduling options
    test_schedule_options()
    
    # Ask user if they want to proceed with test
    print("\n" + "=" * 60)
    print("\nWould you like to test the Typefully API?")
    print("This will create a test draft in your Typefully account.")
    
    choice = input("\nProceed with test? (yes/no): ")
    
    if choice.lower() == 'yes':
        success = test_typefully_api()
        
        if success:
            print("\n✅ All tests passed! Your Typefully API is ready to use.")
            print("\n💡 Tips:")
            print("- You can change scheduling by modifying TYPEFULLY_HOURS_DELAY in .env")
            print("- Set to 0 for immediate posting (next-free-slot)")
            print("- Set to 2, 4, or 8 for delayed posting")
        else:
            print("\n❌ Tests failed. Please fix the issues above and try again.")
    else:
        print("\nTest cancelled. No drafts were created.")
        print("\n💡 When you're ready, run this script again to test Typefully integration.")

if __name__ == "__main__":
    main()