"""
Scheduler Module for Discord to Google Sheets Pipeline

This module orchestrates the complete data pipeline with clean async/sync separation:
1. Async Discord data collection → CSV
2. Sync processing: CSV → Sheets → AI → Publishing → Archive
"""

import asyncio
import csv
import signal
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any
import schedule

from modules.discord_handler import DiscordHandler, TwitterPost
from modules.sheets_handler import GoogleSheetsHandler
from modules.gemini_analyzer import GeminiAnalyzer, SheetAnalyzer
from modules.x_publisher import create_publisher, SheetPublisher
from modules.archive_handler import ArchiveHandler
from utils.logger import setup_logger

logger = setup_logger(__name__)


class AsyncDiscordCollector:
    """Handles async Discord data collection in isolation"""
    
    def __init__(self, discord_token: str, channel_id: str, config: Dict[str, Any]):
        """
        Initialize Discord collector
        
        Args:
            discord_token: Discord bot token
            channel_id: Discord channel ID to monitor
            config: Configuration dictionary
        """
        self.discord_token = discord_token
        self.channel_id = channel_id
        self.config = config
    
    async def collect_to_csv(self) -> Optional[str]:
        """
        Main entry point - collects Discord data to CSV
        
        Returns:
            Path to CSV file if successful, None otherwise
        """
        handler = None
        try:
            logger.info("Starting async Discord collection...")
            
            # Connect to Discord
            handler = DiscordHandler(self.discord_token, self.channel_id)
            logger.info("Connecting to Discord...")
            await handler.connect()
            logger.info("Discord connected successfully")
            
            # Determine time window
            after = self._get_time_window()
            
            # Fetch posts
            limit = int(self.config.get('DISCORD_FETCH_LIMIT', 200))
            logger.info(f"Fetching up to {limit} messages after {after}")
            
            posts = await handler.fetch_twitter_posts_with_retry(
                limit=limit,
                after=after
            )
            
            logger.info(f"Collected {len(posts)} Twitter/X posts from Discord")
            
            if not posts:
                logger.info("No posts found, skipping CSV creation")
                return None
            
            # Save to CSV
            csv_path = self._save_to_csv(posts)
            logger.info(f"Saved {len(posts)} posts to {csv_path}")
            
            return csv_path
            
        except Exception as e:
            logger.error(f"Discord collection failed: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            return None
            
        finally:
            # Always disconnect
            if handler:
                try:
                    logger.info("Disconnecting from Discord...")
                    await handler.disconnect()
                    logger.info("Discord disconnected")
                except Exception as e:
                    logger.warning(f"Error disconnecting from Discord: {e}")
    
    def _get_time_window(self) -> Optional[datetime]:
        """
        Determine time window based on collection mode
        
        Returns:
            Datetime for after parameter, or None for all messages
        """
        collection_mode = self.config.get('DISCORD_COLLECTION_MODE', 'daily')
        
        if collection_mode == 'daily':
            lookback_days = int(self.config.get('DISCORD_LOOKBACK_DAYS', 1))
            after = datetime.now() - timedelta(days=lookback_days)
            logger.info(f"Collection mode: daily (last {lookback_days} days)")
            
        elif collection_mode == 'hours':
            lookback_hours = int(self.config.get('DISCORD_LOOKBACK_HOURS', 24))
            after = datetime.now() - timedelta(hours=lookback_hours)
            logger.info(f"Collection mode: hours (last {lookback_hours} hours)")
            
        elif collection_mode == 'since_last':
            # This will need to be passed from the processor
            # For now, default to 1 day
            after = datetime.now() - timedelta(days=1)
            logger.info("Collection mode: since_last (defaulting to 1 day)")
        else:
            after = None
            logger.info("Collection mode: all messages")
        
        return after
    
    def _save_to_csv(self, posts: List[TwitterPost]) -> str:
        """
        Save posts to timestamped CSV file
        
        Args:
            posts: List of TwitterPost objects
            
        Returns:
            Path to created CSV file
        """
        # Create data directory if it doesn't exist
        data_dir = Path('data')
        data_dir.mkdir(exist_ok=True)
        
        # Generate timestamp for filename
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        csv_path = data_dir / f'discord_posts_{timestamp}.csv'
        
        # Write CSV
        with open(csv_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            
            # Write headers
            writer.writerow(['date', 'time', 'content', 'post_link', 'author', 'author_link'])
            
            # Write data
            for post in posts:
                writer.writerow([
                    post.date,
                    post.time,
                    post.content,
                    post.post_link,
                    post.author,
                    post.author_link
                ])
        
        return str(csv_path)


class SequentialProcessor:
    """Handles all synchronous processing after Discord collection"""
    
    def __init__(self, sheets_handler: GoogleSheetsHandler, config: Dict[str, Any]):
        """
        Initialize sequential processor
        
        Args:
            sheets_handler: GoogleSheetsHandler instance
            config: Configuration dictionary
        """
        self.sheets = sheets_handler
        self.config = config
        self.gemini_analyzer = None
        self.publisher = None
        
        # Initialize Gemini if configured
        gemini_key = config.get('GEMINI_API_KEY')
        if gemini_key:
            try:
                self.gemini_analyzer = GeminiAnalyzer(
                    api_key=gemini_key,
                    model=config.get('GEMINI_MODEL', 'gemini-1.5-flash'),
                    daily_limit=int(config.get('GEMINI_DAILY_LIMIT', 1400))
                )
                logger.info("Gemini analyzer initialized")
            except Exception as e:
                logger.error(f"Failed to initialize Gemini: {e}")
        
        # Initialize publisher if configured
        if config.get('PUBLISHER_TYPE'):
            self._init_publisher()
    
    def _init_publisher(self):
        """Initialize publisher based on configuration"""
        pub_type = self.config.get('PUBLISHER_TYPE', '').lower()
        
        try:
            if pub_type in ['twitter', 'x']:
                self.publisher = create_publisher(
                    'twitter',
                    api_key=self.config.get('X_API_KEY'),
                    api_secret=self.config.get('X_API_SECRET'),
                    access_token=self.config.get('X_ACCESS_TOKEN'),
                    access_token_secret=self.config.get('X_ACCESS_TOKEN_SECRET')
                )
                logger.info("Twitter/X publisher initialized")
                
            elif pub_type == 'typefully':
                self.publisher = create_publisher(
                    'typefully',
                    api_key=self.config.get('TYPEFULLY_API_KEY'),
                    hours_delay=int(self.config.get('TYPEFULLY_HOURS_DELAY', 0))
                )
                logger.info("Typefully publisher initialized")
            else:
                logger.warning(f"Unknown publisher type: {pub_type}")
                
        except Exception as e:
            logger.error(f"Failed to initialize publisher: {e}")
    
    def process_csv_to_sheets(self, csv_path: str) -> Dict:
        """
        Read CSV and upload to Google Sheets
        
        Args:
            csv_path: Path to CSV file
            
        Returns:
            Dictionary with upload results
        """
        results = {
            'success': False,
            'uploaded': 0,
            'duplicates': 0,
            'errors': []
        }
        
        try:
            logger.info(f"Processing CSV: {csv_path}")
            
            # Read CSV
            posts = []
            with open(csv_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    posts.append([
                        row['date'],
                        row['time'],
                        row['content'],
                        row['post_link'],
                        row['author'],
                        row['author_link']
                    ])
            
            logger.info(f"Read {len(posts)} posts from CSV")
            
            if not posts:
                logger.info("No posts to upload")
                results['success'] = True
                return results
            
            # Check for duplicates if configured
            if self.config.get('DISCORD_SKIP_DUPLICATES', 'true').lower() == 'true':
                new_posts = self._filter_duplicates(posts)
                results['duplicates'] = len(posts) - len(new_posts)
            else:
                new_posts = posts
            
            # Upload to sheets
            if new_posts:
                # Ensure headers exist
                existing_data = self.sheets.get_sheet_data()
                if not existing_data:
                    headers = ["Date", "Time", "Content", "Post Link", "Author", "Author Link"]
                    self.sheets.append_data([headers])
                    logger.info("Added headers to empty sheet")
                
                # Batch upload
                batch_size = int(self.config.get('SHEETS_BATCH_SIZE', 100))
                self.sheets.batch_append_data(new_posts, batch_size=batch_size)
                
                results['uploaded'] = len(new_posts)
                logger.info(f"Uploaded {len(new_posts)} posts to Google Sheets")
            else:
                logger.info("No new posts to upload after filtering duplicates")
            
            results['success'] = True
            
        except Exception as e:
            logger.error(f"CSV processing failed: {e}")
            results['errors'].append(str(e))
        
        return results
    
    def _filter_duplicates(self, posts: List[List[str]]) -> List[List[str]]:
        """
        Filter out posts that already exist in Google Sheets
        
        Args:
            posts: List of post rows
            
        Returns:
            List of posts that don't exist in sheets
        """
        try:
            # Get existing data
            existing_data = self.sheets.get_sheet_data()
            
            if len(existing_data) <= 1:  # Only headers or empty
                logger.info("No existing data in sheets")
                return posts
            
            # Find Post Link column index
            headers = existing_data[0] if existing_data else []
            link_col_idx = -1
            for idx, header in enumerate(headers):
                if 'Post Link' in header:
                    link_col_idx = idx
                    break
            
            if link_col_idx < 0:
                logger.warning("Post Link column not found, skipping duplicate check")
                return posts
            
            # Build set of existing links
            existing_links = set()
            for row in existing_data[1:]:  # Skip headers
                if len(row) > link_col_idx and row[link_col_idx]:
                    existing_links.add(row[link_col_idx])
            
            # Filter posts
            filtered_posts = []
            for post in posts:
                if len(post) > 3 and post[3]:  # post[3] is post_link
                    if post[3] not in existing_links:
                        filtered_posts.append(post)
                else:
                    filtered_posts.append(post)  # Keep posts without links
            
            duplicates_count = len(posts) - len(filtered_posts)
            if duplicates_count > 0:
                logger.info(f"Filtered out {duplicates_count} duplicate posts")
            
            return filtered_posts
            
        except Exception as e:
            logger.error(f"Error checking for duplicates: {e}")
            return posts  # Return all posts if duplicate check fails
    
    def run_gemini_analysis(self) -> Dict:
        """
        Direct call to Gemini AI analysis with rate limiting and retry logic
        
        Returns:
            Dictionary with analysis results
        """
        results = {
            'success': False,
            'projects_found': 0,
            'posts_analyzed': 0,
            'errors': []
        }
        
        if not self.gemini_analyzer:
            logger.info("Gemini not configured, skipping analysis")
            results['success'] = True
            return results
        
        max_retries = 3
        retry_count = 0
        
        while retry_count < max_retries:
            try:
                logger.info(f"Starting Gemini AI analysis... (attempt {retry_count + 1}/{max_retries})")
                
                # Create SheetAnalyzer
                analyzer = SheetAnalyzer(self.sheets, self.gemini_analyzer)
                
                # Ensure columns exist
                ai_summary_col, ai_processed_col, daily_draft_col = analyzer.ensure_columns_exist()
                logger.info(f"AI columns: summary={ai_summary_col}, processed={ai_processed_col}, draft={daily_draft_col}")
                
                # Analyze all unprocessed rows
                project_summaries, all_processed = analyzer.analyze_all_rows()
                
                results['projects_found'] = len(project_summaries)
                results['posts_analyzed'] = len(all_processed)
                
                # Write summaries and mark processed
                if all_processed:
                    analyzer.write_summaries(all_processed, ai_summary_col, ai_processed_col)
                    logger.info(f"Wrote {len(all_processed)} AI summaries/statuses")
                
                # Generate and write daily draft
                if project_summaries:
                    analyzer.generate_and_write_daily_draft(project_summaries, daily_draft_col)
                    logger.info("Generated daily draft")
                
                results['success'] = True
                logger.info(f"Analysis complete: {results['projects_found']} projects, "
                           f"{results['posts_analyzed']} posts analyzed")
                break  # Success, exit retry loop
                
            except Exception as e:
                error_msg = str(e)
                
                # Check if it's a rate limit error
                if "RATE_LIMITED" in error_msg or "429" in error_msg or "quota" in error_msg.lower():
                    retry_count += 1
                    if retry_count < max_retries:
                        # Exponential backoff: 30s, 60s, 120s
                        wait_time = 30 * (2 ** (retry_count - 1))
                        logger.warning(f"Rate limited, waiting {wait_time} seconds before retry...")
                        time.sleep(wait_time)
                        continue
                    else:
                        logger.error("Max retries reached for rate limiting")
                        results['errors'].append("Rate limited after multiple retries")
                else:
                    # Non-rate-limit error, don't retry
                    logger.error(f"Gemini analysis failed: {e}")
                    results['errors'].append(str(e))
                    break
        
        # If we still don't have success after retries, mark as partial success
        # if some posts were analyzed
        if not results['success'] and results['posts_analyzed'] > 0:
            logger.info(f"Partial success: analyzed {results['posts_analyzed']} posts before rate limit")
            results['success'] = True  # Consider partial analysis as success
        
        return results
    
    def run_publisher(self) -> Dict:
        """
        Direct call to publisher
        
        Returns:
            Dictionary with publishing results
        """
        results = {
            'success': False,
            'published': False,
            'url': None,
            'errors': []
        }
        
        if not self.publisher:
            logger.info("Publisher not configured, skipping")
            results['success'] = True
            return results
        
        try:
            logger.info("Starting publishing...")
            
            # Create SheetPublisher wrapper
            sheet_publisher = SheetPublisher(self.publisher, self.sheets)
            
            # Get sheet data
            sheet_data = self.sheets.get_sheet_data()
            if len(sheet_data) < 2:
                logger.info("No data rows in sheet")
                results['success'] = True
                return results
            
            # Find Daily Post Draft column
            headers = sheet_data[0]
            draft_col = -1
            for idx, header in enumerate(headers):
                if 'Daily Post Draft' in header or 'AI Draft' in header:
                    draft_col = idx
                    break
            
            if draft_col < 0:
                logger.info("Draft column not found")
                results['success'] = True
                return results
            
            # Find first non-empty draft
            for idx, row in enumerate(sheet_data[1:], start=2):
                if len(row) > draft_col and row[draft_col] and row[draft_col].strip():
                    logger.info(f"Found draft at row {idx}")
                    
                    # Publish
                    publish_result = sheet_publisher.publish_from_sheet(idx)
                    
                    if publish_result.success:
                        results['success'] = True
                        results['published'] = True
                        results['url'] = publish_result.url
                        logger.info(f"Published successfully: {publish_result.url or publish_result.post_id}")
                    else:
                        logger.error(f"Publishing failed: {publish_result.error_msg}")
                        results['errors'].append(publish_result.error_msg)
                    
                    break
            else:
                logger.info("No draft found to publish")
                results['success'] = True
            
        except Exception as e:
            logger.error(f"Publishing failed: {e}")
            results['errors'].append(str(e))
        
        return results
    
    def run_archiver(self) -> Dict:
        """
        Direct call to archive handler
        
        Returns:
            Dictionary with archive results
        """
        results = {
            'success': False,
            'posts_archived': 0,
            'errors': []
        }
        
        try:
            logger.info("Starting archive process...")
            
            # Create ArchiveHandler
            archiver = ArchiveHandler(self.sheets)
            
            # Run archive workflow
            archive_results = archiver.run_archive_workflow()
            
            results['success'] = archive_results.get('success', False)
            results['posts_archived'] = archive_results.get('posts_archived', 0)
            
            if not results['success']:
                results['errors'] = archive_results.get('errors', [])
            
            logger.info(f"Archived {results['posts_archived']} posts")
            
        except Exception as e:
            logger.error(f"Archive failed: {e}")
            results['errors'].append(str(e))
        
        return results
    
    def cleanup_csv(self, csv_path: str):
        """
        Move processed CSV to archive
        
        Args:
            csv_path: Path to CSV file to archive
        """
        try:
            csv_file = Path(csv_path)
            if not csv_file.exists():
                logger.warning(f"CSV file not found: {csv_path}")
                return
            
            # Create processed directory
            processed_dir = Path('data/processed')
            processed_dir.mkdir(parents=True, exist_ok=True)
            
            # Move file
            dest_path = processed_dir / csv_file.name
            csv_file.rename(dest_path)
            
            logger.info(f"Moved CSV to: {dest_path}")
            
        except Exception as e:
            logger.error(f"Failed to archive CSV: {e}")


class ScheduledTaskRunner:
    """Main orchestrator coordinating all phases"""
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize scheduled task runner
        
        Args:
            config: Configuration dictionary
        """
        self.config = config
        self.async_collector = None
        self.processor = None
        self._shutdown = False
        
        # Setup signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals gracefully"""
        _ = signum  # Unused but required by signal handler signature
        _ = frame   # Unused but required by signal handler signature
        logger.info("Received shutdown signal, finishing current task...")
        self._shutdown = True
    
    def initialize_components(self) -> bool:
        """
        Initialize all required components
        
        Returns:
            True if successful, False otherwise
        """
        logger.info("Initializing components...")
        
        try:
            # Get Discord config
            discord_token = self.config.get('DISCORD_TOKEN')
            discord_channel = self.config.get('DISCORD_CHANNEL_ID')
            
            if not discord_token or not discord_channel:
                logger.error("Missing Discord configuration")
                return False
            
            # Initialize async collector
            self.async_collector = AsyncDiscordCollector(
                discord_token,
                discord_channel,
                self.config
            )
            
            # Get Sheets config
            sheets_id = self.config.get('GOOGLE_SHEETS_ID')
            service_account = self.config.get('GOOGLE_SERVICE_ACCOUNT_FILE')
            
            if not sheets_id or not service_account:
                logger.error("Missing Google Sheets configuration")
                return False
            
            # Initialize sheets handler
            sheets_handler = GoogleSheetsHandler(service_account, sheets_id)
            
            # Initialize processor
            self.processor = SequentialProcessor(sheets_handler, self.config)
            
            logger.info("All components initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize components: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            return False
    
    def run_complete_pipeline(self) -> Dict:
        """
        Execute complete pipeline with clean async/sync separation
        
        Returns:
            Dictionary with pipeline results
        """
        results = {
            'timestamp': datetime.now().isoformat(),
            'csv_file': None,
            'discord_collection': None,
            'sheets_upload': None,
            'ai_analysis': None,
            'publishing': None,
            'archive': None,
            'overall_success': False,
            'summary': []
        }
        
        start_time = time.time()
        
        logger.info("="*80)
        logger.info(f"Starting Complete Pipeline - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info("="*80)
        
        # Phase 1: Async Discord collection (isolated)
        logger.info("\nPhase 1: Discord Data Collection (Async)")
        logger.info("-"*40)
        
        try:
            # Run Discord collection in isolated event loop
            csv_file = asyncio.run(self.async_collector.collect_to_csv())
            
            if csv_file:
                results['csv_file'] = csv_file
                results['discord_collection'] = {'success': True, 'csv_file': csv_file}
                results['summary'].append(f"✅ Discord data collected to: {csv_file}")
                
                # Phase 2: CSV to Google Sheets (Sync)
                logger.info("\nPhase 2: CSV to Google Sheets (Sync)")
                logger.info("-"*40)
                
                sheets_results = self.processor.process_csv_to_sheets(csv_file)
                results['sheets_upload'] = sheets_results
                
                if sheets_results['success']:
                    results['summary'].append(
                        f"✅ Uploaded {sheets_results['uploaded']} posts "
                        f"({sheets_results['duplicates']} duplicates skipped)"
                    )
                else:
                    results['summary'].append(f"❌ Sheets upload failed: {sheets_results['errors']}")
                
                # Phase 3: Gemini AI Analysis (Sync)
                logger.info("\nPhase 3: Gemini AI Analysis (Sync)")
                logger.info("-"*40)
                
                # Check if we should skip AI analysis
                skip_ai = self.config.get('SKIP_AI_ON_RATE_LIMIT', 'true').lower() == 'true'
                
                ai_results = self.processor.run_gemini_analysis()
                results['ai_analysis'] = ai_results
                
                if ai_results['success']:
                    if ai_results['posts_analyzed'] > 0:
                        results['summary'].append(
                            f"✅ Analyzed {ai_results['posts_analyzed']} posts, "
                            f"found {ai_results['projects_found']} projects"
                        )
                    else:
                        results['summary'].append("ℹ️  No new posts to analyze (all previously processed)")
                else:
                    if skip_ai and any("rate" in err.lower() or "quota" in err.lower() for err in ai_results.get('errors', [])):
                        results['summary'].append("⚠️  AI analysis skipped due to rate limiting")
                        # Don't fail the pipeline for rate limits if configured to skip
                        ai_results['success'] = True
                    else:
                        results['summary'].append(f"❌ AI analysis failed: {ai_results['errors']}")
                
                # Phase 4: Publishing (Sync)
                logger.info("\nPhase 4: Publishing (Sync)")
                logger.info("-"*40)
                
                pub_results = self.processor.run_publisher()
                results['publishing'] = pub_results
                
                if pub_results['success']:
                    if pub_results['published']:
                        results['summary'].append(f"✅ Published successfully: {pub_results['url']}")
                    else:
                        results['summary'].append("ℹ️  No draft available to publish")
                else:
                    results['summary'].append(f"❌ Publishing failed: {pub_results['errors']}")
                
                # Phase 5: Archive & Cleanup (Sync)
                logger.info("\nPhase 5: Archive & Cleanup (Sync)")
                logger.info("-"*40)
                
                archive_results = self.processor.run_archiver()
                results['archive'] = archive_results
                
                if archive_results['success']:
                    results['summary'].append(f"✅ Archived {archive_results['posts_archived']} posts")
                else:
                    results['summary'].append(f"❌ Archive failed: {archive_results['errors']}")
                
                # Cleanup CSV
                self.processor.cleanup_csv(csv_file)
                results['summary'].append(f"✅ CSV moved to processed directory")
                
                # Overall success if key phases succeeded
                results['overall_success'] = all([
                    sheets_results.get('success', False),
                    ai_results.get('success', False),
                    archive_results.get('success', False)
                ])
                
            else:
                results['discord_collection'] = {'success': False, 'error': 'No data collected'}
                results['summary'].append("ℹ️  No Discord data to process")
                results['overall_success'] = True  # Not a failure, just no data
                
        except Exception as e:
            logger.error(f"Pipeline error: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            results['summary'].append(f"❌ Pipeline error: {e}")
        
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
        Run the pipeline once manually
        
        Returns:
            Dictionary with execution results
        """
        logger.info("Running pipeline manually...")
        
        if not self.initialize_components():
            return {
                'overall_success': False,
                'error': 'Failed to initialize components'
            }
        
        return self.run_complete_pipeline()
    
    def schedule_daily(self):
        """Set up daily scheduling"""
        schedule_time = self.config.get('SCHEDULE_TIME', '20:00')
        
        # Schedule the task
        schedule.every().day.at(schedule_time).do(self.run_complete_pipeline)
        
        # Log scheduling info
        logger.info(f"Scheduled daily pipeline run at {schedule_time}")
        
        # Log next run time
        next_run = schedule.next_run()
        if next_run:
            logger.info(f"Next scheduled run: {next_run}")
    
    def start(self):
        """Start the scheduler daemon"""
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