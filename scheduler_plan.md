# Scheduler Module Implementation Plan

## Overview
The scheduler module will be the main entry point for the application, orchestrating the complete data pipeline from Discord to Archive. It will support both manual triggering and automatic daily scheduling.

## Architecture

### Complete Workflow Chain
```
Discord Channel (Async) → CSV File → Google Sheets → Gemini AI Analysis → Publishing → Archive
```

### Key Design Principles
1. **Clean separation of async and sync operations:**
   - Phase 1: Async Discord data collection → Save to CSV
   - Phase 2: Sequential sync processing of CSV data through the pipeline

2. **Direct module calls (no workflow_orchestrator):**
   - Each module called directly in sequence
   - Simple, transparent error handling
   - No complex orchestration layer

### Module Structure
```
modules/
├── scheduler.py              # Main scheduler module
└── ...existing modules...

data/
├── discord_posts_{timestamp}.csv  # Temporary CSV files
└── processed/                     # Archived CSV files after processing

main.py                       # Entry point that uses scheduler
```

## Implementation Details

### 1. Scheduler Module (`modules/scheduler.py`)

#### Key Components:

##### A. AsyncDiscordCollector Class
- Responsible for async Discord data collection ONLY
- Runs in isolated async context
- Methods:
  - `async collect_to_csv()`: Fetch posts from Discord and save to CSV
  - `async _connect_discord()`: Establish Discord connection
  - `async _fetch_posts()`: Retrieve posts based on time window
  - `async _save_to_csv()`: Write posts to CSV file
  - `async _disconnect()`: Clean disconnect from Discord

##### B. SequentialProcessor Class  
- Responsible for synchronous processing of CSV data
- Direct calls to individual modules (no workflow_orchestrator)
- Methods:
  - `process_csv_to_sheets()`: Read CSV and upload to Google Sheets
  - `run_gemini_analysis()`: Direct call to GeminiAnalyzer and SheetAnalyzer
  - `run_publisher()`: Direct call to SheetPublisher
  - `run_archiver()`: Direct call to ArchiveHandler
  - `cleanup_csv()`: Move processed CSV to archive

##### C. ScheduledTaskRunner Class
- Main orchestrator coordinating async and sync phases
- Methods:
  - `run_complete_pipeline()`: Execute full pipeline (async → sync)
  - `run_async_phase()`: Run Discord collection in new event loop
  - `run_sync_phase()`: Run sequential processing
  - `run_manual()`: Manual trigger for testing
  - `schedule_daily()`: Set up daily scheduling
  - `start()`: Main daemon loop

#### Core Features:

1. **Phase 1: Async Discord Data Collection**
   - Run in isolated async context using `asyncio.run()`
   - Connect to Discord using DiscordHandler
   - Fetch posts based on configured time window:
     - `daily` mode: Fetch posts from last N days
     - `hours` mode: Fetch posts from last N hours  
     - `since_last` mode: Fetch posts since last entry in Google Sheets
   - Process Twitter/X links from messages
   - Save to CSV with timestamp: `data/discord_posts_{YYYYMMDD_HHMMSS}.csv`
   - CSV columns: `date,time,content,post_link,author,author_link`
   - Properly close Discord connection after collection
   - Return CSV filepath for next phase

2. **Phase 2: Sequential CSV Processing**
   - Read CSV file from Phase 1
   - Check for duplicates against existing Google Sheets data
   - Upload new posts to Google Sheets main tab
   - Ensure headers exist before data upload
   - Handle batch uploads for large datasets

3. **Phase 3: Gemini AI Analysis (Direct Module Call)**
   - Initialize GeminiAnalyzer with API key
   - Create SheetAnalyzer instance
   - Analyze unprocessed rows in sheet
   - Update sheet with AI summaries
   - Generate daily draft if projects found

4. **Phase 4: Publishing (Direct Module Call)**
   - Create publisher instance (Twitter/Typefully)
   - Create SheetPublisher wrapper
   - Find draft in Daily Post Draft column
   - Publish if draft exists
   - Update sheet with publish status

5. **Phase 5: Archiving & Cleanup (Direct Module Call)**
   - Create ArchiveHandler instance
   - Move processed posts to Archive sheet
   - Clear processed rows from main sheet
   - Move CSV file to `data/processed/` directory
   - Generate summary report

6. **Scheduling & Control**
   - Use `schedule` library for simplicity
   - Support manual trigger via command-line flag
   - Daily execution at configured time (default 20:00)
   - Timezone support with optional SCHEDULE_TIMEZONE
   - Graceful shutdown handling

7. **Error Handling & Resilience**
   - Isolated async context prevents event loop conflicts
   - Each phase can fail independently without crashing pipeline
   - CSV files serve as backup if downstream processing fails
   - Detailed logging at each phase
   - Summary report after each run

### 2. Main Entry Point (`main.py`)

#### Features:
- Command-line interface with argparse
- Options:
  - `--manual`: Run once immediately
  - `--test`: Test mode (dry run)
  - `--daemon`: Run as daemon (default)
- Configuration validation before starting
- Proper signal handling for graceful shutdown

### 3. Configuration Requirements

#### Environment Variables:
```env
# Core Discord & Sheets (Required)
DISCORD_TOKEN=...
DISCORD_CHANNEL_ID=...
GOOGLE_SHEETS_ID=...
GOOGLE_SERVICE_ACCOUNT_FILE=credentials.json

# Scheduling
SCHEDULE_TIME=20:00  # 24-hour format (uses system local time)
SCHEDULE_TIMEZONE=  # Optional: Timezone (e.g., 'US/Eastern', 'UTC'). If empty, uses system timezone

# Discord Data Collection Time Window
DISCORD_COLLECTION_MODE=daily      # Options: 'daily', 'hours', 'since_last'
DISCORD_LOOKBACK_HOURS=24          # For 'hours' mode: how many hours to look back
DISCORD_LOOKBACK_DAYS=1            # For 'daily' mode: how many days to look back
DISCORD_FETCH_LIMIT=200            # Max messages to fetch per run
DISCORD_SKIP_DUPLICATES=true       # Check sheets for existing posts before uploading

# Optional: Gemini AI
GEMINI_API_KEY=...

# Optional: Publishing
PUBLISHER_TYPE=twitter  # or 'typefully'
X_API_KEY=...           # If using Twitter
# OR
TYPEFULLY_API_KEY=...   # If using Typefully
```

## Implementation Flow

### Manual Trigger Flow:
1. User runs: `python main.py --manual`
2. Validate configuration
3. Initialize ScheduledTaskRunner
4. Execute complete pipeline once
5. Display summary and exit

### Scheduled Daemon Flow:
1. User runs: `python main.py` or `python main.py --daemon`
2. Validate configuration
3. Initialize ScheduledTaskRunner
4. Schedule daily task at SCHEDULE_TIME
5. Enter daemon loop
6. Execute pipeline at scheduled time
7. Continue running until interrupted

### Pipeline Execution Steps:

1. **Phase 1: Async Discord Collection (Isolated)**
   ```python
   # Run in new event loop to avoid conflicts
   csv_file = asyncio.run(async_discord_collector.collect_to_csv())
   ```
   - Create new event loop
   - Connect to Discord
   - Determine time window based on DISCORD_COLLECTION_MODE
   - Fetch messages from channel
   - Filter for Twitter/X links
   - Write to CSV: `data/discord_posts_{timestamp}.csv`
   - Disconnect from Discord
   - Close event loop
   - Return CSV filepath

2. **Phase 2: CSV to Google Sheets (Sync)**
   ```python
   # Process CSV synchronously
   processor.process_csv_to_sheets(csv_file)
   ```
   - Read CSV file
   - Connect to Google Sheets
   - Check last entry date
   - Filter out duplicates
   - Upload new posts
   - Log statistics

3. **Phase 3: Gemini AI Analysis (Sync - Direct Module Call)**
   ```python
   # Direct call to GeminiAnalyzer and SheetAnalyzer
   results['ai'] = processor.run_gemini_analysis()
   ```
   - Initialize GeminiAnalyzer with API key
   - Create SheetAnalyzer instance
   - Read unprocessed entries from sheet
   - Send to Gemini for analysis
   - Update sheet with AI summaries
   - Generate daily draft if projects found

4. **Phase 4: Publishing (Sync - Direct Module Call)**
   ```python
   # Direct call to publisher modules
   results['publishing'] = processor.run_publisher()
   ```
   - Create publisher instance (Twitter/Typefully)
   - Wrap with SheetPublisher
   - Check for drafts in Daily Post Draft column
   - Publish if draft exists
   - Update sheet with publish status

5. **Phase 5: Archive & Cleanup (Sync - Direct Module Call)**
   ```python
   # Direct call to ArchiveHandler
   results['archive'] = processor.run_archiver()
   processor.cleanup_csv(csv_file)
   ```
   - Create ArchiveHandler instance
   - Archive processed posts to Archive sheet
   - Clear processed rows from main sheet
   - Move CSV to `data/processed/`
   - Generate summary report

## Error Handling Strategy

### Failure Modes:
1. **Discord Connection Failure**
   - Log error, skip data collection
   - Continue with existing sheet data

2. **Sheets Upload Failure**
   - Log error with details
   - Retry with exponential backoff
   - Continue to workflow if retries exhausted

3. **AI Analysis Failure**
   - Log error, continue to publishing

4. **Publishing Failure**
   - Log error, continue to archiving

5. **Archive Failure**
   - Log error, complete pipeline
   - Alert in summary report

## Logging & Monitoring

### Log Levels:
- **INFO**: Normal operations, summaries
- **WARNING**: Recoverable issues, skipped steps
- **ERROR**: Failures requiring attention
- **DEBUG**: Detailed troubleshooting info

### Summary Report Format:
```
================================================================================
Daily Pipeline Run - 2024-01-15 20:00:00 (PST)
================================================================================
Phase 1: Discord Collection
  ✅ Fetched 25 messages from Discord
  ✅ Found 18 Twitter/X posts
  ✅ Saved to: data/discord_posts_20240115_200000.csv

Phase 2: CSV to Google Sheets
  ✅ Uploaded 15 new posts (3 duplicates skipped)

Phase 3: Gemini AI Analysis (Direct Call)
  ✅ Analyzed 15 posts
  ✅ Found 5 crypto projects
  ✅ Generated daily draft

Phase 4: Publishing (Direct Call)
  ✅ Published to X/Twitter
  📝 Post ID: 123456789

Phase 5: Archive & Cleanup (Direct Call)
  ✅ Archived 15 processed posts
  📊 Total archived: 1,234 posts
  ✅ CSV moved to: data/processed/

Overall Status: ✅ SUCCESS
Runtime: 45.3 seconds
================================================================================
```

## Testing Strategy

### Unit Tests:
- Test data collection logic
- Test duplicate detection
- Test error handling
- Mock external APIs

### Integration Tests:
- Test with test Discord channel
- Test with test Google Sheet
- Verify complete pipeline flow

### Manual Testing:
```bash
# Test configuration
python main.py --test

# Run once manually
python main.py --manual

# Run with debug logging
LOG_LEVEL=DEBUG python main.py --manual
```

## Deployment Considerations

### System Requirements:
- Python 3.8+
- Stable internet connection
- Sufficient API quotas

### Resource Usage:
- Memory: ~100MB typical
- CPU: Minimal except during processing
- Network: Burst during data collection

### Monitoring:
- Log rotation (daily)
- Error alerting (optional)
- Performance metrics logging

## Future Enhancements

1. **Web Dashboard**
   - Real-time status
   - Manual trigger button
   - Configuration UI

2. **Advanced Scheduling**
   - Multiple daily runs
   - Weekday/weekend schedules
   - Holiday awareness

3. **Data Analytics**
   - Post engagement tracking
   - Trend analysis
   - Performance metrics

4. **Notification System**
   - Email alerts on failure
   - Slack/Discord notifications
   - Summary reports

## Implementation Priority

### Phase 1 (Core - Must Have):
1. Basic scheduler with manual trigger
2. Discord to Sheets data collection
3. Integration with WorkflowOrchestrator
4. Daily scheduling support
5. Basic error handling and logging

### Phase 2 (Enhancement - Nice to Have):
1. Advanced error recovery
2. Duplicate detection optimization
3. Performance monitoring
4. Configuration validation
5. Test mode implementation

### Phase 3 (Future - Optional):
1. Web interface
2. Advanced analytics
3. Notification system
4. Multi-channel support

## Code Example Structure

```python
# modules/scheduler.py
import asyncio
import csv
from pathlib import Path
from datetime import datetime

class AsyncDiscordCollector:
    """Handles async Discord data collection in isolation"""
    
    def __init__(self, discord_token, channel_id, config):
        self.discord_token = discord_token
        self.channel_id = channel_id
        self.config = config
    
    async def collect_to_csv(self) -> str:
        """Main entry point - collects Discord data to CSV"""
        try:
            # Connect to Discord
            handler = DiscordHandler(self.discord_token, self.channel_id)
            await handler.connect()
            
            # Determine time window
            after = self._get_time_window()
            
            # Fetch posts
            posts = await handler.fetch_twitter_posts_with_retry(
                limit=self.config.get('DISCORD_FETCH_LIMIT', 200),
                after=after
            )
            
            # Save to CSV
            csv_path = self._save_to_csv(posts)
            
            # Disconnect
            await handler.disconnect()
            
            return csv_path
            
        except Exception as e:
            logger.error(f"Discord collection failed: {e}")
            raise
    
    def _save_to_csv(self, posts) -> str:
        """Save posts to timestamped CSV file"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        csv_path = Path(f'data/discord_posts_{timestamp}.csv')
        csv_path.parent.mkdir(exist_ok=True)
        
        with open(csv_path, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['date', 'time', 'content', 'post_link', 'author', 'author_link'])
            for post in posts:
                writer.writerow([
                    post.date, post.time, post.content,
                    post.post_link, post.author, post.author_link
                ])
        
        return str(csv_path)

class SequentialProcessor:
    """Handles all synchronous processing after Discord collection"""
    
    def __init__(self, sheets_handler, config):
        self.sheets = sheets_handler
        self.config = config
        self.gemini_analyzer = None
        self.publisher = None
        
        # Initialize Gemini if configured
        if config.get('GEMINI_API_KEY'):
            from modules.gemini_analyzer import GeminiAnalyzer
            self.gemini_analyzer = GeminiAnalyzer(api_key=config['GEMINI_API_KEY'])
        
        # Initialize publisher if configured
        if config.get('PUBLISHER_TYPE'):
            self._init_publisher()
    
    def process_csv_to_sheets(self, csv_path: str) -> dict:
        """Read CSV and upload to Google Sheets"""
        posts = []
        with open(csv_path, 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                posts.append([
                    row['date'], row['time'], row['content'],
                    row['post_link'], row['author'], row['author_link']
                ])
        
        # Check for duplicates and upload
        new_posts = self._filter_duplicates(posts)
        if new_posts:
            self.sheets.batch_append_data(new_posts)
        
        return {'uploaded': len(new_posts), 'duplicates': len(posts) - len(new_posts)}
    
    def run_gemini_analysis(self) -> dict:
        """Direct call to Gemini AI analysis"""
        if not self.gemini_analyzer:
            return {'success': False, 'error': 'Gemini not configured'}
        
        from modules.gemini_analyzer import SheetAnalyzer
        analyzer = SheetAnalyzer(self.sheets, self.gemini_analyzer)
        
        # Ensure columns exist
        ai_summary_col, ai_processed_col, daily_draft_col = analyzer.ensure_columns_exist()
        
        # Analyze rows
        project_summaries, all_processed = analyzer.analyze_all_rows()
        
        # Write results
        if all_processed:
            analyzer.write_summaries(all_processed, ai_summary_col, ai_processed_col)
        if project_summaries:
            analyzer.generate_and_write_daily_draft(project_summaries, daily_draft_col)
        
        return {
            'success': True,
            'projects_found': len(project_summaries),
            'posts_analyzed': len(all_processed)
        }
    
    def run_publisher(self) -> dict:
        """Direct call to publisher"""
        if not self.publisher:
            return {'success': False, 'error': 'Publisher not configured'}
        
        from modules.x_publisher import SheetPublisher
        sheet_publisher = SheetPublisher(self.publisher, self.sheets)
        
        # Find draft to publish
        sheet_data = self.sheets.get_sheet_data()
        if len(sheet_data) < 2:
            return {'success': True, 'published': False}
        
        headers = sheet_data[0]
        draft_col = headers.index('Daily Post Draft') if 'Daily Post Draft' in headers else -1
        
        # Find first draft
        for idx, row in enumerate(sheet_data[1:], start=2):
            if draft_col >= 0 and len(row) > draft_col and row[draft_col]:
                result = sheet_publisher.publish_from_sheet(idx)
                return {
                    'success': result.success,
                    'published': result.success,
                    'url': result.url
                }
        
        return {'success': True, 'published': False}
    
    def run_archiver(self) -> dict:
        """Direct call to archive handler"""
        from modules.archive_handler import ArchiveHandler
        archiver = ArchiveHandler(self.sheets)
        return archiver.run_archive_workflow()
    
    def cleanup_csv(self, csv_path: str):
        """Move processed CSV to archive"""
        processed_dir = Path('data/processed')
        processed_dir.mkdir(exist_ok=True)
        Path(csv_path).rename(processed_dir / Path(csv_path).name)

class ScheduledTaskRunner:
    """Main orchestrator coordinating all phases"""
    
    def __init__(self, config):
        self.config = config
        self.async_collector = None
        self.processor = None
    
    def run_complete_pipeline(self) -> dict:
        """Execute complete pipeline with clean async/sync separation"""
        results = {}
        
        # Phase 1: Async Discord collection (isolated)
        logger.info("Phase 1: Discord Data Collection")
        csv_file = asyncio.run(self.async_collector.collect_to_csv())
        results['csv_file'] = csv_file
        
        # Phase 2-5: Sequential sync processing
        logger.info("Phase 2: CSV to Google Sheets")
        results['sheets'] = self.processor.process_csv_to_sheets(csv_file)
        
        logger.info("Phase 3: Gemini AI Analysis")
        results['ai'] = self.processor.run_gemini_analysis()
        
        logger.info("Phase 4: Publishing")
        results['publishing'] = self.processor.run_publisher()
        
        logger.info("Phase 5: Archive & Cleanup")
        results['archive'] = self.processor.run_archiver()
        self.processor.cleanup_csv(csv_file)
        
        return results

# main.py
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--manual', action='store_true')
    parser.add_argument('--test', action='store_true')
    parser.add_argument('--daemon', action='store_true')
    args = parser.parse_args()
    
    # Validate config
    # Initialize scheduler
    # Run based on mode
```

## Benefits of CSV-Based Architecture

1. **Clean Async/Sync Separation**
   - No event loop conflicts
   - Async Discord operations isolated
   - Sync operations run sequentially without complexity

2. **Data Persistence**
   - CSV files serve as automatic backups
   - Can reprocess CSVs if downstream fails
   - Audit trail of all collected data

3. **Debugging & Testing**
   - Can inspect CSV files directly
   - Test downstream processing with saved CSVs
   - Replay processing without Discord connection

4. **Modularity**
   - Discord collection completely decoupled
   - Each phase can be developed/tested independently
   - Easy to add new processing steps

5. **Error Recovery**
   - If Sheets upload fails, CSV data preserved
   - Can manually process CSV files if needed
   - No data loss even in catastrophic failures

## Success Criteria

1. **Reliability**: Pipeline runs successfully 95%+ of the time
2. **Performance**: Complete pipeline in < 2 minutes
3. **Maintainability**: Clear code structure, comprehensive logging
4. **Usability**: Simple command-line interface, clear documentation
5. **Resilience**: Graceful handling of failures, no data loss
6. **Data Integrity**: CSV backups ensure zero data loss

## Notes

- The scheduler should be the **only** entry point for the application
- All orchestration logic should be contained within the scheduler
- **KEY PRINCIPLE**: Use `asyncio.run()` to isolate Discord async operations, preventing event loop conflicts
- CSV files act as a bridge between async and sync operations
- Keep the implementation simple and maintainable per CLAUDE.md guidelines
- Focus on reliability over complex features
- Ensure comprehensive logging for debugging production issues

## Migration from Current Implementation

### Current Issues:
1. **Event Loop Conflicts**: Mixed async Discord operations with sync processing
2. **Complex Orchestration**: WorkflowOrchestrator adds unnecessary complexity
3. **Hanging Connections**: Discord bot runs in background causing timeouts
4. **Debugging Difficulty**: Hard to trace issues through complex orchestration

### New Architecture Solutions:
1. **Isolated Async**: Discord collection in isolated `asyncio.run()` call
2. **Direct Module Calls**: No workflow_orchestrator, each module called directly
3. **CSV Bridge**: Clean handoff between async and sync phases
4. **Simple Sequential**: Each phase runs to completion before next starts
5. **Transparent Error Handling**: Each module's errors directly visible

### Key Improvements:
- **No WorkflowOrchestrator dependency** - Direct, simple module calls
- **CSV files as data bridge** - Persistent, debuggable data transfer
- **Clean async/sync separation** - No context switching after Discord phase
- **Modular testing** - Each phase can be tested independently