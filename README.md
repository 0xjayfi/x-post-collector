# Discord to X/Twitter Auto-Publisher with AI Analysis

A complete automation pipeline that collects crypto/Web3 posts from Discord, analyzes them with AI, publishes summaries to X/Twitter or Typefully, and maintains organized archives in Google Sheets.

## 🎯 Key Features

### Complete Automation Workflow
1. **📥 Discord Collection** - Monitors Discord channels for Twitter/X posts about crypto projects
2. **📊 Google Sheets Storage** - Stores posts in structured spreadsheet format
3. **🤖 AI Analysis** - Uses Gemini AI to identify and summarize new Web3/DeFi/NFT projects
4. **📝 Content Generation** - Creates daily summary drafts of trending projects
5. **📢 Auto Publishing** - Posts to X/Twitter or schedules via Typefully
6. **📚 Smart Archiving** - Moves processed posts to Archives with metadata

### Workflow Pipeline
```
Discord Channel → Google Sheets → Gemini AI Analysis → 
Daily Draft Generation → X/Twitter Publishing → Archive System
```

## ⚡ Quick Start

Once configured, run the complete workflow with a single command:

```bash
# Run the complete automated pipeline
./venv/bin/python test_complete_workflow.py

# Or run individual components:
./venv/bin/python test_discord_integration.py  # Collect from Discord
./venv/bin/python test_gemini_integration.py   # Analyze with AI
./venv/bin/python test_sheet_publishing.py     # Publish to X/Twitter
./venv/bin/python test_archive.py              # Archive processed posts
```

## 🚀 Project Status

### ✅ Completed Components (as of 2025-08-18)

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
   - ✅ Automatic column creation (AI Summary, AI processed, Daily Post Draft)
   - ✅ Non-project posts marked as "Not new project related"
   - ✅ AI processed column tracks all analyzed rows with "TRUE" value
   - ✅ Integration test script with dry-run mode
   - ✅ Fixed sheet update logic for proper column creation

6. **X API Publisher** (`modules/x_publisher.py`)
   - ✅ X API v2 authentication with OAuth 2.0
   - ✅ Tweet publishing with automatic thread creation for long content
   - ✅ Rate limiting (50 posts/day, 5 posts/15min)
   - ✅ Typefully API support with UTC time scheduling
   - ✅ Content validation and formatting
   - ✅ Automatic hashtag addition
   - ✅ Error handling with detailed diagnostics
   - ✅ SheetPublisher wrapper for Google Sheets integration
   - ✅ Automatic "Publication receipt" column creation
   - ✅ Receipt tracking (tweet URLs for X API, draft IDs for Typefully)
   - ✅ Direct publishing from "Daily Post Draft" column
   - ✅ Test scripts: `test_x_api.py` (authentication), `test_sheet_publishing.py` (sheet integration)

7. **Archive Handler** (`modules/archive_handler.py`)
   - ✅ Archives posts marked with "AI processed = TRUE"
   - ✅ Creates Archives sheet with proper headers if it doesn't exist
   - ✅ Extracts only essential columns: date, time, author, post_link, content, AI Summary
   - ✅ Adds metadata: "Date Processed (UTC)" timestamp and "Publication Receipt"
   - ✅ Fills Publication Receipt for all archived rows in batch
   - ✅ Removes archived posts from Sheet1 completely
   - ✅ Clears processing columns (AI Summary, AI processed, Daily Post Draft, Publication receipt)
   - ✅ Appends to existing Archives sheet (preserves historical data)
   - ✅ UTC timestamps for consistent time tracking
   - ✅ Complete workflow integration with error handling

8. **Workflow Orchestrator** (`modules/workflow_orchestrator.py`)
   - ✅ Orchestrates complete pipeline: Analysis → Publishing → Archiving
   - ✅ Supports optional components (Gemini AI, X/Typefully publisher)
   - ✅ Modular design allows running individual steps or complete workflow
   - ✅ Comprehensive error handling and result tracking
   - ✅ Detailed logging for each workflow step
   - ✅ Test scripts: `test_archive.py`, `test_complete_workflow.py`

### 🔄 In Progress / Next Steps

1. **Scheduler** (`modules/scheduler.py`)
   - [ ] Daily run at 20:00 (8 PM) (or a time specified in .env)
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
│   ├── x_publisher.py          ✅ Complete & Tested
│   ├── archive_handler.py      ✅ Complete & Tested
│   ├── workflow_orchestrator.py ✅ Complete & Tested
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
├── test_x_api.py              ✅ X API authentication & permission testing
├── test_sheet_publishing.py   ✅ Sheet-based publishing with receipt tracking
├── test_archive.py            ✅ Archive handler testing & viewer
├── test_complete_workflow.py  ✅ Complete pipeline testing
├── run_tests.py               ✅ Test runner utility
├── plan.md                    ✅ Implementation plans & X API setup guide
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

# X API Configuration (for Twitter publishing)
X_API_KEY=your_x_api_key
X_API_SECRET=your_x_api_secret
X_ACCESS_TOKEN=your_x_access_token
X_ACCESS_TOKEN_SECRET=your_x_access_token_secret

# Typefully API Configuration (alternative to X API)
TYPEFULLY_API_KEY=your_typefully_api_key  # Optional
TYPEFULLY_HOURS_DELAY=8  # Schedule posts X hours from now

# Publishing Configuration
PUBLISHER_TYPE=twitter  # 'twitter' or 'typefully'

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

### X API Setup
1. **Create X Developer Account**
   - Go to [Twitter Developer Portal](https://developer.twitter.com)
   - Apply for developer access
   - Create a Project and App

2. **Configure App Permissions**
   - Go to App Settings → User authentication settings
   - Set **App permissions** to **"Read and write"**
   - Save settings

3. **Generate Credentials**
   - Go to Keys and tokens tab
   - Save API Key and Secret
   - Generate Access Token with Read/Write permissions
   - Save all 4 credentials to `.env`

4. **Test Authentication**
   ```bash
   ./venv/bin/python test_x_api.py
   ```

For detailed X API setup, see [plan.md](./plan.md)

### Archive Workflow

The archive system automatically manages processed posts:

1. **Archive Criteria**
   - Only archives posts marked with `AI processed = TRUE`
   - Preserves essential columns in Archives sheet
   - Adds UTC timestamp and publication receipt

2. **Archives Sheet Structure**
   ```
   - date, time, author, post_link, content (from original)
   - AI Summary (from Gemini analysis)
   - Date Processed (UTC) - when archived
   - Publication Receipt - tweet URL or draft ID
   ```

3. **Running Archive Workflow**
   ```bash
   # Test archive functionality
   ./venv/bin/python test_archive.py
   
   # View archived posts
   # Select option 2 in the test script
   ```

4. **Complete Pipeline**
   ```bash
   # Run full workflow: Analyze → Publish → Archive
   ./venv/bin/python test_complete_workflow.py
   ```

5. **Using in Code**
   ```python
   from modules.archive_handler import ArchiveHandler
   from modules.sheets_handler import GoogleSheetsHandler
   
   # Initialize
   sheets = GoogleSheetsHandler(credentials_path, sheet_id)
   archiver = ArchiveHandler(sheets)
   
   # Run archive workflow
   results = archiver.run_archive_workflow()
   print(f"Archived {results['posts_archived']} posts")
   ```

### Publishing Workflow

1. **Test Publishing from Sheet**
   ```bash
   ./venv/bin/python test_sheet_publishing.py
   ```
   - Interactive script that reads "Daily Post Draft" from your Google Sheet
   - Choose between X API (immediate) or Typefully (scheduled)
   - Automatically updates "Publication receipt" column with:
     - X API: Tweet URL (e.g., `https://twitter.com/username/status/123`)
     - Typefully: Draft ID (e.g., `Typefully Draft: abc123`)

2. **Using in Code**
   ```python
   from modules.x_publisher import create_publisher, SheetPublisher
   from modules.sheets_handler import GoogleSheetsHandler
   
   # Create publisher (X API or Typefully)
   publisher = create_publisher('twitter', **credentials)
   
   # Wrap with SheetPublisher for receipt tracking
   sheets = GoogleSheetsHandler(credentials_path, sheet_id)
   sheet_publisher = SheetPublisher(publisher, sheets)
   
   # Publish from specific row
   result = sheet_publisher.publish_from_sheet(row_number=2)
   ```

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

# X API Integration (Requires X API credentials)
./venv/bin/python test_x_api.py

# Sheet Publishing Integration (Publishes from Google Sheet)
./venv/bin/python test_sheet_publishing.py

# Archive Handler Testing (Archives processed posts)
./venv/bin/python test_archive.py

# Complete Workflow Testing (Full pipeline)
./venv/bin/python test_complete_workflow.py
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

### 5. AI-Powered Analysis
- Gemini AI integration for crypto project detection
- Automatic identification of new Web3/DeFi/NFT projects
- Twitter/X username and link extraction from embedded content
- AI-generated project summaries (concise 1-2 sentences)
- Daily draft creation with formatted project list
- Smart rate limiting for free tier usage
- Non-project posts marked as "Not new project related"
- AI processed column tracks all analyzed rows

### 6. X/Twitter Publishing
- X API v2 integration with OAuth 2.0 authentication
- Automatic thread creation for long content
- Typefully API support for scheduled posting
- SheetPublisher wrapper for Google Sheets integration
- Automatic "Publication receipt" column creation
- Receipt tracking (tweet URLs for X API, draft IDs for Typefully)
- Direct publishing from "Daily Post Draft" column in sheet

### 7. Testing & Validation
- 46 unit tests total (16 Discord + 12 Sheets + 18 Gemini)
- Integration tests for Discord, Google Sheets, Gemini AI, and X API
- Sheet publishing test with interactive mode
- CSV export for manual data inspection
- Test coverage for edge cases and error scenarios
- X API permission diagnostic tool

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

### Phase 1: X (Twitter) Publishing & Archiving
1. **X API Integration** (`modules/x_publisher.py`)
   - ✅ Authenticate with X API v2
   - ✅ Publish Daily Post Draft content
   - ✅ Handle rate limits and errors
   - ✅ Return publication status/URL

2. **Archive System** (`modules/archive_handler.py`)
   - ✅ Move processed posts to Archives sheet
   - ✅ Clear processed posts from Sheet1
   - ✅ Add metadata columns:
     - Date Processed (UTC) - timestamp of archiving
     - Publication Receipt - link to published tweet/draft
   - ✅ Maintain data integrity during transfer

3. **Workflow Integration** (`modules/workflow_orchestrator.py`)
   - ✅ Chain: Analyze → Generate Draft → Publish → Archive
   - ✅ Modular design supporting optional components
   - ✅ Comprehensive error handling and logging

### Phase 2: Scheduling & Automation
1. Implement `scheduler.py` with daily runs
2. Add manual trigger option
3. Create systemd service or cron job
4. Add health checks and monitoring
5. Integrate full workflow (Discord → Sheets → AI → X → Archive)

### Phase 3: Production Deployment
1. Implement proper logging (`utils/logger.py`)
2. Add configuration management
3. Create main orchestration script (`main.py`)
4. Set up error notifications
5. Deploy to server/cloud

### Phase 4: Enhancements
1. Add data deduplication
2. Implement data archiving (monthly sheets)
3. Add analytics/reporting
4. Create web dashboard (optional)
5. Add multiple channel support
6. Multi-language support for summaries
7. Custom AI prompts per project type

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

3. **Next Priority**: 
   - Implement X API publishing for Daily Post Draft
     Or implement Typefully API (below is an example)
   ```python
    import requests
   API_KEY = "XXXXXXXXXXXXXX"
   headers = {"X-API-KEY": f"Bearer {API_KEY}"}
   payload = {
      "content": f"""🚀 New/Trending Projects on 2025-08-11:
   • @CakeshopApp: Cakeshop is an upcoming iOS app, likely offering an easy-to-use interface for a specific crypto-related task.

   • @hyenatrade: No info yet

   • @ZeroCool_AI: This project aims to build AGI-level vulnerability detection to secure all software.

   • @underscore_hq: Underscore offers an AI-powered wallet for automated DeFi across all protocols, using secure AI agent delegation.""",
      "schedule-date": "next-free-slot"
   }
   r = requests.post("https://api.typefully.com/v1/drafts/", headers=headers, json=payload, timeout=30)
   r.raise_for_status()
   print(r.json())
   ```

   - Create archive system to move processed posts
   - Add metadata tracking for processed items

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

*Last Updated: 2025-08-18 by Claude (AI Assistant)*  
*Session Summary: Implemented complete Archive Handler module for managing processed posts. Archives posts marked with "AI processed = TRUE" to Archives sheet with UTC timestamps and publication receipts. Removes archived posts from Sheet1 and clears processing columns. Created Workflow Orchestrator for complete pipeline integration (Analysis → Publishing → Archiving). Added comprehensive test scripts for archive functionality and complete workflow testing. Archives sheet appends data to preserve historical records.*