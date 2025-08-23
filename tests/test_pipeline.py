#!/usr/bin/env python3
"""Simple test script to debug the pipeline issue."""

import asyncio
import logging
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

import config
from modules.discord_handler import DiscordHandler
from modules.sheets_handler import GoogleSheetsHandler
from modules.scheduler import DataCollectionOrchestrator

# Setup logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def test_discord_connection():
    """Test Discord connection only."""
    logger.info("Testing Discord connection...")
    
    handler = DiscordHandler(config.DISCORD_TOKEN, config.DISCORD_CHANNEL_ID)
    
    try:
        logger.info("Connecting to Discord...")
        await handler.connect()
        logger.info("Connected successfully!")
        
        logger.info("Fetching messages...")
        messages = await handler.fetch_channel_messages(limit=5)
        logger.info(f"Fetched {len(messages)} messages")
        
        logger.info("Disconnecting...")
        await handler.disconnect()
        logger.info("Disconnected successfully!")
        
        return True
    except Exception as e:
        logger.error(f"Error: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False

async def test_data_collection():
    """Test the data collection orchestrator."""
    logger.info("Testing data collection orchestrator...")
    
    discord_handler = DiscordHandler(config.DISCORD_TOKEN, config.DISCORD_CHANNEL_ID)
    sheets_handler = GoogleSheetsHandler(config.GOOGLE_SERVICE_ACCOUNT_FILE, config.GOOGLE_SHEETS_ID)
    
    config_dict = {
        'DISCORD_COLLECTION_MODE': 'daily',
        'DISCORD_LOOKBACK_DAYS': 1,
        'DISCORD_FETCH_LIMIT': 10,
        'DISCORD_SKIP_DUPLICATES': 'true',
        'SHEETS_BATCH_SIZE': 100
    }
    
    orchestrator = DataCollectionOrchestrator(discord_handler, sheets_handler, config_dict)
    
    try:
        results = await orchestrator.run_data_collection()
        logger.info(f"Results: {results}")
        return results['success']
    except Exception as e:
        logger.error(f"Error: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False

def main():
    """Main test function."""
    logger.info("Starting pipeline test...")
    
    # Test 1: Discord connection
    logger.info("\n" + "="*50)
    logger.info("TEST 1: Discord Connection")
    logger.info("="*50)
    
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    success = loop.run_until_complete(test_discord_connection())
    loop.close()
    
    if not success:
        logger.error("Discord connection test failed!")
        return 1
    
    logger.info("Discord connection test passed!")
    
    # Test 2: Data collection
    logger.info("\n" + "="*50)
    logger.info("TEST 2: Data Collection")
    logger.info("="*50)
    
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    success = loop.run_until_complete(test_data_collection())
    loop.close()
    
    if not success:
        logger.error("Data collection test failed!")
        return 1
    
    logger.info("Data collection test passed!")
    
    logger.info("\n" + "="*50)
    logger.info("All tests passed!")
    return 0

if __name__ == '__main__':
    sys.exit(main())