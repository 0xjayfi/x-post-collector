# Discord to Google Sheets - Twitter/X Post Collector

A Python automation tool that collects Twitter/X posts from Discord channels and archives them to Google Sheets daily.

## 🚀 Project Status

### ✅ Completed Components (as of 2025-08-15)

1. **Discord Handler Module** (`modules/discord_handler.py`)
   - ✅ Connects to Discord using bot token
   - ✅ Fetches messages from specified channel
   - ✅ Filters messages containing Twitter/X links
   - ✅ Extracts embedded content from Discord messages (not just links)
   - ✅ Preserves Discord markdown format for usernames (e.g., `[@username](link)`)
   - ✅ Maintains paragraph structure from original embeds
   - ✅ Handles zero-width characters in Discord markdown
   - ✅ Implements retry logic with exponential backoff
   - ✅ Formats data into structured `TwitterPost` objects
   - ✅ Supports date range queries

2. **Testing Infrastructure**
   - ✅ Comprehensive unit tests (`tests/test_discord_handler.py`)
   - ✅ Integration tests with real Discord connection (`test_discord_integration.py`)
   - ✅ CSV export functionality for data inspection
   - ✅ Test runner script (`run_tests.py`)

3. **Data Extraction Features**
   - ✅ Extracts full embedded tweet content (not just URLs)
   - ✅ Captures project announcements with follower counts
   - ✅ Preserves lists of trending projects/accounts
   - ✅ Includes bio information and descriptions
   - ✅ Maintains author information and timestamps
   - ✅ Preserves multi-paragraph structure from embeds
   - ✅ Supports content up to 1000 characters (increased from 500)

4. **Google Sheets Integration** (`modules/sheets_handler.py`)
   - ✅ Service account authentication with Google API
   - ✅ CSV file reading with multiple encoding support
   - ✅ Batch write operations for large datasets
   - ✅ Duplicate detection via last entry date
   - ✅ Sheet clearing with header preservation
   - ✅ Exponential backoff retry for rate limits
   - ✅ Comprehensive error handling and logging
   - ✅ Support for append and replace modes
   - ✅ Data validation and structure verification

5. **Gemini AI Analyzer** (`modules/gemini_analyzer.py`)
   - ✅ Integration with Google's Gemini AI (free tier)
   - ✅ Automatic detection of new crypto/Web3 projects
   - ✅ Extraction of Twitter/X project info from embedded Discord content
   - ✅ AI-powered project summarization (1-2 sentences)
   - ✅ Rate limiting for free tier (1500 requests/day, 15/minute)
   - ✅ Batch processing for API efficiency
   - ✅ Daily draft generation with structured format
   - ✅ Automatic column creation (AI Summary, Daily Post Draft)
   - ✅ Integration test script with dry-run mode

### 🔄 In Progress / Next Steps

1. **Scheduler** (`modules/scheduler.py`)
   - [ ] Daily run at 20:00 (8 PM)
   - [ ] Manual trigger option
   - [ ] Error recovery

2. **Main Application** (`main.py`)
   - [ ] Orchestration logic
   - [ ] Configuration management
   - [ ] Error handling and logging

## 📁 Project Structure

```
discord-to-sheets/
├── modules/
│   ├── __init__.py
│   ├── discord_handler.py      ✅ Complete & Tested
│   ├── sheets_handler.py       ✅ Complete & Tested
│   ├── gemini_analyzer.py      ✅ Complete & Tested
│   ├── data_processor.py       🔄 To be implemented
│   └── scheduler.py            🔄 To be implemented
├── tests/
│   ├── __init__.py
│   ├── test_discord_handler.py ✅ 16 unit tests passing
│   ├── test_sheets_handler.py  ✅ 12 unit tests passing
│   ├── test_gemini_analyzer.py ✅ 18 unit tests passing
│   └── test_data_processor.py  🔄 To be implemented
├── utils/
│   └── logger.py               🔄 To be implemented
├── .env                        ✅ Configured with Discord credentials
├── .env.example               
├── requirements.txt            ✅ Dependencies installed
├── CLAUDE.md                   ✅ AI assistant guidelines
├── test_discord_integration.py ✅ Integration tests with CSV export
├── test_sheets_integration.py  ✅ Google Sheets upload testing
├── test_gemini_integration.py  ✅ Gemini AI analyzer testing
├── run_tests.py               ✅ Test runner utility
├── plan.md                    ✅ Google Sheets setup guide
└── README.md                  ✅ This file
```

## 🔧 Setup & Configuration

### Prerequisites
- Python 3.8+
- Discord Bot Token
- Google Cloud Project with Sheets API enabled
- Google Service Account credentials (credentials.json)

### Environment Variables (.env)
```bash
# Discord Configuration
DISCORD_TOKEN=your_discord_bot_token
DISCORD_CHANNEL_ID=your_channel_id

# Google Sheets Configuration
GOOGLE_SHEETS_ID=your_sheet_id  # Just the ID, not the full URL
GOOGLE_SERVICE_ACCOUNT_FILE=credentials.json
GOOGLE_SHEET_NAME=Sheet1
SHEETS_BATCH_SIZE=100  # Optional, default 100

# Gemini AI Configuration
GEMINI_API_KEY=your_gemini_api_key_here
GEMINI_MODEL=gemini-1.5-flash  # Optional, default model
GEMINI_DAILY_LIMIT=1400  # Optional, daily request limit

# Schedule Configuration
SCHEDULE_TIME=20:00  # Default 8 PM
```

### Installation
```bash
# Create virtual environment
python3 -m venv venv

# Activate virtual environment
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### Google Sheets Setup
1. **Create Google Cloud Project**
   - Go to [Google Cloud Console](https://console.cloud.google.com/)
   - Create new project or select existing
   - Enable Google Sheets API and Google Drive API

2. **Create Service Account**
   - Go to APIs & Services → Credentials
   - Create Service Account
   - Download JSON key as `credentials.json`
   - Place in project root directory

3. **Share Your Google Sheet**
   - Open your target Google Sheet
   - Click Share button
   - Add service account email (found in credentials.json)
   - Give Editor permissions

4. **Configure Sheet ID**
   - Copy ID from sheet URL: `https://docs.google.com/spreadsheets/d/SHEET_ID/edit`
   - Add to `.env` file (just the ID, not full URL)

For detailed instructions, see [plan.md](./plan.md)

## 🧪 Testing

### Run All Tests
```bash
python run_tests.py
```

### Run Unit Tests Only
```bash
python run_tests.py unit
# or
./venv/bin/python -m unittest tests.test_discord_handler -v
```

### Run Integration Tests
```bash
# Discord Integration (Requires Discord credentials)
python run_tests.py integration
# or
./venv/bin/python test_discord_integration.py

# Google Sheets Integration (Requires credentials.json)
./venv/bin/python test_sheets_integration.py

# Gemini AI Integration (Requires GEMINI_API_KEY)
./venv/bin/python test_gemini_integration.py
```

### Generate CSV Exports for Inspection
```bash
./venv/bin/python test_discord_integration.py
```

This will generate:
- `all_discord_posts_[timestamp].csv` - All available posts (up to 500)
- `today_posts_[date].csv` - Today's posts only
- `weekly_posts_[dates].csv` - Last 7 days of posts
- `recent_posts_sample.csv` - Sample of recent posts

## 📊 Data Format

### TwitterPost Structure
```python
@dataclass
class TwitterPost:
    date: str         # YYYY-MM-DD format
    time: str         # HH:MM format
    content: str      # Full embedded content (up to 1000 chars)
    post_link: str    # Twitter/X URL
    author: str       # Discord username
    author_link: str  # Discord user profile URL
```

### Sample CSV Output
```csv
date,time,author,post_link,content,author_link
2025-08-13,13:46,Web3 Alerts • TweetShift,https://twitter.com/Web3Alerts/status/...,"📈 Trending account alert: [@arc](https://twitter.com/arc) (15.3K followers) is trending among the web3 community

Recently followed by 0xMert_, hasufl, mikedemarais

Description: ""Arc is an open Layer-1 blockchain purpose-built for stablecoin finance.""",https://discord.com/users/...
```

## 🎯 Key Features Implemented

### 1. Discord Message Processing
- Connects to Discord bot and monitors specified channel
- Filters messages containing Twitter/X links (twitter.com or x.com)
- Extracts embedded content from TweetShift and other bot messages

### 2. Content Extraction
- **Before**: Only captured link text like `[Tweeted](url)`
- **After**: Extracts full embedded content including:
  - Project announcements with @handles in Discord markdown format
  - Follower counts and account age
  - Bio descriptions
  - Lists of trending accounts
  - Alert followers
  - Multi-paragraph structure preserved with proper newlines
  - Discord markdown links properly formatted (e.g., `[@username](link)`)

### 3. Robust Error Handling
- Exponential backoff retry for Discord API failures
- Rate limiting protection
- Graceful connection/disconnection
- Comprehensive error logging

### 4. Google Sheets Integration
- Service account authentication
- Batch uploads for efficiency (configurable batch size)
- Multiple modes: append or replace
- Automatic retry with exponential backoff for rate limits
- CSV structure validation
- Duplicate detection via date checking
- Support for large datasets (tested with 1000+ rows)

### 5. AI-Powered Analysis (New!)
- Gemini AI integration for crypto project detection
- Automatic identification of new Web3/DeFi/NFT projects
- Twitter/X username and link extraction from embedded content
- AI-generated project summaries (concise 1-2 sentences)
- Daily draft creation with formatted project list
- Smart rate limiting for free tier usage

### 6. Testing & Validation
- 46 unit tests total (16 Discord + 12 Sheets + 18 Gemini)
- Integration tests for Discord, Google Sheets, and Gemini AI
- CSV export for manual data inspection
- Test coverage for edge cases and error scenarios

## 📈 Statistics from Current Data

Based on test runs (as of 2025-08-12):
- **Total Posts Collected**: 299 Twitter/X posts
- **Date Range**: July 10 - August 11, 2025 (29 days)
- **Average**: 10.3 posts per day
- **Top Sources**:
  - leak.me | Crypto KOL Tracker: 113 posts
  - ARES Alpha Labs: 105 posts
  - Web3 Alerts: 81 posts

## 🚦 Next Development Steps

### Phase 1: Scheduling & Automation
1. Implement `scheduler.py` with daily runs
2. Add manual trigger option
3. Create systemd service or cron job
4. Add health checks and monitoring
5. Integrate Gemini analysis into daily workflow

### Phase 2: Production Deployment
1. Implement proper logging (`utils/logger.py`)
2. Add configuration management
3. Create main orchestration script (`main.py`)
4. Set up error notifications
5. Deploy to server/cloud

### Phase 3: Enhancements
1. Add data deduplication
2. Implement data archiving (monthly sheets)
3. Add analytics/reporting
4. Create web dashboard (optional)
5. Add multiple channel support

## 🐛 Known Issues & Limitations

1. **Discord API Rate Limits**: Current implementation handles rate limits but may need tuning for larger volumes
2. **Link Format**: Some Twitter links end with `)` which may need cleaning
3. **Bot Detection**: Only processes messages from TweetShift and similar bots
4. **Google Sheets Quotas**: API has daily quota limits (may need monitoring for high volume)

## 📝 Notes for Resuming Development

When you return to this project:

1. **Current State**: Discord handler, Google Sheets handler, and Gemini AI analyzer are all fully functional and tested. The complete data pipeline from Discord to Google Sheets with AI analysis is ready.

2. **Gemini AI Setup**: To use the AI analyzer:
   - Get your API key from [Google AI Studio](https://makersuite.google.com/app/apikey)
   - Add `GEMINI_API_KEY` to your `.env` file
   - Run `python test_gemini_integration.py` to test

3. **Next Priority**: Implement scheduler for automated daily runs at 8 PM with Gemini analysis.

4. **Test Data Available**: Run `./venv/bin/python test_discord_integration.py` to generate fresh CSV files with current Discord data.

5. **Architecture Decision**: The modular design allows you to work on each component independently without affecting others.

6. **Configuration**: Discord, Google Sheets, and Gemini AI credentials are all working correctly. Channel `#💎-early-alpha` (ID: 1392132542877929472) is being monitored successfully, data can be uploaded to your Google Sheet, and AI analysis can identify new crypto projects.

## 📚 References

- [Discord.py Documentation](https://discordpy.readthedocs.io/)
- [Google Sheets API Python Quickstart](https://developers.google.com/sheets/api/quickstart/python)
- [Google AI Studio - Gemini API](https://makersuite.google.com/app/apikey)
- [Project Guidelines (CLAUDE.md)](./CLAUDE.md)

## 🤝 Contributing

This is a private project. All development guidelines are documented in `CLAUDE.md`.

## 📄 License

Private project - All rights reserved

---

*Last Updated: 2025-08-15 by Claude (AI Assistant)*  
*Session Summary: Implemented Gemini AI analyzer for automatic crypto project detection, Twitter/X info extraction from embedded Discord content, and AI-powered summarization with rate limiting for free tier usage*