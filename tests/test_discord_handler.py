"""Unit tests for discord_handler module."""

import unittest
import re
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from datetime import datetime, timedelta
import asyncio

from modules.discord_handler import DiscordHandler, TwitterPost


class TestDiscordHandler(unittest.TestCase):
    """Test cases for DiscordHandler class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.test_token = "test_discord_token"
        self.test_channel_id = "123456789"
        self.handler = DiscordHandler(self.test_token, self.test_channel_id)
        
    def test_initialization(self):
        """Test DiscordHandler initialization."""
        self.assertEqual(self.handler.token, self.test_token)
        self.assertEqual(self.handler.channel_id, 123456789)
        self.assertIsNone(self.handler.bot)
        self.assertFalse(self.handler._ready)
        
    def test_extract_twitter_link(self):
        """Test extraction of Twitter/X links from message content."""
        test_cases = [
            # Standard Twitter/X links
            ("Check this out: https://twitter.com/user/status/123", 
             "https://twitter.com/user/status/123"),
            ("New post on https://x.com/user/status/456 today!", 
             "https://x.com/user/status/456"),
            # Real Discord message format from screenshots
            ("🚀 New project alpha alert: @DV_aix (263 followers, account created 1 month ago)\n\nDescription: \"exploring\"\n\nVisit http://web3alerts.app/ for more alpha :)",
             None),  # No Twitter link in this message
            ("New project:@sugardotmoney\n(follower 356)\nBio:The first positive-sum launchpad on Solana 🍩 Save SOL. Share rewards. Launch better.",
             None),  # No Twitter link in this message
            # Embedded Twitter mentions (not full URLs)
            ("Check out @Web3Alerts for updates", None),
            ("Multiple links https://twitter.com/a/1 and https://x.com/b/2", 
             "https://twitter.com/a/1"),
        ]
        
        for content, expected in test_cases:
            result = self.handler.extract_twitter_link(content)
            self.assertEqual(result, expected, f"Failed for content: {content[:50]}...")
            
    def test_filter_twitter_messages(self):
        """Test filtering messages containing Twitter/X links."""
        mock_messages = []
        
        # Create mock messages with and without Twitter links
        msg1 = Mock()
        msg1.content = "Check out https://twitter.com/user/status/123"
        mock_messages.append(msg1)
        
        msg2 = Mock()
        msg2.content = "Just a regular message"
        mock_messages.append(msg2)
        
        msg3 = Mock()
        msg3.content = "Another link: https://x.com/user/status/456"
        mock_messages.append(msg3)
        
        # Real Discord message format (no Twitter link, just mentions)
        msg4 = Mock()
        msg4.content = "🚀 New project alpha alert: @DV_aix (263 followers)"
        mock_messages.append(msg4)
        
        # Message with embedded image/link
        msg5 = Mock()
        msg5.content = "New tweet from https://twitter.com/Web3Alerts/status/789"
        mock_messages.append(msg5)
        
        filtered = self.handler.filter_twitter_messages(mock_messages)
        
        self.assertEqual(len(filtered), 3)
        self.assertIn(msg1, filtered)
        self.assertIn(msg3, filtered)
        self.assertIn(msg5, filtered)
        self.assertNotIn(msg2, filtered)
        self.assertNotIn(msg4, filtered)
        
    def test_format_post_data(self):
        """Test formatting Discord message to TwitterPost."""
        mock_message = Mock()
        mock_message.created_at = datetime(2024, 1, 15, 14, 30, 0)
        mock_message.content = "Check this out: https://twitter.com/user/status/123 #awesome"
        mock_message.author.name = "TestUser"
        mock_message.author.id = 987654321
        
        result = self.handler.format_post_data(mock_message)
        
        self.assertIsInstance(result, TwitterPost)
        self.assertEqual(result.date, "2024-01-15")
        self.assertEqual(result.time, "14:30")
        self.assertEqual(result.content, mock_message.content)
        self.assertEqual(result.post_link, "https://twitter.com/user/status/123")
        self.assertEqual(result.author, "TestUser")
        self.assertEqual(result.author_link, "https://discord.com/users/987654321")
        
    def test_format_post_data_long_content(self):
        """Test that long content is truncated to 500 characters."""
        mock_message = Mock()
        mock_message.created_at = datetime(2024, 1, 15, 14, 30, 0)
        mock_message.content = "x" * 600  # Content longer than 500 chars
        mock_message.author.name = "TestUser"
        mock_message.author.id = 987654321
        
        result = self.handler.format_post_data(mock_message)
        
        self.assertEqual(len(result.content), 500)
        
    def test_format_post_data_no_twitter_link(self):
        """Test formatting message without Twitter link."""
        mock_message = Mock()
        mock_message.created_at = datetime(2024, 1, 15, 14, 30, 0)
        mock_message.content = "Just a regular message"
        mock_message.author.name = "TestUser"
        mock_message.author.id = 987654321
        
        result = self.handler.format_post_data(mock_message)
        
        self.assertEqual(result.post_link, "")
        
    def test_format_post_data_real_discord_format(self):
        """Test formatting real Discord message format from screenshots."""
        # Test Web3 Alerts message format
        mock_message1 = Mock()
        mock_message1.created_at = datetime(2024, 1, 15, 14, 30, 0)
        mock_message1.content = "🚀 New project alpha alert: @DV_aix (263 followers, account created 1 month ago)\n\nDescription: \"exploring\"\n\nVisit http://web3alerts.app/ for more alpha :)"
        mock_message1.author.name = "Web3 Alerts"
        mock_message1.author.id = 123456789
        
        result1 = self.handler.format_post_data(mock_message1)
        
        self.assertEqual(result1.post_link, "")  # No Twitter link
        self.assertEqual(result1.author, "Web3 Alerts")
        self.assertIn("@DV_aix", result1.content)
        
        # Test ARES Alpha Labs message format
        mock_message2 = Mock()
        mock_message2.created_at = datetime(2024, 1, 15, 15, 45, 0)
        mock_message2.content = "New project:@sugardotmoney\n(follower 356)\nBio:The first positive-sum launchpad on Solana 🍩 Save SOL. Share rewards. Launch better."
        mock_message2.author.name = "ARES Alpha Labs"
        mock_message2.author.id = 987654321
        
        result2 = self.handler.format_post_data(mock_message2)
        
        self.assertEqual(result2.post_link, "")  # No Twitter link
        self.assertEqual(result2.author, "ARES Alpha Labs")
        self.assertIn("@sugardotmoney", result2.content)
        self.assertIn("Solana", result2.content)
        
    def test_extract_twitter_handles(self):
        """Test extraction of Twitter handles from Discord messages."""
        test_cases = [
            ("New project alpha alert: @DV_aix (263 followers)", ["@DV_aix"]),
            ("Check out @Web3Alerts and @AresLabs_xyz", ["@Web3Alerts", "@AresLabs_xyz"]),
            ("New project:@sugardotmoney", ["@sugardotmoney"]),
            ("No handles here", []),
        ]
        
        # This would be a potential enhancement to extract handles
        for content, expected_handles in test_cases:
            # Find all @mentions using regex
            handle_pattern = r'@[\w_]+'
            handles = re.findall(handle_pattern, content)
            for expected in expected_handles:
                self.assertIn(expected, handles)


class TestDiscordHandlerAsync(unittest.TestCase):
    """Test cases for async methods in DiscordHandler."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.test_token = "test_discord_token"
        self.test_channel_id = "123456789"
        self.handler = DiscordHandler(self.test_token, self.test_channel_id)
        
    @patch('modules.discord_handler.commands.Bot')
    def test_initialize_bot(self, mock_bot_class):
        """Test bot initialization."""
        mock_bot = Mock()
        mock_bot_class.return_value = mock_bot
        
        asyncio.run(self.handler.initialize_bot())
        
        mock_bot_class.assert_called_once()
        self.assertEqual(self.handler.bot, mock_bot)
        
    @patch('modules.discord_handler.commands.Bot')
    def test_connect_success(self, mock_bot_class):
        """Test successful connection to Discord."""
        mock_bot = AsyncMock()
        mock_bot_class.return_value = mock_bot
        
        async def run_test():
            await self.handler.initialize_bot()
            # Simulate bot ready
            self.handler._ready = True
            await self.handler.connect()
            
        asyncio.run(run_test())
        
        self.assertTrue(self.handler._ready)
        
    @patch('modules.discord_handler.commands.Bot')
    def test_disconnect(self, mock_bot_class):
        """Test disconnection from Discord."""
        mock_bot = AsyncMock()
        mock_bot_class.return_value = mock_bot
        self.handler.bot = mock_bot
        self.handler._ready = True
        
        asyncio.run(self.handler.disconnect())
        
        mock_bot.close.assert_called_once()
        self.assertFalse(self.handler._ready)
        
    def test_fetch_channel_messages_not_ready(self):
        """Test fetching messages when bot is not ready."""
        with self.assertRaises(RuntimeError) as context:
            asyncio.run(self.handler.fetch_channel_messages())
            
        self.assertIn("Bot is not connected", str(context.exception))
        
    @patch('modules.discord_handler.commands.Bot')
    def test_fetch_channel_messages_success(self, mock_bot_class):
        """Test successful message fetching."""
        mock_bot = Mock()
        mock_channel = AsyncMock()
        mock_bot.get_channel.return_value = mock_channel
        
        # Create mock messages
        mock_messages = [Mock() for _ in range(5)]
        
        async def mock_history(**kwargs):
            for msg in mock_messages:
                yield msg
                
        mock_channel.history = mock_history
        
        self.handler.bot = mock_bot
        self.handler._ready = True
        
        result = asyncio.run(self.handler.fetch_channel_messages(limit=5))
        
        self.assertEqual(len(result), 5)
        mock_bot.get_channel.assert_called_once_with(123456789)
        
    def test_fetch_twitter_posts_with_retry(self):
        """Test retry logic with exponential backoff."""
        import discord
        self.handler._ready = True
        
        # Mock the fetch_channel_messages to fail twice then succeed
        call_count = 0
        
        async def mock_fetch(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count <= 2:
                raise discord.HTTPException(Mock(), "Rate limited")
            return []
            
        self.handler.fetch_channel_messages = mock_fetch
        self.handler.filter_twitter_messages = Mock(return_value=[])
        
        with patch('asyncio.sleep', new_callable=AsyncMock):
            result = asyncio.run(
                self.handler.fetch_twitter_posts_with_retry(max_retries=3)
            )
            
        self.assertEqual(call_count, 3)
        self.assertEqual(result, [])
        
    def test_get_today_posts(self):
        """Test fetching today's posts."""
        mock_posts = [
            TwitterPost(
                date=datetime.now().strftime('%Y-%m-%d'),
                time="10:00",
                content="Test post",
                post_link="https://twitter.com/test",
                author="TestUser",
                author_link="https://discord.com/users/123"
            )
        ]
        
        self.handler.fetch_twitter_posts_with_retry = AsyncMock(
            return_value=mock_posts
        )
        
        result = asyncio.run(self.handler.get_today_posts())
        
        self.assertEqual(result, mock_posts)
        self.handler.fetch_twitter_posts_with_retry.assert_called_once()
        
    def test_get_posts_between_dates(self):
        """Test fetching posts between specified dates."""
        start_date = datetime(2024, 1, 1)
        end_date = datetime(2024, 1, 31)
        
        mock_posts = [
            TwitterPost(
                date="2024-01-15",
                time="10:00",
                content="Test post 1",
                post_link="https://twitter.com/test1",
                author="User1",
                author_link="https://discord.com/users/1"
            ),
            TwitterPost(
                date="2024-02-01",  # Outside date range
                time="11:00",
                content="Test post 2",
                post_link="https://twitter.com/test2",
                author="User2",
                author_link="https://discord.com/users/2"
            ),
            TwitterPost(
                date="2024-01-20",
                time="12:00",
                content="Test post 3",
                post_link="https://twitter.com/test3",
                author="User3",
                author_link="https://discord.com/users/3"
            ),
        ]
        
        self.handler.fetch_twitter_posts_with_retry = AsyncMock(
            return_value=mock_posts
        )
        
        result = asyncio.run(
            self.handler.get_posts_between_dates(start_date, end_date)
        )
        
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0].date, "2024-01-15")
        self.assertEqual(result[1].date, "2024-01-20")


if __name__ == '__main__':
    unittest.main()