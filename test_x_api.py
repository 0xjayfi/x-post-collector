#!/usr/bin/env python3
"""
Test script for X API authentication and permissions
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from modules.x_publisher import create_publisher
import config

def diagnose_x_api_error():
    """Diagnose X API authentication and permission issues"""
    
    print("=" * 60)
    print("X API DIAGNOSTIC TEST")
    print("=" * 60)
    
    # Check configuration
    print("\n1. Checking configuration...")
    if not config.validate_x_api_config():
        print("❌ X API configuration is incomplete")
        return
    
    print("✅ X API credentials found")
    
    # Create publisher
    print("\n2. Creating publisher...")
    publisher = create_publisher(
        'twitter',
        api_key=config.X_API_KEY,
        api_secret=config.X_API_SECRET,
        access_token=config.X_ACCESS_TOKEN,
        access_token_secret=config.X_ACCESS_TOKEN_SECRET
    )
    
    if not publisher:
        print("❌ Failed to create publisher")
        return
    
    print("✅ Publisher created")
    
    # Test publishing
    print("\n3. Testing tweet publishing...")
    result = publisher.publish("Test a post from api 🚀")
    
    if result.success:
        print(f"✅ Published: {result.url}")
    else:
        print(f"❌ Error: {result.error_msg}")
        
        # Diagnose the error
        if "forbidden" in result.error_msg.lower() or "403" in result.error_msg:
            print("\n🔧 SOLUTION: Fix App Permissions")
            print("-" * 40)
            print("Your X app doesn't have 'Write' permission.")
            print("\nStep-by-step fix:")
            print("\n1. Go to: https://developer.twitter.com/en/portal/projects-and-apps")
            print("2. Find and click on your app")
            print("3. Go to 'Settings' tab")
            print("4. Click 'Set up' under 'User authentication settings'")
            print("5. Set these values:")
            print("   - App permissions: ✅ Read and write")
            print("   - Type of App: Web App, Automated App or Bot")
            print("   - Callback URL: http://localhost:3000/callback")
            print("   - Website URL: https://example.com")
            print("6. Click 'Save'")
            print("\n7. CRITICAL: Regenerate your Access Token")
            print("   - Go to 'Keys and tokens' tab")
            print("   - Scroll to 'Authentication Tokens'")
            print("   - Click 'Regenerate' for Access Token and Secret")
            print("   - Copy the new tokens")
            print("\n8. Update your .env file with new tokens:")
            print("   X_ACCESS_TOKEN=<new_token>")
            print("   X_ACCESS_TOKEN_SECRET=<new_secret>")
            print("\n9. Run this test again")
            
        elif "unauthorized" in result.error_msg.lower() or "401" in result.error_msg:
            print("\n🔧 SOLUTION: Fix Authentication")
            print("-" * 40)
            print("Your credentials are invalid or expired.")
            print("\nVerify these in your .env file:")
            print("- X_API_KEY (Consumer Key)")
            print("- X_API_SECRET (Consumer Secret)")
            print("- X_ACCESS_TOKEN")
            print("- X_ACCESS_TOKEN_SECRET")

if __name__ == "__main__":
    diagnose_x_api_error()