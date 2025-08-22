"""Discord handler module for fetching Twitter/X posts from Discord channels."""

import re
import asyncio
import logging
from datetime import datetime, timedelta
from typing import List, Optional
from dataclasses import dataclass

import discord
from discord.ext import commands

logger = logging.getLogger(__name__)


@dataclass
class TwitterPost:
    """Data structure for Twitter/X post information."""
    date: str  # YYYY-MM-DD format
    time: str  # HH:MM format
    content: str
    post_link: str
    author: str
    author_link: str


class DiscordHandler:
    """Handler for Discord bot operations and message fetching."""
    
    TWITTER_URL_PATTERN = re.compile(
        r'https?://(twitter\.com|x\.com)/[^\s]+',
        re.IGNORECASE
    )
    
    def __init__(self, token: str, channel_id: str):
        """Initialize Discord handler with bot token and target channel.
        
        Args:
            token: Discord bot token
            channel_id: Target Discord channel ID to monitor
        """
        self.token = token
        self.channel_id = int(channel_id)
        self.bot = None
        self._ready = False
        self._bot_task = None
        
    async def initialize_bot(self) -> None:
        """Initialize and start the Discord bot."""
        intents = discord.Intents.default()
        intents.message_content = True
        intents.messages = True
        
        self.bot = commands.Bot(command_prefix='!', intents=intents)
        
        @self.bot.event
        async def on_ready():
            self._ready = True
            logger.info(f"Discord bot connected as {self.bot.user}")
            
    async def connect(self) -> None:
        """Connect to Discord and wait for bot to be ready."""
        logger.debug("Starting Discord connection...")
        if not self.bot:
            logger.debug("Initializing bot...")
            await self.initialize_bot()
        
        # Start the bot in the background
        logger.debug("Starting bot task...")
        self._bot_task = asyncio.create_task(self.bot.start(self.token))
        
        # Wait for bot to be ready
        logger.debug("Waiting for bot to be ready...")
        retry_count = 0
        while not self._ready and retry_count < 30:
            await asyncio.sleep(1)
            retry_count += 1
            if retry_count % 5 == 0:
                logger.debug(f"Still waiting for bot... ({retry_count}s)")
            
        if not self._ready:
            raise TimeoutError("Failed to connect to Discord within 30 seconds")
        
        logger.debug("Discord connection successful")
            
    async def disconnect(self) -> None:
        """Disconnect from Discord."""
        if self.bot:
            await self.bot.close()
            self._ready = False
            
    async def fetch_channel_messages(
        self, 
        limit: int = 100,
        after: Optional[datetime] = None
    ) -> List[discord.Message]:
        """Fetch messages from the configured Discord channel.
        
        Args:
            limit: Maximum number of messages to fetch
            after: Only fetch messages after this datetime
            
        Returns:
            List of Discord messages
        """
        if not self._ready:
            raise RuntimeError("Bot is not connected. Call connect() first.")
            
        channel = self.bot.get_channel(self.channel_id)
        if not channel:
            raise ValueError(f"Channel with ID {self.channel_id} not found")
            
        messages = []
        async for message in channel.history(limit=limit, after=after):
            messages.append(message)
            
        logger.info(f"Fetched {len(messages)} messages from channel {self.channel_id}")
        return messages
        
    def filter_twitter_messages(self, messages: List[discord.Message]) -> List[discord.Message]:
        """Filter messages containing Twitter/X links.
        
        Args:
            messages: List of Discord messages to filter
            
        Returns:
            List of messages containing Twitter/X links
        """
        filtered_messages = []
        
        for message in messages:
            if self.TWITTER_URL_PATTERN.search(message.content):
                filtered_messages.append(message)
                
        logger.info(f"Filtered {len(filtered_messages)} messages with Twitter/X links")
        return filtered_messages
        
    def extract_twitter_link(self, content: str) -> Optional[str]:
        """Extract the first Twitter/X link from message content.
        
        Args:
            content: Message content to search
            
        Returns:
            Twitter/X URL if found, None otherwise
        """
        match = self.TWITTER_URL_PATTERN.search(content)
        return match.group(0) if match else None
        
    def clean_content(self, text: str) -> str:
        """Clean content by fixing Discord markdown issues while preserving structure.
        
        Args:
            text: Text to clean
            
        Returns:
            Cleaned text with fixed markdown and preserved paragraph structure
        """
        # Fix zero-width characters in Discord markdown links
        # Pattern: [@​username] -> [@username] (remove zero-width chars)
        text = text.replace('\u200b', '').replace('​', '')
        
        # Fix Discord markdown links that have zero-width spaces
        # This preserves the markdown format while removing invisible characters
        username_pattern = re.compile(r'\[@\s*([^\]]+)\]')
        text = username_pattern.sub(r'[@\1]', text)
        
        # Preserve paragraph structure - only clean up excessive spaces within lines
        lines = text.split('\n')
        cleaned_lines = []
        for line in lines:
            # Clean up multiple spaces within a line (but preserve single spaces)
            cleaned_line = re.sub(r'[ \t]+', ' ', line).strip()
            cleaned_lines.append(cleaned_line)
        
        # Join back with newlines, removing empty lines at start/end but preserving internal structure
        text = '\n'.join(cleaned_lines).strip()
        
        return text
    
    def format_post_data(self, message: discord.Message) -> TwitterPost:
        """Convert Discord message to TwitterPost data structure.
        
        Args:
            message: Discord message to format
            
        Returns:
            TwitterPost object with extracted data
        """
        created_at = message.created_at
        twitter_link = self.extract_twitter_link(message.content)
        
        # Extract content from embed if available (for TweetShift embeds)
        content = message.content[:1000]  # Default to message content (increased limit)
        
        # Check for Twitter embeds which contain the actual tweet content
        if message.embeds:
            for embed in message.embeds:
                # Look for Twitter/TweetShift embeds
                if embed.type == "rich" and embed.description:
                    # This is likely a Twitter embed with actual content
                    content = embed.description[:1000]  # Increased limit
                    break
                elif embed.url and twitter_link and embed.url == twitter_link:
                    # Found matching Twitter embed
                    if embed.description:
                        content = embed.description[:1000]  # Increased limit
                        break
        
        # If we still have just a link, try to extract Twitter handle from content
        if not twitter_link and message.embeds:
            for embed in message.embeds:
                if embed.url and self.TWITTER_URL_PATTERN.search(embed.url):
                    twitter_link = embed.url
                    break
        
        # Clean the content (fix Discord markdown while preserving structure)
        content = self.clean_content(content)
        
        return TwitterPost(
            date=created_at.strftime('%Y-%m-%d'),
            time=created_at.strftime('%H:%M'),
            content=content,
            post_link=twitter_link or "",
            author=message.author.name,
            author_link=f"https://discord.com/users/{message.author.id}"
        )
        
    async def fetch_twitter_posts_with_retry(
        self,
        limit: int = 100,
        after: Optional[datetime] = None,
        max_retries: int = 3
    ) -> List[TwitterPost]:
        """Fetch Twitter posts with exponential backoff retry logic.
        
        Args:
            limit: Maximum number of messages to fetch
            after: Only fetch messages after this datetime
            max_retries: Maximum number of retry attempts
            
        Returns:
            List of TwitterPost objects
        """
        retry_count = 0
        backoff_seconds = 1
        
        while retry_count <= max_retries:
            try:
                messages = await self.fetch_channel_messages(limit, after)
                twitter_messages = self.filter_twitter_messages(messages)
                
                twitter_posts = [
                    self.format_post_data(msg) 
                    for msg in twitter_messages
                ]
                
                return twitter_posts
                
            except discord.HTTPException as e:
                retry_count += 1
                
                if retry_count > max_retries:
                    logger.error(f"Max retries exceeded. Final error: {e}")
                    raise
                    
                logger.warning(
                    f"Discord API error (attempt {retry_count}/{max_retries}): {e}. "
                    f"Retrying in {backoff_seconds} seconds..."
                )
                
                await asyncio.sleep(backoff_seconds)
                backoff_seconds *= 2  # Exponential backoff
                
            except Exception as e:
                logger.error(f"Unexpected error fetching Twitter posts: {e}")
                raise
                
        return []
        
    async def get_today_posts(self) -> List[TwitterPost]:
        """Fetch Twitter posts from today.
        
        Returns:
            List of TwitterPost objects from today
        """
        today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        yesterday = today_start - timedelta(days=1)
        
        return await self.fetch_twitter_posts_with_retry(
            limit=200,  # Fetch more messages to ensure we get all from today
            after=yesterday
        )
        
    async def get_posts_between_dates(
        self,
        start_date: datetime,
        end_date: datetime
    ) -> List[TwitterPost]:
        """Fetch Twitter posts between specified dates.
        
        Args:
            start_date: Start date for fetching messages
            end_date: End date for fetching messages
            
        Returns:
            List of TwitterPost objects within date range
        """
        all_posts = await self.fetch_twitter_posts_with_retry(
            limit=None,  # Fetch all available
            after=start_date - timedelta(days=1)
        )
        
        # Filter posts within the date range
        filtered_posts = [
            post for post in all_posts
            if start_date.strftime('%Y-%m-%d') <= post.date <= end_date.strftime('%Y-%m-%d')
        ]
        
        return filtered_posts


async def main():
    """Example usage and testing function."""
    import os
    from dotenv import load_dotenv
    
    load_dotenv()
    
    token = os.getenv('DISCORD_TOKEN')
    channel_id = os.getenv('DISCORD_CHANNEL_ID')
    
    if not token or not channel_id:
        logger.error("Missing DISCORD_TOKEN or DISCORD_CHANNEL_ID in environment")
        return
        
    handler = DiscordHandler(token, channel_id)
    
    try:
        await handler.connect()
        
        # Fetch today's Twitter posts
        posts = await handler.get_today_posts()
        
        for post in posts:
            print(f"Date: {post.date} {post.time}")
            print(f"Author: {post.author}")
            print(f"Link: {post.post_link}")
            print(f"Content: {post.content[:100]}...")
            print("-" * 50)
            
    finally:
        await handler.disconnect()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())