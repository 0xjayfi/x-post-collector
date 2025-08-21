"""
Scheduler Module for Discord to Google Sheets Pipeline

This module orchestrates the complete data pipeline:
1. Discord data collection
2. Google Sheets upload
3. AI analysis (optional)
4. Publishing (optional)
5. Archiving
"""

import asyncio
import logging
import signal
import sys
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import schedule
import time

from modules.discord_handler import DiscordHandler, TwitterPost
from modules.sheets_handler import GoogleSheetsHandler
from modules.workflow_orchestrator import WorkflowOrchestrator

logger = logging.getLogger(__name__)


class DataCollectionOrchestrator:
    """Orchestrates Discord data collection and Google Sheets upload."""
    
    def __init__(
        self,
        discord_handler: DiscordHandler,
        sheets_handler: GoogleSheetsHandler,
        config: Dict[str, Any]
    ):
        """
        Initialize data collection orchestrator.
        
        Args:
            discord_handler: Discord handler instance
            sheets_handler: Google Sheets handler instance
            config: Configuration dictionary
        """
        self.discord = discord_handler
        self.sheets = sheets_handler
        self.config = config
    
    async def collect_discord_posts(self) -> List[TwitterPost]:
        """
        Collect Discord posts based on configured time window.
        
        Returns:
            List of TwitterPost objects
        """
        collection_mode = self.config.get('DISCORD_COLLECTION_MODE', 'daily')
        logger.info(f"Starting Discord data collection in '{collection_mode}' mode")
        
        # Determine time window
        after = None
        if collection_mode == 'daily':
            lookback_days = int(self.config.get('DISCORD_LOOKBACK_DAYS', 1))
            after = datetime.now() - timedelta(days=lookback_days)
            logger.info(f"Collecting posts from last {lookback_days} day(s)")
            
        elif collection_mode == 'hours':
            lookback_hours = int(self.config.get('DISCORD_LOOKBACK_HOURS', 24))
            after = datetime.now() - timedelta(hours=lookback_hours)
            logger.info(f"Collecting posts from last {lookback_hours} hour(s)")
            
        elif collection_mode == 'since_last':
            last_entry = self.sheets.get_last_entry_date()
            if last_entry:
                after = last_entry
                logger.info(f"Collecting posts since last entry: {after}")
            else:
                # Default to 1 day if no previous entries
                after = datetime.now() - timedelta(days=1)
                logger.info("No previous entries found, collecting from last 24 hours")
        
        # Fetch posts with configured limit
        limit = int(self.config.get('DISCORD_FETCH_LIMIT', 200))
        
        try:
            posts = await self.discord.fetch_twitter_posts_with_retry(
                limit=limit,
                after=after
            )
            logger.info(f"Collected {len(posts)} Twitter/X posts from Discord")
            return posts
            
        except Exception as e:
            logger.error(f"Failed to collect Discord posts: {e}")
            return []
    
    def filter_duplicates(self, posts: List[TwitterPost]) -> List[TwitterPost]:
        """
        Filter out posts that already exist in Google Sheets.
        
        Args:
            posts: List of posts to filter
            
        Returns:
            List of posts that don't exist in sheets
        """
        if self.config.get('DISCORD_SKIP_DUPLICATES', 'true').lower() != 'true':
            logger.info("Duplicate checking disabled")
            return posts
        
        try:
            # Get existing data from sheets
            existing_data = self.sheets.get_sheet_data()
            
            if len(existing_data) <= 1:  # Only headers or empty
                logger.info("No existing data in sheets")
                return posts
            
            # Create set of existing post links for fast lookup
            existing_links = set()
            link_col_idx = -1
            
            # Find post link column index
            headers = existing_data[0] if existing_data else []
            for idx, header in enumerate(headers):
                if 'Post Link' in header:
                    link_col_idx = idx
                    break
            
            if link_col_idx >= 0:
                for row in existing_data[1:]:  # Skip headers
                    if len(row) > link_col_idx and row[link_col_idx]:
                        existing_links.add(row[link_col_idx])
            
            # Filter out duplicates
            filtered_posts = []
            duplicates_count = 0
            
            for post in posts:
                if post.post_link and post.post_link not in existing_links:
                    filtered_posts.append(post)
                else:
                    duplicates_count += 1
            
            logger.info(f"Filtered out {duplicates_count} duplicate posts")
            return filtered_posts
            
        except Exception as e:
            logger.error(f"Error checking for duplicates: {e}")
            # Return all posts if duplicate checking fails
            return posts
    
    def push_to_sheets(self, posts: List[TwitterPost]) -> bool:
        """
        Push collected posts to Google Sheets.
        
        Args:
            posts: List of TwitterPost objects to upload
            
        Returns:
            True if successful, False otherwise
        """
        if not posts:
            logger.info("No posts to upload to sheets")
            return True
        
        try:
            # Check if headers exist
            existing_data = self.sheets.get_sheet_data()
            
            # Prepare headers if needed
            headers = ["Date", "Time", "Content", "Post Link", "Author", "Author Link"]
            
            if not existing_data:
                # Sheet is empty, add headers first
                logger.info("Adding headers to empty sheet")
                self.sheets.append_data([headers])
            
            # Convert posts to sheet rows
            rows = []
            for post in posts:
                row = [
                    post.date,
                    post.time,
                    post.content,
                    post.post_link,
                    post.author,
                    post.author_link
                ]
                rows.append(row)
            
            # Batch upload
            batch_size = int(self.config.get('SHEETS_BATCH_SIZE', 100))
            self.sheets.batch_append_data(rows, batch_size=batch_size)
            
            logger.info(f"Successfully uploaded {len(posts)} posts to Google Sheets")
            return True
            
        except Exception as e:
            logger.error(f"Failed to upload posts to sheets: {e}")
            return False
    
    async def run_data_collection(self) -> Dict:
        """
        Run the complete data collection workflow.
        
        Returns:
            Dictionary with collection results
        """
        results = {
            'success': False,
            'posts_collected': 0,
            'posts_uploaded': 0,
            'duplicates_skipped': 0,
            'errors': []
        }
        
        try:
            # Connect to Discord
            logger.info("Connecting to Discord...")
            await self.discord.connect()
            
            # Collect posts
            posts = await self.collect_discord_posts()
            results['posts_collected'] = len(posts)
            
            if posts:
                # Filter duplicates
                filtered_posts = self.filter_duplicates(posts)
                results['duplicates_skipped'] = len(posts) - len(filtered_posts)
                
                # Upload to sheets
                if filtered_posts:
                    if self.push_to_sheets(filtered_posts):
                        results['posts_uploaded'] = len(filtered_posts)
                        results['success'] = True
                    else:
                        results['errors'].append("Failed to upload posts to sheets")
                else:
                    logger.info("No new posts to upload after filtering duplicates")
                    results['success'] = True
            else:
                logger.info("No posts collected from Discord")
                results['success'] = True
                
        except Exception as e:
            logger.error(f"Data collection failed: {e}")
            results['errors'].append(str(e))
            
        finally:
            # Always disconnect from Discord
            try:
                await self.discord.disconnect()
                logger.info("Disconnected from Discord")
            except Exception as e:
                logger.warning(f"Error disconnecting from Discord: {e}")
        
        return results


class ScheduledTaskRunner:
    """Main scheduler that orchestrates the complete pipeline."""
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize scheduled task runner.
        
        Args:
            config: Configuration dictionary
        """
        self.config = config
        self.data_collector = None
        self.workflow_orchestrator = None
        self.timezone = self._setup_timezone()
        self._shutdown = False
        
        # Setup signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals gracefully."""
        logger.info("Received shutdown signal, finishing current task...")
        self._shutdown = True
    
    def _setup_timezone(self) -> Optional[Any]:
        """
        Setup timezone for scheduling.
        
        Returns:
            Timezone object or None for system timezone
        """
        tz_name = self.config.get('SCHEDULE_TIMEZONE')
        if tz_name:
            try:
                import pytz
                tz = pytz.timezone(tz_name)
                logger.info(f"Using configured timezone: {tz_name}")
                return tz
            except ImportError:
                logger.warning("pytz not installed, using system timezone")
            except Exception as e:
                logger.warning(f"Invalid timezone '{tz_name}': {e}, using system timezone")
        
        # Log current system time for clarity
        logger.info(f"Using system timezone. Current time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S %Z')}")
        return None
    
    def initialize_components(self) -> bool:
        """
        Initialize all required components.
        
        Returns:
            True if successful, False otherwise
        """
        try:
            # Initialize Discord handler
            discord_token = self.config.get('DISCORD_TOKEN')
            discord_channel = self.config.get('DISCORD_CHANNEL_ID')
            
            if not discord_token or not discord_channel:
                logger.error("Missing Discord configuration")
                return False
            
            discord_handler = DiscordHandler(discord_token, discord_channel)
            
            # Initialize Sheets handler
            sheets_id = self.config.get('GOOGLE_SHEETS_ID')
            service_account = self.config.get('GOOGLE_SERVICE_ACCOUNT_FILE')
            
            if not sheets_id or not service_account:
                logger.error("Missing Google Sheets configuration")
                return False
            
            sheets_handler = GoogleSheetsHandler(service_account, sheets_id)
            
            # Create data collector
            self.data_collector = DataCollectionOrchestrator(
                discord_handler,
                sheets_handler,
                self.config
            )
            
            # Create workflow orchestrator
            gemini_key = self.config.get('GEMINI_API_KEY')
            
            # Prepare publisher config if available
            publisher_config = None
            publisher_type = self.config.get('PUBLISHER_TYPE', '').lower()
            
            if publisher_type == 'twitter' or publisher_type == 'x':
                if all([
                    self.config.get('X_API_KEY'),
                    self.config.get('X_API_SECRET'),
                    self.config.get('X_ACCESS_TOKEN'),
                    self.config.get('X_ACCESS_TOKEN_SECRET')
                ]):
                    publisher_config = {
                        'type': 'twitter',
                        'api_key': self.config['X_API_KEY'],
                        'api_secret': self.config['X_API_SECRET'],
                        'access_token': self.config['X_ACCESS_TOKEN'],
                        'access_token_secret': self.config['X_ACCESS_TOKEN_SECRET']
                    }
                    logger.info("X/Twitter publisher configured")
                    
            elif publisher_type == 'typefully':
                if self.config.get('TYPEFULLY_API_KEY'):
                    publisher_config = {
                        'type': 'typefully',
                        'api_key': self.config['TYPEFULLY_API_KEY'],
                        'hours_delay': int(self.config.get('TYPEFULLY_HOURS_DELAY', 0))
                    }
                    logger.info("Typefully publisher configured")
            
            self.workflow_orchestrator = WorkflowOrchestrator(
                sheets_handler,
                gemini_api_key=gemini_key,
                publisher_config=publisher_config
            )
            
            logger.info("All components initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize components: {e}")
            return False
    
    def run_complete_pipeline(self) -> Dict:
        """
        Run the complete pipeline synchronously.
        
        Returns:
            Dictionary with pipeline results
        """
        results = {
            'timestamp': datetime.now().isoformat(),
            'data_collection': None,
            'workflow': None,
            'overall_success': False,
            'summary': []
        }
        
        start_time = time.time()
        
        logger.info("="*80)
        logger.info(f"Starting Complete Pipeline - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info("="*80)
        
        # Step 1: Data Collection (Discord → Sheets)
        logger.info("Step 1: Discord Data Collection")
        logger.info("-"*40)
        
        try:
            # Run async data collection in sync context
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            collection_results = loop.run_until_complete(
                self.data_collector.run_data_collection()
            )
            
            loop.close()
            
            results['data_collection'] = collection_results
            
            if collection_results['success']:
                results['summary'].append(
                    f"✅ Collected {collection_results['posts_collected']} posts, "
                    f"uploaded {collection_results['posts_uploaded']} new posts "
                    f"({collection_results['duplicates_skipped']} duplicates skipped)"
                )
            else:
                results['summary'].append(
                    f"❌ Data collection failed: {collection_results['errors']}"
                )
                
        except Exception as e:
            logger.error(f"Data collection error: {e}")
            results['data_collection'] = {
                'success': False,
                'errors': [str(e)]
            }
            results['summary'].append(f"❌ Data collection error: {e}")
        
        # Step 2: Workflow Orchestration (AI → Publishing → Archive)
        logger.info("\nStep 2: Workflow Orchestration")
        logger.info("-"*40)
        
        try:
            workflow_results = self.workflow_orchestrator.run_complete_workflow()
            results['workflow'] = workflow_results
            
            # Add workflow summary items
            if workflow_results.get('summary'):
                results['summary'].extend(workflow_results['summary'])
                
        except Exception as e:
            logger.error(f"Workflow orchestration error: {e}")
            results['workflow'] = {
                'success': False,
                'errors': [str(e)]
            }
            results['summary'].append(f"❌ Workflow error: {e}")
        
        # Calculate overall success
        results['overall_success'] = all([
            results['data_collection']['success'] if results['data_collection'] else False,
            results['workflow']['overall_success'] if results['workflow'] else False
        ])
        
        # Calculate runtime
        runtime = time.time() - start_time
        
        # Log summary
        logger.info("="*80)
        logger.info("Pipeline Complete")
        logger.info("-"*80)
        for line in results['summary']:
            logger.info(line)
        logger.info(f"\nOverall Status: {'✅ SUCCESS' if results['overall_success'] else '❌ FAILED'}")
        logger.info(f"Runtime: {runtime:.1f} seconds")
        logger.info("="*80)
        
        return results
    
    def run_manual(self) -> Dict:
        """
        Run the pipeline once manually.
        
        Returns:
            Dictionary with execution results
        """
        logger.info("Running pipeline manually...")
        
        if not self.initialize_components():
            return {
                'success': False,
                'error': 'Failed to initialize components'
            }
        
        return self.run_complete_pipeline()
    
    def schedule_daily(self):
        """Set up daily scheduling."""
        schedule_time = self.config.get('SCHEDULE_TIME', '20:00')
        
        # Schedule the task
        schedule.every().day.at(schedule_time).do(self.run_complete_pipeline)
        
        # Log scheduling info
        tz_info = f" ({self.config.get('SCHEDULE_TIMEZONE')})" if self.config.get('SCHEDULE_TIMEZONE') else " (system timezone)"
        logger.info(f"Scheduled daily pipeline run at {schedule_time}{tz_info}")
        
        # Log next run time
        next_run = schedule.next_run()
        if next_run:
            logger.info(f"Next scheduled run: {next_run}")
    
    def start(self):
        """Start the scheduler daemon."""
        logger.info("Starting scheduler daemon...")
        
        if not self.initialize_components():
            logger.error("Failed to initialize, exiting")
            return
        
        # Set up scheduling
        self.schedule_daily()
        
        # Main daemon loop
        logger.info("Scheduler is running. Press Ctrl+C to stop.")
        
        while not self._shutdown:
            try:
                schedule.run_pending()
                time.sleep(60)  # Check every minute
            except KeyboardInterrupt:
                logger.info("Received interrupt signal")
                break
            except Exception as e:
                logger.error(f"Error in scheduler loop: {e}")
                # Continue running despite errors
        
        logger.info("Scheduler stopped")