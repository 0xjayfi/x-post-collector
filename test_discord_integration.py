"""Integration tests for discord_handler module with real Discord connection.

This file tests the actual Discord connection and message fetching.
Run with: python test_discord_integration.py
"""

import asyncio
import os
import sys
import csv
from datetime import datetime, timedelta
from dotenv import load_dotenv

# Add parent directory to path to import modules
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from modules.discord_handler import DiscordHandler, TwitterPost


def export_posts_to_csv(posts, filename="discord_posts_export.csv"):
    """Export TwitterPost objects to CSV file.
    
    Args:
        posts: List of TwitterPost objects
        filename: Output CSV filename
    """
    if not posts:
        print(f"  No posts to export to {filename}")
        return
        
    fieldnames = ['date', 'time', 'author', 'post_link', 'content', 'author_link']
    
    with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        
        for post in posts:
            writer.writerow({
                'date': post.date,
                'time': post.time,
                'author': post.author,
                'post_link': post.post_link,
                'content': post.content,
                'author_link': post.author_link
            })
    
    print(f"✓ Exported {len(posts)} posts to {filename}")


async def test_connection():
    """Test actual Discord connection."""
    print("\n=== Testing Discord Connection ===")
    
    load_dotenv()
    token = os.getenv('DISCORD_TOKEN')
    channel_id = os.getenv('DISCORD_CHANNEL_ID')
    
    if not token or not channel_id:
        print("❌ Missing DISCORD_TOKEN or DISCORD_CHANNEL_ID in .env file")
        return False
        
    print(f"✓ Found credentials")
    print(f"  Channel ID: {channel_id}")
    
    handler = DiscordHandler(token, channel_id)
    
    try:
        print("Connecting to Discord...")
        await handler.connect()
        print("✓ Successfully connected to Discord")
        
        # Verify bot is ready
        if handler._ready:
            print(f"✓ Bot is ready and logged in as {handler.bot.user}")
        else:
            print("❌ Bot failed to become ready")
            return False
            
        # Test channel access
        channel = handler.bot.get_channel(handler.channel_id)
        if channel:
            print(f"✓ Found channel: #{channel.name}")
        else:
            print(f"❌ Could not find channel with ID {channel_id}")
            return False
            
    except Exception as e:
        print(f"❌ Failed to connect: {e}")
        return False
        
    finally:
        await handler.disconnect()
        print("✓ Disconnected from Discord")
        
    return True


async def test_fetch_messages():
    """Test fetching messages from Discord channel."""
    print("\n=== Testing Message Fetching ===")
    
    load_dotenv()
    token = os.getenv('DISCORD_TOKEN')
    channel_id = os.getenv('DISCORD_CHANNEL_ID')
    
    handler = DiscordHandler(token, channel_id)
    
    try:
        await handler.connect()
        print("Connected to Discord")
        
        # Fetch recent messages
        print("\nFetching last 10 messages...")
        messages = await handler.fetch_channel_messages(limit=10)
        print(f"✓ Fetched {len(messages)} messages")
        
        if messages:
            print("\nFirst 3 messages preview:")
            for i, msg in enumerate(messages[:3], 1):
                print(f"\n  Message {i}:")
                print(f"    Author: {msg.author.name}")
                print(f"    Date: {msg.created_at}")
                print(f"    Content: {msg.content[:100]}...")
        else:
            print("  No messages found in channel")
            
    except Exception as e:
        print(f"❌ Failed to fetch messages: {e}")
        return False
        
    finally:
        await handler.disconnect()
        
    return True


async def test_filter_twitter_posts():
    """Test filtering Twitter/X posts from Discord messages."""
    print("\n=== Testing Twitter Post Filtering ===")
    
    load_dotenv()
    token = os.getenv('DISCORD_TOKEN')
    channel_id = os.getenv('DISCORD_CHANNEL_ID')
    
    handler = DiscordHandler(token, channel_id)
    
    try:
        await handler.connect()
        print("Connected to Discord")
        
        # Fetch messages
        print("\nFetching last 50 messages...")
        messages = await handler.fetch_channel_messages(limit=50)
        print(f"✓ Fetched {len(messages)} messages")
        
        # Filter Twitter messages
        twitter_messages = handler.filter_twitter_messages(messages)
        print(f"✓ Found {len(twitter_messages)} messages with Twitter/X links")
        
        if twitter_messages:
            print("\nTwitter posts found:")
            for i, msg in enumerate(twitter_messages[:5], 1):
                link = handler.extract_twitter_link(msg.content)
                print(f"\n  Post {i}:")
                print(f"    Author: {msg.author.name}")
                print(f"    Date: {msg.created_at}")
                print(f"    Link: {link}")
                
        else:
            print("  No Twitter/X links found in recent messages")
            print("\n  Showing message content patterns instead:")
            for i, msg in enumerate(messages[:5], 1):
                print(f"\n  Message {i}:")
                print(f"    Has @mention: {'@' in msg.content}")
                print(f"    Content start: {msg.content[:50]}...")
                
    except Exception as e:
        print(f"❌ Failed during filtering: {e}")
        return False
        
    finally:
        await handler.disconnect()
        
    return True


async def test_format_post_data():
    """Test formatting Discord messages to TwitterPost objects."""
    print("\n=== Testing Post Data Formatting ===")
    
    load_dotenv()
    token = os.getenv('DISCORD_TOKEN')
    channel_id = os.getenv('DISCORD_CHANNEL_ID')
    
    handler = DiscordHandler(token, channel_id)
    
    try:
        await handler.connect()
        print("Connected to Discord")
        
        # Fetch and format posts
        print("\nFetching and formatting posts...")
        posts = await handler.fetch_twitter_posts_with_retry(limit=20)
        print(f"✓ Formatted {len(posts)} Twitter posts")
        
        if posts:
            print("\nFormatted posts:")
            for i, post in enumerate(posts[:3], 1):
                print(f"\n  Post {i}:")
                print(f"    Date: {post.date} {post.time}")
                print(f"    Author: {post.author}")
                print(f"    Link: {post.post_link}")
                print(f"    Content: {post.content[:100]}...")
                print(f"    Author Profile: {post.author_link}")
                
            # Export to CSV for inspection
            export_posts_to_csv(posts, "recent_posts_sample.csv")
        else:
            print("  No Twitter posts to format")
            
    except Exception as e:
        print(f"❌ Failed during formatting: {e}")
        return False
        
    finally:
        await handler.disconnect()
        
    return True


async def test_get_today_posts():
    """Test fetching today's posts."""
    print("\n=== Testing Today's Posts Fetching ===")
    
    load_dotenv()
    token = os.getenv('DISCORD_TOKEN')
    channel_id = os.getenv('DISCORD_CHANNEL_ID')
    
    handler = DiscordHandler(token, channel_id)
    
    try:
        await handler.connect()
        print("Connected to Discord")
        
        # Fetch today's posts
        print(f"\nFetching posts from today ({datetime.now().strftime('%Y-%m-%d')})...")
        posts = await handler.get_today_posts()
        print(f"✓ Found {len(posts)} Twitter posts from today")
        
        if posts:
            print("\nToday's posts:")
            for i, post in enumerate(posts, 1):
                print(f"\n  Post {i}:")
                print(f"    Time: {post.time}")
                print(f"    Author: {post.author}")
                print(f"    Link: {post.post_link}")
                
            # Export today's posts to CSV
            filename = f"today_posts_{datetime.now().strftime('%Y%m%d')}.csv"
            export_posts_to_csv(posts, filename)
        else:
            print("  No Twitter posts found from today")
            print("  (This is normal if no Twitter links were shared today)")
            
    except Exception as e:
        print(f"❌ Failed to fetch today's posts: {e}")
        return False
        
    finally:
        await handler.disconnect()
        
    return True


async def test_date_range_posts():
    """Test fetching posts from a date range."""
    print("\n=== Testing Date Range Posts Fetching ===")
    
    load_dotenv()
    token = os.getenv('DISCORD_TOKEN')
    channel_id = os.getenv('DISCORD_CHANNEL_ID')
    
    handler = DiscordHandler(token, channel_id)
    
    try:
        await handler.connect()
        print("Connected to Discord")
        
        # Fetch posts from last 7 days
        end_date = datetime.now()
        start_date = end_date - timedelta(days=7)
        
        print(f"\nFetching posts from {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}...")
        posts = await handler.get_posts_between_dates(start_date, end_date)
        print(f"✓ Found {len(posts)} Twitter posts in date range")
        
        if posts:
            # Group posts by date
            posts_by_date = {}
            for post in posts:
                if post.date not in posts_by_date:
                    posts_by_date[post.date] = []
                posts_by_date[post.date].append(post)
                
            print("\nPosts by date:")
            for date in sorted(posts_by_date.keys(), reverse=True):
                print(f"\n  {date}: {len(posts_by_date[date])} posts")
                for post in posts_by_date[date][:2]:  # Show first 2 posts per day
                    print(f"    - {post.time} by {post.author}")
                    
            # Export weekly posts to CSV
            filename = f"weekly_posts_{start_date.strftime('%Y%m%d')}_{end_date.strftime('%Y%m%d')}.csv"
            export_posts_to_csv(posts, filename)
        else:
            print("  No Twitter posts found in date range")
            
    except Exception as e:
        print(f"❌ Failed to fetch date range posts: {e}")
        return False
        
    finally:
        await handler.disconnect()
        
    return True


async def test_retry_mechanism():
    """Test the retry mechanism with simulated failures."""
    print("\n=== Testing Retry Mechanism ===")
    
    load_dotenv()
    token = os.getenv('DISCORD_TOKEN')
    channel_id = os.getenv('DISCORD_CHANNEL_ID')
    
    handler = DiscordHandler(token, channel_id)
    
    # We'll test the retry logic by using a very high limit that might trigger rate limiting
    try:
        await handler.connect()
        print("Connected to Discord")
        
        print("\nTesting retry with exponential backoff...")
        posts = await handler.fetch_twitter_posts_with_retry(
            limit=1000,  # High limit to potentially trigger rate limit
            max_retries=2
        )
        print(f"✓ Successfully fetched {len(posts)} posts with retry logic")
        
    except Exception as e:
        print(f"❌ Retry mechanism test failed: {e}")
        return False
        
    finally:
        await handler.disconnect()
        
    return True


async def export_all_posts():
    """Export all available posts to a comprehensive CSV file."""
    print("\n=== Exporting All Available Posts ===")
    
    load_dotenv()
    token = os.getenv('DISCORD_TOKEN')
    channel_id = os.getenv('DISCORD_CHANNEL_ID')
    
    handler = DiscordHandler(token, channel_id)
    
    try:
        await handler.connect()
        print("Connected to Discord")
        
        # Fetch a large batch of posts
        print("\nFetching all available posts (up to 500)...")
        posts = await handler.fetch_twitter_posts_with_retry(limit=500)
        print(f"✓ Fetched {len(posts)} Twitter posts")
        
        if posts:
            # Sort posts by date and time
            posts.sort(key=lambda p: (p.date, p.time), reverse=True)
            
            # Export all posts
            filename = f"all_discord_posts_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
            export_posts_to_csv(posts, filename)
            
            # Create summary statistics
            print("\nPost Statistics:")
            
            # Group by date
            posts_by_date = {}
            for post in posts:
                if post.date not in posts_by_date:
                    posts_by_date[post.date] = []
                posts_by_date[post.date].append(post)
            
            print(f"  Date range: {min(posts_by_date.keys())} to {max(posts_by_date.keys())}")
            print(f"  Total days with posts: {len(posts_by_date)}")
            print(f"  Average posts per day: {len(posts) / len(posts_by_date):.1f}")
            
            # Group by author
            posts_by_author = {}
            for post in posts:
                if post.author not in posts_by_author:
                    posts_by_author[post.author] = 0
                posts_by_author[post.author] += 1
            
            print(f"\n  Top 5 Authors:")
            for author, count in sorted(posts_by_author.items(), key=lambda x: x[1], reverse=True)[:5]:
                print(f"    - {author}: {count} posts")
                
        else:
            print("  No posts to export")
            
    except Exception as e:
        print(f"❌ Failed to export posts: {e}")
        return False
        
    finally:
        await handler.disconnect()
        
    return True


async def run_all_tests():
    """Run all integration tests."""
    print("=" * 60)
    print("Discord Handler Integration Tests")
    print("=" * 60)
    
    tests = [
        ("Connection Test", test_connection),
        ("Message Fetching", test_fetch_messages),
        ("Twitter Post Filtering", test_filter_twitter_posts),
        ("Post Data Formatting", test_format_post_data),
        ("Today's Posts", test_get_today_posts),
        ("Date Range Posts", test_date_range_posts),
        ("Retry Mechanism", test_retry_mechanism),
        ("Export All Posts", export_all_posts),
    ]
    
    results = []
    
    for test_name, test_func in tests:
        print(f"\n{'=' * 60}")
        print(f"Running: {test_name}")
        print("=" * 60)
        
        try:
            success = await test_func()
            results.append((test_name, success))
        except Exception as e:
            print(f"❌ Test crashed: {e}")
            results.append((test_name, False))
            
        # Small delay between tests to avoid rate limiting
        await asyncio.sleep(1)
        
    # Print summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    
    for test_name, success in results:
        status = "✓ PASSED" if success else "❌ FAILED"
        print(f"{status}: {test_name}")
        
    passed = sum(1 for _, success in results if success)
    total = len(results)
    print(f"\nTotal: {passed}/{total} tests passed")
    
    # List generated CSV files
    print("\n" + "=" * 60)
    print("GENERATED CSV FILES")
    print("=" * 60)
    
    csv_files = [f for f in os.listdir('.') if f.endswith('.csv')]
    if csv_files:
        print("The following CSV files were generated for inspection:")
        for csv_file in sorted(csv_files):
            file_size = os.path.getsize(csv_file)
            print(f"  - {csv_file} ({file_size:,} bytes)")
    else:
        print("No CSV files were generated")
    
    return passed == total


if __name__ == "__main__":
    import logging
    
    # Set up logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Run tests
    success = asyncio.run(run_all_tests())
    
    # Exit with appropriate code
    sys.exit(0 if success else 1)