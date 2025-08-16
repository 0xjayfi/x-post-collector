"""Configuration management for Discord to Google Sheets bot."""

import os
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv

load_dotenv()

# Discord Configuration
DISCORD_TOKEN: Optional[str] = os.getenv('DISCORD_TOKEN')
DISCORD_CHANNEL_ID: Optional[str] = os.getenv('DISCORD_CHANNEL_ID')

# Google Sheets Configuration
GOOGLE_SHEETS_ID: Optional[str] = os.getenv('GOOGLE_SHEETS_ID')
GOOGLE_SERVICE_ACCOUNT_FILE: Optional[str] = os.getenv('GOOGLE_SERVICE_ACCOUNT_FILE', 'credentials.json')
GOOGLE_SHEET_NAME: str = os.getenv('GOOGLE_SHEET_NAME', 'Sheet1')
SHEETS_BATCH_SIZE: int = int(os.getenv('SHEETS_BATCH_SIZE', '100'))

# Schedule Configuration
SCHEDULE_TIME: str = os.getenv('SCHEDULE_TIME', '20:00')

# Logging Configuration
LOG_LEVEL: str = os.getenv('LOG_LEVEL', 'INFO')
LOG_DIR: Path = Path(os.getenv('LOG_DIR', 'logs'))

# Create logs directory if it doesn't exist
LOG_DIR.mkdir(exist_ok=True)

# Validation
def validate_config() -> bool:
    """Validate that all required configuration is present."""
    required_vars = {
        'DISCORD_TOKEN': DISCORD_TOKEN,
        'DISCORD_CHANNEL_ID': DISCORD_CHANNEL_ID,
        'GOOGLE_SHEETS_ID': GOOGLE_SHEETS_ID,
        'GOOGLE_SERVICE_ACCOUNT_FILE': GOOGLE_SERVICE_ACCOUNT_FILE
    }
    
    missing_vars = []
    for var_name, var_value in required_vars.items():
        if not var_value or var_value.startswith('your_'):
            missing_vars.append(var_name)
    
    if missing_vars:
        print(f"Missing or invalid configuration for: {', '.join(missing_vars)}")
        print("Please update your .env file with valid values.")
        return False
    
    # Check if service account file exists
    if GOOGLE_SERVICE_ACCOUNT_FILE and not Path(GOOGLE_SERVICE_ACCOUNT_FILE).exists():
        print(f"Google service account file not found: {GOOGLE_SERVICE_ACCOUNT_FILE}")
        return False
    
    return True

def validate_x_api_config() -> bool:
    """Validate X API configuration if using Twitter publisher."""
    if PUBLISHER_TYPE.lower() != 'twitter':
        return True  # Not using Twitter, no validation needed
    
    required_x_vars = {
        'X_API_KEY': X_API_KEY,
        'X_API_SECRET': X_API_SECRET,
        'X_ACCESS_TOKEN': X_ACCESS_TOKEN,
        'X_ACCESS_TOKEN_SECRET': X_ACCESS_TOKEN_SECRET
    }
    
    missing_x_vars = []
    for var_name, var_value in required_x_vars.items():
        if not var_value or var_value.startswith('your_'):
            missing_x_vars.append(var_name)
    
    if missing_x_vars:
        print(f"Missing or invalid X API configuration for: {', '.join(missing_x_vars)}")
        print("Please update your .env file with valid X API credentials.")
        return False
    
    return True

# Application Configuration
APP_NAME = "Discord to Google Sheets Bot"
VERSION = "1.0.0"
TWITTER_LINK_PATTERNS = [
    r'https?://(?:www\.)?twitter\.com/\S+',
    r'https?://(?:www\.)?x\.com/\S+'
]

# Google Sheets Configuration
SHEET_NAME = "Sheet1"
SHEET_HEADERS = [
    "Date",
    "Time", 
    "Content",
    "Post Link",
    "Author",
    "Author Link"
]

# Rate Limiting
MAX_RETRIES = 3
RETRY_DELAY = 5  # seconds
BATCH_SIZE = 100  # Maximum messages to process at once

# Gemini AI Configuration
GEMINI_API_KEY: Optional[str] = os.getenv('GEMINI_API_KEY')
GEMINI_MODEL: str = os.getenv('GEMINI_MODEL', 'gemini-1.5-flash')
GEMINI_DAILY_LIMIT: int = int(os.getenv('GEMINI_DAILY_LIMIT', '1400'))

# X API Configuration
X_API_KEY: Optional[str] = os.getenv('X_API_KEY')
X_API_SECRET: Optional[str] = os.getenv('X_API_SECRET')
X_ACCESS_TOKEN: Optional[str] = os.getenv('X_ACCESS_TOKEN')
X_ACCESS_TOKEN_SECRET: Optional[str] = os.getenv('X_ACCESS_TOKEN_SECRET')

# Publishing Configuration
PUBLISHER_TYPE: str = os.getenv('PUBLISHER_TYPE', 'twitter')  # 'twitter' or 'typefully'

# Typefully Configuration (alternative to X API)
TYPEFULLY_API_KEY: Optional[str] = os.getenv('TYPEFULLY_API_KEY')
TYPEFULLY_SCHEDULE: str = os.getenv('TYPEFULLY_SCHEDULE', 'next-free-slot')

# Archive Configuration
ARCHIVE_SHEET_NAME: str = os.getenv('ARCHIVE_SHEET_NAME', 'Archive')
ARCHIVE_BATCH_SIZE: int = int(os.getenv('ARCHIVE_BATCH_SIZE', '50'))