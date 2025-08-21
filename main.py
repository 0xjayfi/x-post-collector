#!/usr/bin/env python3
"""
Discord to Google Sheets Bot - Main Entry Point

This script provides the command-line interface for running the bot
in various modes: manual, test, or daemon.
"""

import argparse
import logging
import sys
from pathlib import Path

# Add project root to path for imports
sys.path.insert(0, str(Path(__file__).parent))

import config
from utils.logger import setup_logger
from modules.scheduler import ScheduledTaskRunner


def validate_configuration() -> bool:
    """
    Validate that all required configuration is present.
    
    Returns:
        True if configuration is valid, False otherwise
    """
    # Check core configuration
    if not config.validate_config():
        return False
    
    # Log configuration status
    logger = logging.getLogger(__name__)
    logger.info("Configuration validated successfully")
    
    # Log optional features status
    if config.GEMINI_API_KEY:
        logger.info("✓ Gemini AI analysis enabled")
    else:
        logger.info("○ Gemini AI analysis disabled (no API key)")
    
    # Check publisher configuration
    publisher_type = config.PUBLISHER_TYPE.lower() if config.PUBLISHER_TYPE else ''
    
    if publisher_type == 'twitter' or publisher_type == 'x':
        if config.validate_x_api_config():
            logger.info("✓ X/Twitter publishing enabled")
        else:
            logger.info("○ X/Twitter publishing disabled (missing credentials)")
    elif publisher_type == 'typefully':
        if config.validate_typefully_config():
            logger.info("✓ Typefully publishing enabled")
        else:
            logger.info("○ Typefully publishing disabled (missing credentials)")
    else:
        logger.info("○ Publishing disabled (no publisher configured)")
    
    return True


def build_config_dict() -> dict:
    """
    Build configuration dictionary from config module.
    
    Returns:
        Dictionary with all configuration values
    """
    return {
        # Discord
        'DISCORD_TOKEN': config.DISCORD_TOKEN,
        'DISCORD_CHANNEL_ID': config.DISCORD_CHANNEL_ID,
        
        # Google Sheets
        'GOOGLE_SHEETS_ID': config.GOOGLE_SHEETS_ID,
        'GOOGLE_SERVICE_ACCOUNT_FILE': config.GOOGLE_SERVICE_ACCOUNT_FILE,
        'GOOGLE_SHEET_NAME': config.GOOGLE_SHEET_NAME,
        'SHEETS_BATCH_SIZE': config.SHEETS_BATCH_SIZE,
        
        # Scheduling
        'SCHEDULE_TIME': config.SCHEDULE_TIME,
        'SCHEDULE_TIMEZONE': getattr(config, 'SCHEDULE_TIMEZONE', None),
        
        # Discord Collection
        'DISCORD_COLLECTION_MODE': getattr(config, 'DISCORD_COLLECTION_MODE', 'daily'),
        'DISCORD_LOOKBACK_HOURS': getattr(config, 'DISCORD_LOOKBACK_HOURS', 24),
        'DISCORD_LOOKBACK_DAYS': getattr(config, 'DISCORD_LOOKBACK_DAYS', 1),
        'DISCORD_FETCH_LIMIT': getattr(config, 'DISCORD_FETCH_LIMIT', 200),
        'DISCORD_SKIP_DUPLICATES': getattr(config, 'DISCORD_SKIP_DUPLICATES', 'true'),
        
        # Gemini AI
        'GEMINI_API_KEY': config.GEMINI_API_KEY,
        'GEMINI_MODEL': config.GEMINI_MODEL,
        
        # Publishing
        'PUBLISHER_TYPE': config.PUBLISHER_TYPE,
        'X_API_KEY': config.X_API_KEY,
        'X_API_SECRET': config.X_API_SECRET,
        'X_ACCESS_TOKEN': config.X_ACCESS_TOKEN,
        'X_ACCESS_TOKEN_SECRET': config.X_ACCESS_TOKEN_SECRET,
        'TYPEFULLY_API_KEY': config.TYPEFULLY_API_KEY,
        'TYPEFULLY_HOURS_DELAY': config.TYPEFULLY_HOURS_DELAY,
        
        # Archive
        'ARCHIVE_SHEET_NAME': config.ARCHIVE_SHEET_NAME,
        'ARCHIVE_BATCH_SIZE': config.ARCHIVE_BATCH_SIZE,
    }


def run_test_mode():
    """Run in test mode to validate configuration and connections."""
    logger = logging.getLogger(__name__)
    logger.info("Running in TEST mode")
    logger.info("="*60)
    
    # Test Discord connection
    logger.info("Testing Discord connection...")
    try:
        import asyncio
        from modules.discord_handler import DiscordHandler
        
        handler = DiscordHandler(config.DISCORD_TOKEN, config.DISCORD_CHANNEL_ID)
        
        async def test_discord():
            await handler.connect()
            logger.info("✓ Discord connection successful")
            await handler.disconnect()
        
        asyncio.run(test_discord())
    except Exception as e:
        logger.error(f"✗ Discord connection failed: {e}")
    
    # Test Google Sheets connection
    logger.info("\nTesting Google Sheets connection...")
    try:
        from modules.sheets_handler import GoogleSheetsHandler
        
        sheets = GoogleSheetsHandler(
            config.GOOGLE_SERVICE_ACCOUNT_FILE,
            config.GOOGLE_SHEETS_ID
        )
        
        # Try to get sheet data
        data = sheets.get_sheet_data()
        logger.info(f"✓ Google Sheets connection successful (found {len(data)} rows)")
    except Exception as e:
        logger.error(f"✗ Google Sheets connection failed: {e}")
    
    # Test Gemini if configured
    if config.GEMINI_API_KEY:
        logger.info("\nTesting Gemini AI connection...")
        try:
            from modules.gemini_analyzer import GeminiAnalyzer
            
            gemini = GeminiAnalyzer(api_key=config.GEMINI_API_KEY)
            logger.info("✓ Gemini AI connection successful")
        except Exception as e:
            logger.error(f"✗ Gemini AI connection failed: {e}")
    
    logger.info("="*60)
    logger.info("Test mode complete")


def main():
    """Main entry point for the application."""
    # Parse command line arguments
    parser = argparse.ArgumentParser(
        description='Discord to Google Sheets Bot - Collect Twitter/X posts and archive them'
    )
    
    parser.add_argument(
        '--manual',
        action='store_true',
        help='Run the pipeline once immediately and exit'
    )
    
    parser.add_argument(
        '--test',
        action='store_true',
        help='Test mode - validate configuration and connections'
    )
    
    parser.add_argument(
        '--daemon',
        action='store_true',
        help='Run as daemon with scheduled execution (default)'
    )
    
    parser.add_argument(
        '--debug',
        action='store_true',
        help='Enable debug logging'
    )
    
    args = parser.parse_args()
    
    # If no mode specified, default to daemon
    if not args.manual and not args.test:
        args.daemon = True
    
    # Setup logging
    log_level = logging.DEBUG if args.debug else getattr(logging, config.LOG_LEVEL)
    logger = setup_logger(__name__)
    logger.setLevel(log_level)
    
    # Log startup info
    logger.info(f"{config.APP_NAME} v{config.VERSION}")
    logger.info("="*60)
    
    # Validate configuration
    if not validate_configuration():
        logger.error("Configuration validation failed. Please check your .env file.")
        sys.exit(1)
    
    # Run in requested mode
    if args.test:
        run_test_mode()
        
    elif args.manual:
        logger.info("Running in MANUAL mode (one-time execution)")
        
        config_dict = build_config_dict()
        runner = ScheduledTaskRunner(config_dict)
        
        results = runner.run_manual()
        
        if not results.get('overall_success', False):
            logger.error("Pipeline execution failed")
            sys.exit(1)
        else:
            logger.info("Pipeline execution completed successfully")
            
    elif args.daemon:
        logger.info("Running in DAEMON mode (scheduled execution)")
        logger.info(f"Pipeline will run daily at {config.SCHEDULE_TIME}")
        
        config_dict = build_config_dict()
        runner = ScheduledTaskRunner(config_dict)
        
        try:
            runner.start()
        except KeyboardInterrupt:
            logger.info("Daemon stopped by user")
        except Exception as e:
            logger.error(f"Daemon error: {e}")
            sys.exit(1)


if __name__ == '__main__':
    main()