# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

A Python automation tool that collects Twitter/X posts from a Discord channel and archives them to Google Sheets daily at 08:00 PM. The system is designed to be simple, maintainable, and reliable.

## Core Principles

### 1. Simplicity First
- **Write simple, readable code** - Avoid clever one-liners or complex abstractions
- **Explicit is better than implicit** - Make intentions clear in the code
- **Use descriptive variable names** - `discord_channel` not `ch`, `post_content` not `content`
- **Keep functions small** - Each function should do one thing well (max 20-30 lines)
- **Avoid premature optimization** - Focus on working code first

### 2. Python Best Practices
- Follow **PEP 8** style guide strictly
- Use **type hints** for function signatures
- Prefer **f-strings** for string formatting
- Use **pathlib** for file operations instead of os.path
- Implement **proper logging** instead of print statements
- Handle exceptions at appropriate levels, not everywhere

## Project Structure

```
discord-to-sheets/
├── main.py                 # Entry point - keeps it simple
├── config.py              # Configuration and environment variables
├── requirements.txt       # Project dependencies
├── .env.example          # Example environment variables
├── modules/
│   ├── __init__.py
│   ├── discord_handler.py    # Discord API interactions
│   ├── sheets_handler.py     # Google Sheets API interactions
│   ├── data_processor.py     # Data extraction and formatting
│   └── scheduler.py          # Scheduling logic
├── utils/
│   ├── __init__.py
│   └── logger.py            # Logging configuration
└── tests/
    ├── __init__.py
    ├── test_discord_handler.py
    ├── test_sheets_handler.py
    └── test_data_processor.py
```

## Implementation Guidelines

### Configuration Management
```python
# config.py - Use environment variables, keep secrets safe
import os
from dotenv import load_dotenv

load_dotenv()

DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')
DISCORD_CHANNEL_ID = os.getenv('DISCORD_CHANNEL_ID')
GOOGLE_SHEETS_ID = os.getenv('GOOGLE_SHEETS_ID')
SCHEDULE_TIME = os.getenv('SCHEDULE_TIME', '20:00')  # Default to 8 PM
```

### Module Design

#### Discord Handler
- Keep Discord bot minimal - only fetch messages, don't add complex features
- Use discord.py's built-in methods rather than raw API calls
- Filter Twitter/X links using simple regex: `https://(twitter\.com|x\.com)/`
- Handle rate limits gracefully with exponential backoff

#### Data Processor
- Simple data extraction - no complex parsing unless necessary
- Use dataclasses or TypedDict for structured data:
```python
from dataclasses import dataclass
from datetime import datetime

@dataclass
class TwitterPost:
    date: str  # YYYY-MM-DD format
    time: str  # HH:MM format
    content: str
    post_link: str
    author: str
    author_link: str
```

#### Google Sheets Handler
- Use service account authentication (simpler than OAuth)
- Batch operations when possible to reduce API calls
- Always verify sheet structure before writing

#### Scheduler
- Use `schedule` library for simplicity over complex solutions like Celery
- Run as a simple daemon process
- Include a manual trigger option for testing

### Error Handling Strategy

```python
# Be specific with exceptions, provide context
try:
    posts = await fetch_discord_posts(channel_id)
except discord.HTTPException as e:
    logger.error(f"Failed to fetch Discord posts: {e}")
    # Don't crash - log and continue
    return []
```

### Logging Configuration

```python
# utils/logger.py - Simple, effective logging
import logging
from datetime import datetime

def setup_logger(name: str) -> logging.Logger:
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)
    
    # Console handler for development
    console_handler = logging.StreamHandler()
    
    # File handler for production
    file_handler = logging.FileHandler(
        f'logs/{datetime.now().strftime("%Y%m%d")}.log'
    )
    
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    console_handler.setFormatter(formatter)
    file_handler.setFormatter(formatter)
    
    logger.addHandler(console_handler)
    logger.addHandler(file_handler)
    
    return logger
```

## Dependencies

Keep dependencies minimal and well-maintained:

```txt
# requirements.txt
discord.py>=2.3.0
google-api-python-client>=2.100.0
google-auth>=2.23.0
python-dotenv>=1.0.0
schedule>=1.2.0
```

## Testing Approach

### Unit Tests
- Test each module independently
- Mock external API calls
- Focus on data transformation logic
- Aim for 80% coverage on business logic

### Example Test Structure
```python
# tests/test_data_processor.py
import unittest
from unittest.mock import Mock
from modules.data_processor import extract_twitter_data

class TestDataProcessor(unittest.TestCase):
    def test_extract_twitter_link(self):
        """Test extraction of Twitter/X links from message content"""
        message = Mock()
        message.content = "Check this out: https://twitter.com/user/status/123"
        message.created_at = datetime(2024, 1, 1, 12, 0)
        
        result = extract_twitter_data(message)
        
        self.assertEqual(result.post_link, "https://twitter.com/user/status/123")
        self.assertEqual(result.date, "2024-01-01")
        self.assertEqual(result.time, "12:00")
```

## Security Considerations

1. **Never commit credentials** - Use .env files and .gitignore
2. **Validate Discord channel ID** - Ensure bot only reads from authorized channels
3. **Use read-only Google Sheets scope** when possible, write scope only for target sheet
4. **Implement rate limiting** to avoid API quota issues
5. **Sanitize data** before writing to Google Sheets

## Common Pitfalls to Avoid

1. **Don't overcomplicate the scheduler** - A simple while loop with sleep is fine
2. **Don't store state in memory** - Use Google Sheets as the source of truth
3. **Don't try to parse Twitter embed data** - Just store the link
4. **Don't implement retry logic everywhere** - Only where it matters (API calls)
5. **Don't use async unless necessary** - Sync code is simpler for this use case

## Development Workflow

1. **Start with the simplest working version** - Get basic functionality working first
2. **Add features incrementally** - Don't try to build everything at once
3. **Test manually first** - Use a test Discord channel and test Google Sheet
4. **Add automated tests** after core functionality works
5. **Document as you go** - Update this file with decisions and learnings

## Debugging Tips

- Use `logging.DEBUG` level during development
- Test each module independently via command line before integration
- Use Discord's developer mode to easily get channel IDs
- Test Google Sheets connection with a simple write operation first
- Keep a separate test configuration for development

## Code Style Examples

### Good - Simple and Clear
```python
def format_post_data(message: discord.Message) -> dict:
    """Convert Discord message to Google Sheets row format."""
    created_at = message.created_at
    
    return {
        'date': created_at.strftime('%Y-%m-%d'),
        'time': created_at.strftime('%H:%M'),
        'content': message.content[:500],  # Limit content length
        'post_link': extract_twitter_link(message.content),
        'author': message.author.name,
        'author_link': f"https://discord.com/users/{message.author.id}"
    }
```

### Avoid - Overly Complex
```python
# Don't do this - too clever, hard to debug
data = {k: v for k, v in zip(
    ['date', 'time', 'content', 'post_link', 'author', 'author_link'],
    [*[getattr(m.created_at, f)('%Y-%m-%d' if i == 0 else '%H:%M') 
      for i, f in enumerate(['strftime'] * 2)],
     m.content[:500], extract_link(m.content), m.author.name,
     f"https://discord.com/users/{m.author.id}"]
)}
```

## Final Notes

- **Keep it simple** - This is a straightforward data pipeline, not a complex system
- **Focus on reliability** over features - Better to work consistently than have many features
- **Monitor and log** - You'll thank yourself when debugging production issues
- **Document decisions** - Future you (or others) will appreciate context

Remember: The goal is to build a tool that works reliably every day at 8 PM, not to showcase advanced Python features.  