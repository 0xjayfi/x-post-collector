# Scheduler Module Implementation Plan

## Overview
The scheduler module will be the main entry point for the application, orchestrating the complete data pipeline from Discord to Archive. It will support both manual triggering and automatic daily scheduling.

## Architecture

### Complete Workflow Chain
```
Discord Channel → Google Sheets → Gemini AI Analysis → Daily Draft Generation → X/Twitter Publishing → Archive System
```

### Module Structure
```
modules/
├── scheduler.py              # Main scheduler module
└── ...existing modules...

main.py                       # Entry point that uses scheduler
```

## Implementation Details

### 1. Scheduler Module (`modules/scheduler.py`)

#### Key Components:

##### A. DataCollectionOrchestrator Class
- Responsible for Discord → Google Sheets pipeline (Steps 1-2)
- Methods:
  - `collect_discord_posts()`: Fetch new posts from Discord
  - `push_to_sheets()`: Upload posts to Google Sheets
  - `run_data_collection()`: Orchestrate Discord to Sheets flow

##### B. ScheduledTaskRunner Class
- Main orchestrator combining data collection and workflow orchestration
- Methods:
  - `run_complete_pipeline()`: Execute full pipeline
  - `run_manual()`: Manual trigger for testing
  - `schedule_daily()`: Set up daily scheduling
  - `start()`: Main daemon loop

#### Core Features:

1. **Discord Data Collection**
   - Connect to Discord using DiscordHandler
   - Fetch posts based on configured time window:
     - `daily` mode: Fetch posts from last N days
     - `hours` mode: Fetch posts from last N hours  
     - `since_last` mode: Fetch posts since last entry in Google Sheets
   - Handle duplicate detection using last entry date from Sheets (if DISCORD_SKIP_DUPLICATES=true)
   - Process Twitter/X links from messages

2. **Google Sheets Integration**
   - Push collected Discord posts to main sheet
   - Ensure headers exist before data upload
   - Handle batch uploads for large datasets
   - Track last processed timestamp to avoid duplicates

3. **Workflow Orchestration Integration**
   - After data collection, call WorkflowOrchestrator
   - Run AI analysis (if Gemini configured)
   - Run publishing (if publisher configured)
   - Run archiving (always)

4. **Scheduling Mechanism**
   - Use `schedule` library for simplicity
   - Support manual trigger via command-line flag
   - Daily execution at configured time (default 20:00)
   - Time interpretation:
     - By default, uses system local timezone
     - Optional SCHEDULE_TIMEZONE to specify timezone (requires `pytz` library)
     - Logs timezone info at startup for clarity
   - Graceful shutdown handling

5. **Error Handling & Resilience**
   - Comprehensive error handling at each step
   - Continue pipeline even if one step fails
   - Detailed logging of all operations
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
1. **Data Collection Phase**
   - Connect to Discord
   - Determine time window based on DISCORD_COLLECTION_MODE:
     - `daily`: Use datetime.now() - timedelta(days=DISCORD_LOOKBACK_DAYS)
     - `hours`: Use datetime.now() - timedelta(hours=DISCORD_LOOKBACK_HOURS)
     - `since_last`: Query Google Sheets for last entry timestamp
   - Fetch messages from channel within time window
   - Filter for Twitter/X links
   - Format as TwitterPost objects
   - Disconnect from Discord

2. **Sheets Upload Phase**
   - Check last entry date in Sheets
   - Filter out duplicates
   - Upload new posts to Sheets
   - Log statistics

3. **Workflow Orchestration Phase**
   - Initialize WorkflowOrchestrator
   - Run AI analysis (optional)
   - Run publishing (optional)
   - Run archiving (required)
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
Data Collection:
  ✅ Fetched 25 Discord messages
  ✅ Found 18 Twitter/X posts
  ✅ Uploaded 15 new posts to Sheets (3 duplicates skipped)

AI Analysis:
  ✅ Analyzed 15 posts
  ✅ Found 5 crypto projects
  ✅ Generated daily draft

Publishing:
  ✅ Published to X/Twitter
  📝 Post ID: 123456789

Archive:
  ✅ Archived 15 processed posts
  📊 Total archived: 1,234 posts

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
class DataCollectionOrchestrator:
    def __init__(self, discord_handler, sheets_handler, config):
        self.discord = discord_handler
        self.sheets = sheets_handler
        self.config = config
    
    async def collect_discord_posts(self):
        # Determine time window based on collection mode
        collection_mode = self.config.get('DISCORD_COLLECTION_MODE', 'daily')
        
        if collection_mode == 'daily':
            lookback_days = int(self.config.get('DISCORD_LOOKBACK_DAYS', 1))
            after = datetime.now() - timedelta(days=lookback_days)
        elif collection_mode == 'hours':
            lookback_hours = int(self.config.get('DISCORD_LOOKBACK_HOURS', 24))
            after = datetime.now() - timedelta(hours=lookback_hours)
        elif collection_mode == 'since_last':
            after = self.sheets.get_last_entry_date() or datetime.now() - timedelta(days=1)
        
        # Fetch posts with configured limit
        limit = int(self.config.get('DISCORD_FETCH_LIMIT', 200))
        return await self.discord.fetch_twitter_posts_with_retry(limit=limit, after=after)
    
    def push_to_sheets(self, posts):
        # Check for duplicates if configured
        if self.config.get('DISCORD_SKIP_DUPLICATES', 'true').lower() == 'true':
            # Filter out existing posts
            pass
        # Implementation
        pass

class ScheduledTaskRunner:
    def __init__(self, config):
        self.config = config
        self.data_collector = None
        self.workflow_orchestrator = None
        self.timezone = self._setup_timezone()
    
    def _setup_timezone(self):
        # Setup timezone for scheduling
        tz_name = self.config.get('SCHEDULE_TIMEZONE')
        if tz_name:
            import pytz
            return pytz.timezone(tz_name)
        else:
            # Use system local timezone
            from datetime import datetime
            logger.info(f"Using system timezone. Current time: {datetime.now()}")
            return None
    
    def run_complete_pipeline(self):
        # Step 1: Data collection
        # Step 2: Workflow orchestration
        pass
    
    def schedule_daily(self):
        # Set up scheduling with timezone awareness
        schedule_time = self.config.get('SCHEDULE_TIME', '20:00')
        schedule.every().day.at(schedule_time).do(self.run_complete_pipeline)
        logger.info(f"Scheduled daily run at {schedule_time} {'UTC' if self.timezone else 'local time'}")
        pass
    
    def start(self):
        # Main daemon loop
        pass

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

## Success Criteria

1. **Reliability**: Pipeline runs successfully 95%+ of the time
2. **Performance**: Complete pipeline in < 2 minutes
3. **Maintainability**: Clear code structure, comprehensive logging
4. **Usability**: Simple command-line interface, clear documentation
5. **Resilience**: Graceful handling of failures, no data loss

## Notes

- The scheduler should be the **only** entry point for the application
- All orchestration logic should be contained within the scheduler
- Keep the implementation simple and maintainable per CLAUDE.md guidelines
- Focus on reliability over complex features
- Ensure comprehensive logging for debugging production issues