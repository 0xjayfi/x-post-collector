#!/usr/bin/env python3
"""
Debug script for Typefully API - tests different endpoints and configurations
"""

import sys
import requests
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

import config

def test_typefully_raw():
    """Test Typefully API with raw requests to debug issues"""
    
    print("=" * 60)
    print("TYPEFULLY API DEBUG TEST")
    print("=" * 60)
    
    api_key = config.TYPEFULLY_API_KEY
    
    if not api_key or api_key == 'your_typefully_api_key':
        print("❌ No API key found in .env")
        return
    
    print(f"\n📝 API Key: {api_key[:10]}...")
    
    # Test different header formats
    headers_options = [
        {"X-API-KEY": api_key},
        {"X-API-KEY": f"Bearer {api_key}"},
        {"Authorization": f"Bearer {api_key}"},
        {"Authorization": api_key}
    ]
    
    # Test different endpoints
    endpoints = [
        "https://api.typefully.com/v1/drafts/",
        "https://api.typefully.com/v1/drafts",
        "https://api.typefully.com/drafts/",
        "https://api.typefully.com/v1/profiles/",
        "https://api.typefully.com/v1/me"
    ]
    
    print("\n🔍 Testing different configurations...")
    print("-" * 40)
    
    for endpoint in endpoints:
        print(f"\n📍 Endpoint: {endpoint}")
        
        for i, headers in enumerate(headers_options, 1):
            header_desc = list(headers.keys())[0] + ": " + (
                headers[list(headers.keys())[0]][:20] + "..." 
                if "Bearer" in headers[list(headers.keys())[0]] 
                else headers[list(headers.keys())[0]][:10] + "..."
            )
            
            try:
                response = requests.get(endpoint, headers=headers, timeout=5)
                
                if response.status_code == 200:
                    print(f"   ✅ Option {i} ({header_desc}): SUCCESS")
                    print(f"      Status: {response.status_code}")
                    
                    # Try to parse response
                    try:
                        data = response.json()
                        print(f"      Response type: {type(data).__name__}")
                        if isinstance(data, list):
                            print(f"      Items: {len(data)}")
                        elif isinstance(data, dict):
                            print(f"      Keys: {list(data.keys())[:5]}")
                    except:
                        print(f"      Response: {response.text[:100]}")
                    
                    # Found working configuration
                    print("\n" + "=" * 40)
                    print("✅ WORKING CONFIGURATION FOUND!")
                    print("=" * 40)
                    print(f"Endpoint: {endpoint}")
                    print(f"Header: {header_desc}")
                    print("\nUpdate x_publisher.py with these settings if needed.")
                    return True
                    
                elif response.status_code == 401:
                    print(f"   ❌ Option {i} ({header_desc}): Unauthorized")
                elif response.status_code == 404:
                    print(f"   ❌ Option {i} ({header_desc}): Not Found")
                else:
                    print(f"   ⚠️  Option {i} ({header_desc}): {response.status_code}")
                    
            except requests.exceptions.Timeout:
                print(f"   ⏱️  Option {i}: Timeout")
            except requests.exceptions.ConnectionError:
                print(f"   🔌 Option {i}: Connection Error")
            except Exception as e:
                print(f"   ❓ Option {i}: {type(e).__name__}")
    
    print("\n" + "=" * 40)
    print("❌ No working configuration found")
    print("=" * 40)
    print("\nPossible issues:")
    print("1. API key might be invalid")
    print("2. Typefully API might have changed")
    print("3. Network/firewall issues")
    print("\nNext steps:")
    print("1. Verify your API key at https://typefully.com")
    print("2. Check Typefully API documentation")
    print("3. Contact Typefully support if needed")
    
    return False

def test_create_draft_raw():
    """Test creating a draft with raw request"""
    
    print("\n" + "=" * 60)
    print("TESTING DRAFT CREATION")
    print("=" * 60)
    
    api_key = config.TYPEFULLY_API_KEY
    
    if not api_key:
        print("❌ No API key found")
        return
    
    # Use the simplest working configuration
    headers = {"X-API-KEY": api_key}
    url = "https://api.typefully.com/v1/drafts/"
    
    # Test content
    content = "Test draft from API debug script"
    
    payload = {
        "content": content,
        "schedule-date": "next-free-slot"
    }
    
    print(f"\n📝 Creating draft...")
    print(f"   URL: {url}")
    print(f"   Headers: X-API-KEY: {api_key[:10]}...")
    print(f"   Content: {content}")
    
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=10)
        
        print(f"\n📊 Response Status: {response.status_code}")
        
        if response.status_code in [200, 201]:
            print("✅ Draft created successfully!")
            data = response.json()
            print(f"   Response: {data}")
        else:
            print("❌ Failed to create draft")
            print(f"   Response: {response.text}")
            
            # Try to parse error
            try:
                error_data = response.json()
                if 'error' in error_data:
                    print(f"   Error: {error_data['error']}")
                elif 'message' in error_data:
                    print(f"   Message: {error_data['message']}")
            except:
                pass
                
    except Exception as e:
        print(f"❌ Exception: {e}")

def main():
    """Run debug tests"""
    
    print("\nTypefully API Debug Tool\n")
    
    # First test endpoints
    if test_typefully_raw():
        # If we found a working configuration, ask to test draft
        print("\n" + "=" * 60)
        choice = input("\nTest draft creation? (yes/no): ")
        if choice.lower() == 'yes':
            test_create_draft_raw()
    
    print("\n✅ Debug complete")

if __name__ == "__main__":
    main()