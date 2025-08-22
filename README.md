# Discord to Google Sheets Bot

An automated pipeline that collects Twitter/X posts from Discord channels and processes them through a complete workflow: collection, AI analysis, publishing, and archiving.

## 🚀 Features

- **Discord Data Collection**: Automatically fetch Twitter/X posts from specified Discord channels
- **Google Sheets Integration**: Store and manage posts in Google Sheets
- **AI Analysis**: Analyze posts using Google's Gemini AI to identify crypto projects and generate summaries
- **Automated Publishing**: Publish daily summaries to X/Twitter or Typefully
- **Archive System**: Automatically archive processed posts with publication tracking
- **Flexible Scheduling**: Run manually or on a daily schedule with timezone support

## 📋 Architecture

```
Discord Channel → CSV File → Google Sheets → Gemini AI Analysis → Daily Draft Generation → X/Twitter Publishing → Archive System
```

### Key Architecture Features

- **CSV Intermediate Storage**: Discord data is first saved to CSV files for reliability
- **Clean Async/Sync Separation**: Discord operations run in isolated async context
- **Sequential Processing**: Modules are called directly in sequence (no complex orchestration)
- **Individual Row Analysis**: Gemini AI processes rows one at a time with delays to avoid rate limits

### Modules

- **`discord_handler.py`**: Fetches Twitter/X posts from Discord channels
- **`sheets_handler.py`**: Manages Google Sheets operations (read/write)
- **`gemini_analyzer.py`**: AI-powered post analysis and summarization
- **`x_publisher.py`**: Publishes content to X/Twitter or Typefully
- **`archive_handler.py`**: Archives processed posts with metadata
- **`workflow_orchestrator.py`**: Orchestrates the AI → Publishing → Archive flow
- **`scheduler.py`**: Main scheduler for the complete pipeline
- **`main.py`**: Entry point with CLI interface

## 🛠️ Installation

### Prerequisites

- Python 3.8+
- Discord Bot Token
- Google Cloud Service Account
- Google Sheets API enabled
- (Optional) Gemini AI API key
- (Optional) X/Twitter API credentials or Typefully API key

### Setup

1. **Clone the repository**:
```bash
git clone https://github.com/yourusername/discord-to-sheets.git
cd discord-to-sheets
```

2. **Create virtual environment**:
```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. **Install dependencies**:
```bash
pip install -r requirements.txt
```

4. **Set up Discord Bot**:
   - Go to [Discord Developer Portal](https://discord.com/developers/applications)
   - Create a new application and bot
   - Copy the bot token
   - Add bot to your server with "Read Messages" and "Read Message History" permissions

5. **Set up Google Sheets API**:
   - Go to [Google Cloud Console](https://console.cloud.google.com)
   - Create a new project or select existing
   - Enable Google Sheets API
   - Create a service account and download the JSON key as `credentials.json`
   - Share your Google Sheet with the service account email

6. **Configure environment variables**:
```bash
cp .env.example .env
# Edit .env with your credentials
```

## ⚙️ Configuration

### Required Configuration

```env
# Discord
DISCORD_TOKEN=your_discord_bot_token
DISCORD_CHANNEL_ID=your_channel_id

# Google Sheets
GOOGLE_SHEETS_ID=your_sheet_id
GOOGLE_SERVICE_ACCOUNT_FILE=credentials.json
```

### Optional Configuration

```env
# Scheduling (default: 20:00 local time)
SCHEDULE_TIME=20:00
SCHEDULE_TIMEZONE=UTC  # Optional: specify timezone

# Discord Collection
DISCORD_COLLECTION_MODE=daily  # Options: daily, hours, since_last
DISCORD_LOOKBACK_DAYS=1        # For 'daily' mode
DISCORD_LOOKBACK_HOURS=24      # For 'hours' mode
DISCORD_FETCH_LIMIT=200        # Max messages per run
DISCORD_SKIP_DUPLICATES=true   # Check for existing posts

# Gemini AI (optional)
GEMINI_API_KEY=your_gemini_api_key
GEMINI_MODEL=gemini-2.0-flash-lite  # Latest model for better performance
GEMINI_DAILY_LIMIT=190              # Conservative limit for free tier
SKIP_AI_ON_RATE_LIMIT=true         # Continue pipeline if rate limited

# Publishing (optional)
PUBLISHER_TYPE=twitter  # or 'typefully'

# For X/Twitter
X_API_KEY=your_x_api_key
X_API_SECRET=your_x_api_secret
X_ACCESS_TOKEN=your_x_access_token
X_ACCESS_TOKEN_SECRET=your_x_access_token_secret

# For Typefully
TYPEFULLY_API_KEY=your_typefully_api_key
TYPEFULLY_HOURS_DELAY=0

# Archive
ARCHIVE_SHEET_NAME=Archive
ARCHIVE_BATCH_SIZE=50
```

### Collection Modes

- **`daily`**: Collect posts from the last N days
- **`hours`**: Collect posts from the last N hours
- **`since_last`**: Collect posts since the last entry in Google Sheets

## 🎮 Usage

### Test Configuration

Validate your setup before running:

```bash
python main.py --test
```

This will test:
- Discord connection
- Google Sheets access
- Gemini AI (if configured)
- Publishing credentials (if configured)

### Manual Execution

Run the pipeline once immediately:

```bash
python main.py --manual
```

With debug logging:

```bash
python main.py --manual --debug
```

### Scheduled Daemon

Run as a daemon with daily scheduling:

```bash
python main.py --daemon
# or simply
python main.py
```

The bot will run daily at the time specified in `SCHEDULE_TIME`.

### Command-Line Options

```
usage: main.py [-h] [--manual] [--test] [--daemon] [--debug]

options:
  -h, --help  show this help message and exit
  --manual    Run the pipeline once immediately and exit
  --test      Test mode - validate configuration and connections
  --daemon    Run as daemon with scheduled execution (default)
  --debug     Enable debug logging
```

## 📊 Google Sheets Structure

### Main Sheet (Sheet1)

The main sheet should have these columns:

| Date | Time | Content | Post Link | Author | Author Link | AI Summary | AI Processed | Daily Post Draft | Publication Receipt |
|------|------|---------|-----------|--------|-------------|------------|--------------|------------------|-------------------|

### Archive Sheet

Processed posts are moved to an archive sheet with:
- Essential columns: date, time, author, post_link, content, AI Summary
- Metadata: Date Processed (UTC), Publication Receipt

## 🔄 Complete Workflow

### 1. Discord Collection Phase
- Connect to Discord bot
- Fetch messages from specified channel within configured time window
- Filter for Twitter/X links
- Extract embedded content (up to 1000 characters)
- Format as TwitterPost objects

### 2. Sheets Upload Phase
- Check for existing entries (if duplicate checking enabled)
- Filter duplicates based on post links
- Upload new posts to Google Sheets
- Batch operations for efficiency

### 3. AI Analysis Phase (Optional - requires Gemini API)
- Analyze posts individually (not in batches) for better rate limit handling
- 6-second delay between API calls to avoid rate limiting
- Identify crypto/Web3 projects using AI
- Generate AI summaries (1-2 sentences) for new projects
- Mark all analyzed posts as "AI processed" 
- Posts not identified as projects marked as "Not new project related"
- Create daily draft post with consolidated project list

### 4. Publishing Phase (Optional - requires X/Typefully API)
- Read "Daily Post Draft" from sheet
- Publish to X/Twitter (immediate) or Typefully (scheduled)
- Track publication receipt (tweet URL or draft ID)
- Update sheet with receipt

### 5. Archive Phase
- Move posts marked as "AI processed = TRUE" to Archive sheet
- Add UTC timestamp for processing date
- Preserve publication receipts
- Clear processed posts from main sheet

## 📝 Logging

Logs are stored in the `logs/` directory with daily rotation:
- `YYYYMMDD.log` - Daily log files
- Console output for real-time monitoring

Log levels:
- `INFO`: Normal operations
- `WARNING`: Recoverable issues
- `ERROR`: Failures requiring attention
- `DEBUG`: Detailed troubleshooting

### Sample Pipeline Output

```
================================================================================
Daily Pipeline Run - 2024-01-15 20:00:00 (PST)
================================================================================
Phase 1: Discord Data Collection (Async)
  ✅ Fetched 25 Discord messages
  ✅ Found 18 Twitter/X posts
  ✅ Saved to: data/discord_posts_20240115_200000.csv

Phase 2: CSV to Google Sheets (Sync)
  ✅ Uploaded 15 new posts to Sheets (3 duplicates skipped)

Phase 3: Gemini AI Analysis (Sync)
  ✅ Analyzed 15 posts individually
  ✅ Found 5 crypto projects
  ✅ Generated daily draft
  ⏱️  Analysis time: ~90-180 seconds (6s delay per row)

Phase 4: Publishing (Sync)
  ✅ Published to X/Twitter
  📝 Post ID: 123456789

Phase 5: Archive & Cleanup (Sync)
  ✅ Archived 15 processed posts
  📊 Total archived: 1,234 posts
  ✅ CSV moved to: data/processed/

Overall Status: ✅ SUCCESS
Runtime: 2-3 minutes (depending on number of posts)
================================================================================
```

### Performance Notes

- **AI Analysis Speed**: With individual row processing and 6-second delays, expect ~6-12 seconds per post
- **Total Runtime**: For 20 posts, expect 2-4 minutes total runtime
- **Rate Limit Safety**: The 6-second delays ensure staying well within Gemini's 15 requests/minute limit

## 🧪 Testing

### Test Individual Components

```bash
# Test Discord collection
./venv/bin/python test_discord_integration.py

# Test Google Sheets integration
./venv/bin/python test_sheets_integration.py

# Test Gemini AI analysis
./venv/bin/python test_gemini_integration.py

# Test individual row analyzer (new)
./venv/bin/python test_individual_analyzer.py

# Test batch analyzer optimization
./venv/bin/python test_batch_analyzer.py

# Test X/Twitter publishing
./venv/bin/python test_x_api.py
./venv/bin/python test_sheet_publishing.py

# Test archive system
./venv/bin/python test_archive.py

# Test complete workflow
./venv/bin/python test_complete_workflow.py
```

### Run Unit Tests

```bash
# Run all unit tests
python run_tests.py

# Run specific module tests
./venv/bin/python -m unittest tests.test_discord_handler -v
./venv/bin/python -m unittest tests.test_sheets_handler -v
./venv/bin/python -m unittest tests.test_gemini_analyzer -v
```

## 📁 Project Structure

```
discord-to-sheets/
├── main.py                    # Entry point with CLI
├── config.py                  # Configuration management
├── requirements.txt           # Dependencies
├── .env.example              # Environment template
├── credentials.json          # Google service account key
├── scheduler_plan.md         # Scheduler implementation plan
├── modules/
│   ├── discord_handler.py    # Discord operations
│   ├── sheets_handler.py     # Google Sheets operations
│   ├── gemini_analyzer.py    # AI analysis
│   ├── x_publisher.py        # Publishing functionality
│   ├── archive_handler.py    # Archive management
│   ├── workflow_orchestrator.py  # Workflow orchestration
│   └── scheduler.py          # Main scheduler
├── utils/
│   └── logger.py            # Logging configuration
├── tests/                   # Unit tests
│   ├── test_discord_handler.py
│   ├── test_sheets_handler.py
│   └── test_gemini_analyzer.py
└── logs/                    # Log files (auto-created)
```

## 🚨 Troubleshooting

### Common Issues

1. **Discord Bot Not Connecting**
   - Verify bot token is correct
   - Ensure bot has proper permissions
   - Check bot is added to server

2. **Google Sheets Access Denied**
   - Verify service account has edit access to sheet
   - Check credentials file path
   - Ensure Sheets API is enabled

3. **Duplicate Posts**
   - Enable `DISCORD_SKIP_DUPLICATES=true`
   - Use `since_last` collection mode
   - Check sheet for existing entries

4. **Publishing Failures**
   - Verify API credentials
   - Check rate limits
   - Review publication receipt column

5. **Gemini AI Rate Limiting**
   - The system now uses individual row processing with 6-second delays
   - If still rate limited, increase delays in gemini_analyzer.py
   - Set SKIP_AI_ON_RATE_LIMIT=true to continue pipeline when rate limited
   - Consider reducing GEMINI_DAILY_LIMIT to leave buffer

### Debug Mode

Run with `--debug` flag for detailed logging:

```bash
python main.py --manual --debug
```

## 🔐 Security Best Practices

- Never commit `.env` file or `credentials.json`
- Use environment variables for all sensitive data
- Rotate API keys regularly
- Limit bot permissions to required channels only
- Use read-only Google Sheets scope where possible
- Store credentials securely

## 📈 API Rate Limits

### Discord
- 50 requests per second per bot
- Implemented exponential backoff for rate limit handling

### Google Sheets
- 100 requests per 100 seconds per user
- Batch operations to minimize API calls

### Gemini AI (Free Tier)
- 1,500 requests per day
- 15 requests per minute
- Individual row processing with 6-second delays between API calls
- Automatic rate limit detection and graceful handling
- Supports gemini-2.0-flash-lite model for improved performance

### X/Twitter
- 50 posts per day
- 5 posts per 15 minutes
- Rate limit tracking in publisher

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Follow guidelines in `CLAUDE.md`
4. Add tests for new features
5. Submit a pull request

## 📄 License

MIT License - see LICENSE file for details

## 🙏 Acknowledgments

- Discord.py for Discord API wrapper
- Google APIs for Sheets integration
- Google Gemini for AI analysis
- Tweepy for X/Twitter integration
- Schedule library for task scheduling

## 📮 Support

For issues, questions, or suggestions:
- Open an issue on GitHub
- Check existing issues for solutions
- Review logs for error details

---

**Note**: This bot is designed for personal/research use. Ensure compliance with Discord, Twitter/X, and Google's Terms of Service when deploying.

## 📊 Current Implementation Status

### ✅ Completed Components

1. **Core Modules**
   - Discord Handler: Full Twitter/X post extraction with embedded content
   - Sheets Handler: Batch operations with retry logic
   - Gemini Analyzer: AI-powered project detection with individual row processing
   - X Publisher: Twitter and Typefully API integration
   - Archive Handler: Automated post archiving with metadata
   - Workflow Orchestrator: Complete pipeline orchestration
   - Scheduler: Flexible scheduling with multiple collection modes

2. **Entry Point**
   - Main.py: CLI interface with multiple run modes
   - Config.py: Comprehensive configuration management
   - Logger: Daily rotating log files

3. **Testing**
   - 46+ unit tests across all modules
   - Integration tests for each component
   - Complete workflow testing scripts
   - Individual row analyzer test suite
   - Rate limit handling tests

### 🎯 Ready for Production

The bot is fully functional and ready for deployment. All core features have been implemented and tested:

- ✅ Automated daily scheduling
- ✅ Manual execution mode
- ✅ Complete data pipeline
- ✅ Error handling and recovery
- ✅ Comprehensive logging
- ✅ Flexible configuration

Start collecting, analyzing, and publishing your Discord Twitter/X posts today!

## 📝 Recent Updates

### Version 2.0.0 (2025-08-22)

**Major Architecture Changes:**
- 🔄 **Redesigned Scheduler**: Clean separation of async Discord operations and sync processing
- 📁 **CSV Intermediate Storage**: Discord data saved to CSV files before processing
- 🎯 **Individual Row Processing**: Replaced batch analysis with one-by-one processing
- ⏱️ **Rate Limit Protection**: Added 6-second delays between Gemini API calls
- 🚀 **Model Upgrade**: Now supports gemini-2.0-flash-lite for better performance

**Improvements:**
- Better error handling and recovery from rate limits
- More reliable pipeline execution with isolated async contexts
- Simplified architecture removing complex orchestration layers
- Enhanced logging for debugging rate limit issues

**Configuration Updates:**
- Added `SKIP_AI_ON_RATE_LIMIT` option to continue pipeline when rate limited
- Updated default model to `gemini-2.0-flash-lite`
- Reduced default daily limit to 190 requests for safety buffer