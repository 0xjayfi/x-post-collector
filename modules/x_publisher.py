"""
X/Twitter Publishing Module

Publishes AI-generated daily summaries to X (Twitter) using either
X API v2 directly or Typefully API for scheduled publishing.
"""

import logging
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Optional, List
import requests

logger = logging.getLogger(__name__)


@dataclass
class PublishResult:
    """Result of a publishing attempt"""
    success: bool
    url: Optional[str] = None
    post_id: Optional[str] = None
    error_msg: Optional[str] = None


class PublishRateLimiter:
    """Handle API rate limits for publishing"""
    
    def __init__(self, posts_per_day: int = 50, posts_per_15min: int = 5):
        """
        Initialize rate limiter
        
        Args:
            posts_per_day: Daily post limit
            posts_per_15min: 15-minute window limit
        """
        self.daily_limit = posts_per_day
        self.window_limit = posts_per_15min
        self.daily_posts = 0
        self.window_posts = []
        self.last_reset = datetime.now()
        logger.info(f"Rate limiter initialized: {posts_per_day}/day, {posts_per_15min}/15min")
    
    def can_publish(self) -> bool:
        """Check if we can publish now"""
        now = datetime.now()
        
        # Reset daily counter
        if now.date() > self.last_reset.date():
            self.daily_posts = 0
            self.last_reset = now
            logger.debug("Daily rate limit counter reset")
        
        # Check daily limit
        if self.daily_posts >= self.daily_limit:
            logger.warning(f"Daily rate limit reached: {self.daily_posts}/{self.daily_limit}")
            return False
        
        # Check 15-minute window
        window_start = now - timedelta(minutes=15)
        self.window_posts = [t for t in self.window_posts if t > window_start]
        
        if len(self.window_posts) >= self.window_limit:
            logger.warning(f"15-min rate limit reached: {len(self.window_posts)}/{self.window_limit}")
            return False
        
        return True
    
    def record_post(self):
        """Record a successful post"""
        self.daily_posts += 1
        self.window_posts.append(datetime.now())
        logger.debug(f"Recorded post - Daily: {self.daily_posts}, Window: {len(self.window_posts)}")
    
    def wait_if_needed(self) -> float:
        """
        Calculate wait time if rate limited
        
        Returns:
            Seconds to wait (0 if no wait needed)
        """
        if self.can_publish():
            return 0
        
        # Calculate wait time until oldest post in window expires
        if self.window_posts:
            oldest = min(self.window_posts)
            window_end = oldest + timedelta(minutes=15)
            wait_seconds = (window_end - datetime.now()).total_seconds()
            return max(0, wait_seconds + 1)  # Add 1 second buffer
        
        # If daily limit reached, wait until tomorrow
        tomorrow = datetime.combine(
            datetime.now().date() + timedelta(days=1),
            datetime.min.time()
        )
        return (tomorrow - datetime.now()).total_seconds()


class XPublisher(ABC):
    """Abstract base class for X/Twitter publishers"""
    
    def __init__(self):
        self.rate_limiter = PublishRateLimiter()
    
    @abstractmethod
    def authenticate(self) -> bool:
        """Authenticate with the publishing service"""
        pass
    
    @abstractmethod
    def publish(self, content: str) -> PublishResult:
        """Publish content to X/Twitter"""
        pass
    
    def validate_content(self, content: str) -> bool:
        """
        Validate content before publishing
        
        Args:
            content: Content to validate
            
        Returns:
            True if content is valid
        """
        if not content or not content.strip():
            logger.error("Content is empty")
            return False
        
        # Check for very long content (X has limits)
        if len(content) > 10000:  # Safety limit
            logger.error(f"Content too long: {len(content)} characters")
            return False
        
        return True
    
    def format_for_publishing(self, content: str, add_hashtags: bool = True) -> str:
        """
        Format content for X/Twitter
        
        Args:
            content: Raw content to format
            add_hashtags: Whether to add hashtags
            
        Returns:
            Formatted content
        """
        # Clean up content
        content = content.strip()
        
        # Add hashtags if requested
        if add_hashtags:
            hashtags = "\n\n#CryptoProjects #Web3 #DeFi #NFTs #Blockchain"
            
            # Check if content + hashtags fits in single tweet
            if len(content) + len(hashtags) <= 280:
                return content + hashtags
            
            # Try with fewer hashtags
            short_hashtags = "\n\n#Crypto #Web3"
            if len(content) + len(short_hashtags) <= 280:
                return content + short_hashtags
        
        return content


class TwitterAPIPublisher(XPublisher):
    """Publisher using X API v2 directly"""
    
    def __init__(self, api_key: str, api_secret: str, 
                 access_token: str, access_token_secret: str):
        """
        Initialize Twitter API publisher
        
        Args:
            api_key: X API key
            api_secret: X API secret
            access_token: Access token
            access_token_secret: Access token secret
        """
        super().__init__()
        self.api_key = api_key
        self.api_secret = api_secret
        self.access_token = access_token
        self.access_token_secret = access_token_secret
        self.client = None
        logger.info("Initialized TwitterAPIPublisher")
    
    def authenticate(self) -> bool:
        """Authenticate with X API v2"""
        try:
            # Import tweepy only when needed
            import tweepy
            
            self.client = tweepy.Client(
                consumer_key=self.api_key,
                consumer_secret=self.api_secret,
                access_token=self.access_token,
                access_token_secret=self.access_token_secret
            )
            
            # Test authentication
            me = self.client.get_me()
            if me and me.data:
                logger.info(f"Authenticated as @{me.data.username}")
                return True
            
            logger.error("Failed to authenticate - no user data")
            return False
            
        except ImportError:
            logger.error("tweepy not installed. Run: pip install tweepy")
            return False
        except Exception as e:
            logger.error(f"Authentication failed: {e}")
            return False
    
    def _split_into_tweets(self, content: str, max_length: int = 280) -> List[str]:
        """
        Split long content into tweet-sized chunks
        
        Args:
            content: Content to split
            max_length: Maximum length per tweet
            
        Returns:
            List of tweet-sized strings
        """
        if len(content) <= max_length:
            return [content]
        
        tweets = []
        lines = content.split('\n')
        current_tweet = ""
        
        for line in lines:
            # If single line is too long, split by sentences
            if len(line) > max_length - 10:  # Leave room for "..."
                sentences = line.split('. ')
                for sentence in sentences:
                    if len(current_tweet) + len(sentence) + 2 <= max_length - 10:
                        current_tweet += sentence + ". "
                    else:
                        if current_tweet:
                            tweets.append(current_tweet.strip() + "...")
                        current_tweet = "..." + sentence + ". "
            else:
                # Try to add the line to current tweet
                test_tweet = current_tweet + "\n" + line if current_tweet else line
                
                if len(test_tweet) <= max_length - 10:
                    current_tweet = test_tweet
                else:
                    if current_tweet:
                        tweets.append(current_tweet + "...")
                    current_tweet = "..." + line
        
        # Add remaining content
        if current_tweet:
            tweets.append(current_tweet)
        
        # Add thread numbering
        if len(tweets) > 1:
            for i, tweet in enumerate(tweets, 1):
                prefix = f"({i}/{len(tweets)}) "
                # Adjust tweet length for prefix
                max_with_prefix = max_length - len(prefix)
                if len(tweet) > max_with_prefix:
                    tweet = tweet[:max_with_prefix-3] + "..."
                tweets[i-1] = prefix + tweet
        
        return tweets
    
    def publish(self, content: str) -> PublishResult:
        """
        Publish content as tweet(s)
        
        Args:
            content: Content to publish
            
        Returns:
            PublishResult object
        """
        # Validate content
        if not self.validate_content(content):
            return PublishResult(
                success=False,
                error_msg="Content validation failed"
            )
        
        # Check rate limits
        if not self.rate_limiter.can_publish():
            wait_time = self.rate_limiter.wait_if_needed()
            return PublishResult(
                success=False,
                error_msg=f"Rate limited. Wait {wait_time:.0f} seconds"
            )
        
        # Authenticate if needed
        if not self.client:
            if not self.authenticate():
                return PublishResult(
                    success=False,
                    error_msg="Authentication failed"
                )
        
        try:
            # Format content
            formatted_content = self.format_for_publishing(content)
            
            # Split into tweets if needed
            tweets = self._split_into_tweets(formatted_content)
            
            # Post first tweet
            response = self.client.create_tweet(text=tweets[0])
            
            if not response or not response.data:
                return PublishResult(
                    success=False,
                    error_msg="Failed to create tweet"
                )
            
            tweet_id = response.data['id']
            
            # Get authenticated user for URL
            me = self.client.get_me()
            username = me.data.username if me and me.data else "user"
            tweet_url = f"https://twitter.com/{username}/status/{tweet_id}"
            
            # Thread remaining tweets if any
            for tweet_text in tweets[1:]:
                time.sleep(1)  # Small delay between tweets
                response = self.client.create_tweet(
                    text=tweet_text,
                    in_reply_to_tweet_id=tweet_id
                )
                if response and response.data:
                    tweet_id = response.data['id']
            
            # Record successful post
            self.rate_limiter.record_post()
            
            logger.info(f"Published {len(tweets)} tweet(s): {tweet_url}")
            
            return PublishResult(
                success=True,
                url=tweet_url,
                post_id=str(tweet_id)
            )
            
        except Exception as e:
            error_msg = str(e).lower()
            
            # Parse specific errors
            if "rate limit" in error_msg or "429" in error_msg:
                return PublishResult(
                    success=False,
                    error_msg="X API rate limit exceeded"
                )
            elif "unauthorized" in error_msg or "401" in error_msg:
                return PublishResult(
                    success=False,
                    error_msg="Authentication failed - check credentials"
                )
            elif "forbidden" in error_msg or "403" in error_msg:
                return PublishResult(
                    success=False,
                    error_msg="Forbidden - check app permissions"
                )
            else:
                logger.error(f"Publishing failed: {e}")
                return PublishResult(
                    success=False,
                    error_msg=f"Publishing failed: {str(e)}"
                )


class TypefullyPublisher(XPublisher):
    """Publisher using Typefully API for scheduled publishing"""
    
    def __init__(self, api_key: str, schedule: str = "next-free-slot"):
        """
        Initialize Typefully publisher
        
        Args:
            api_key: Typefully API key
            schedule: Schedule option (e.g., "next-free-slot" or ISO datetime)
        """
        super().__init__()
        self.api_key = api_key
        self.schedule = schedule
        self.base_url = "https://api.typefully.com/v1"
        self.headers = {"X-API-KEY": f"Bearer {api_key}"}
        logger.info(f"Initialized TypefullyPublisher with schedule: {schedule}")
    
    def authenticate(self) -> bool:
        """Test Typefully API authentication"""
        try:
            # Test API with a simple request
            response = requests.get(
                f"{self.base_url}/profiles/",
                headers=self.headers,
                timeout=10
            )
            
            if response.status_code == 200:
                logger.info("Typefully authentication successful")
                return True
            elif response.status_code == 401:
                logger.error("Typefully authentication failed - invalid API key")
                return False
            else:
                logger.error(f"Typefully API error: {response.status_code}")
                return False
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to connect to Typefully: {e}")
            return False
    
    def publish(self, content: str) -> PublishResult:
        """
        Create a draft in Typefully
        
        Args:
            content: Content to publish
            
        Returns:
            PublishResult object
        """
        # Validate content
        if not self.validate_content(content):
            return PublishResult(
                success=False,
                error_msg="Content validation failed"
            )
        
        # Check rate limits (still apply for safety)
        if not self.rate_limiter.can_publish():
            wait_time = self.rate_limiter.wait_if_needed()
            logger.warning(f"Rate limited. Waiting {wait_time:.0f} seconds")
            # For Typefully, we can still create draft
            # but log the warning
        
        try:
            # Format content
            formatted_content = self.format_for_publishing(content)
            
            # Prepare payload
            payload = {
                "content": formatted_content,
                "schedule-date": self.schedule
            }
            
            # Make API request
            response = requests.post(
                f"{self.base_url}/drafts/",
                headers=self.headers,
                json=payload,
                timeout=30
            )
            
            # Check response
            if response.status_code == 200 or response.status_code == 201:
                data = response.json()
                draft_id = data.get('id', 'unknown')
                
                # Construct draft URL
                draft_url = f"https://typefully.com/drafts/{draft_id}"
                
                # Record post (even though it's scheduled)
                self.rate_limiter.record_post()
                
                logger.info(f"Created Typefully draft: {draft_url}")
                
                return PublishResult(
                    success=True,
                    url=draft_url,
                    post_id=str(draft_id)
                )
            else:
                error_msg = f"Typefully API error: {response.status_code}"
                
                try:
                    error_data = response.json()
                    if 'error' in error_data:
                        error_msg = f"Typefully error: {error_data['error']}"
                    elif 'message' in error_data:
                        error_msg = f"Typefully error: {error_data['message']}"
                except:
                    pass
                
                logger.error(error_msg)
                
                return PublishResult(
                    success=False,
                    error_msg=error_msg
                )
                
        except requests.exceptions.Timeout:
            return PublishResult(
                success=False,
                error_msg="Typefully API timeout"
            )
        except requests.exceptions.RequestException as e:
            logger.error(f"Typefully request failed: {e}")
            return PublishResult(
                success=False,
                error_msg=f"Request failed: {str(e)}"
            )
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            return PublishResult(
                success=False,
                error_msg=f"Unexpected error: {str(e)}"
            )


def create_publisher(publisher_type: str, **kwargs) -> Optional[XPublisher]:
    """
    Factory function to create appropriate publisher
    
    Args:
        publisher_type: Type of publisher ('twitter' or 'typefully')
        **kwargs: Configuration parameters for the publisher
        
    Returns:
        Publisher instance or None if creation fails
    """
    try:
        if publisher_type.lower() == 'twitter':
            required = ['api_key', 'api_secret', 'access_token', 'access_token_secret']
            
            if not all(k in kwargs for k in required):
                logger.error(f"Missing required Twitter API credentials")
                return None
            
            publisher = TwitterAPIPublisher(
                api_key=kwargs['api_key'],
                api_secret=kwargs['api_secret'],
                access_token=kwargs['access_token'],
                access_token_secret=kwargs['access_token_secret']
            )
            
            if publisher.authenticate():
                return publisher
            
        elif publisher_type.lower() == 'typefully':
            if 'api_key' not in kwargs:
                logger.error("Missing Typefully API key")
                return None
            
            publisher = TypefullyPublisher(
                api_key=kwargs['api_key'],
                schedule=kwargs.get('schedule', 'next-free-slot')
            )
            
            if publisher.authenticate():
                return publisher
        else:
            logger.error(f"Unknown publisher type: {publisher_type}")
        
    except Exception as e:
        logger.error(f"Failed to create publisher: {e}")
    
    return None