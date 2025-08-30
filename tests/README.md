# Test Scripts Documentation

This directory contains all test scripts for the Discord-to-Sheets automation project.

## Test Categories

### Unit Tests
- `test_discord_handler.py` - Tests for Discord API interactions
- `test_sheets_handler.py` - Tests for Google Sheets API operations
- `test_gemini_analyzer.py` - Tests for Gemini AI analysis module

### Integration Tests
- `test_discord_integration.py` - Tests Discord bot connectivity and message fetching
- `test_sheets_integration.py` - Tests Google Sheets API authentication and operations
- `test_gemini_integration.py` - Tests Gemini API integration
- `test_typefully_api.py` - Tests Typefully API integration
- `test_x_api.py` - Tests X (Twitter) API integration

### Workflow Tests
- `test_complete_workflow.py` - End-to-end workflow testing from analysis to archiving 
- `test_pipeline.py` - Data pipeline testing
- `test_batch_analyzer.py` - Batch Gemini analysis testing
- `test_individual_analyzer.py` - Individual row Gemini analysis testing

### Utility Tests
- `test_archive.py` - Archive functionality testing
- `test_sheet_publishing.py` - Sheet publishing workflow testing
- `test_embed_extraction.py` - Discord embed extraction testing
- `test_typefully_debug.py` - Typefully debugging utilities

### Debug Tools
- `debug_message_structure.py` - Debug tool for analyzing Discord message structures
- `run_tests.py` - Test runner script

## Running Tests

### Run All Tests
```bash
# From project root
python tests/run_tests.py

# Or using unittest directly
python -m unittest discover tests
```

### Run Individual Test Files
```bash
# Run specific test file
python -m unittest tests.test_discord_handler
python -m unittest tests.test_sheets_handler
```

### Run Integration Tests
```bash
# Discord integration test
python tests/test_discord_integration.py

# Sheets integration test  
python tests/test_sheets_integration.py

# Gemini integration test
python tests/test_gemini_integration.py
```

### Run Workflow Tests
```bash
# Complete workflow test
python tests/test_complete_workflow.py

# Pipeline test
python tests/test_pipeline.py

# Batch analyzer test
python tests/test_batch_analyzer.py

# Individual analyzer test
python tests/test_individual_analyzer.py
```

## Environment Setup

Before running tests, ensure you have:

1. **Python virtual environment activated**:
```bash
source venv/bin/activate  # On macOS/Linux
# or
venv\Scripts\activate  # On Windows
```

2. **Required environment variables in `.env`**:
```
DISCORD_TOKEN=your_discord_token
DISCORD_CHANNEL_ID=your_channel_id
GOOGLE_SHEETS_ID=your_sheet_id
GOOGLE_SERVICE_ACCOUNT_KEY=path/to/service_account.json
GEMINI_API_KEY=your_gemini_api_key
```

3. **All dependencies installed**:
```bash
pip install -r requirements.txt
```

## Test Output

Tests will output:
- **PASS/FAIL** status for each test
- **Error messages** with stack traces for failures
- **Log files** in `logs/` directory (if logging is enabled)

## Debugging

For detailed debug output:
```bash
# Run with verbose output
python -m unittest tests.test_discord_handler -v

# Debug Discord message structures
python tests/debug_message_structure.py
```

## Test Coverage

To check test coverage:
```bash
# Install coverage tool
pip install coverage

# Run tests with coverage
coverage run -m unittest discover tests
coverage report
coverage html  # Generate HTML report
```

## Adding New Tests

When adding new test files:
1. Follow naming convention: `test_*.py`
2. Import unittest and required modules
3. Create test classes inheriting from `unittest.TestCase`
4. Prefix test methods with `test_`
5. Use descriptive test names that explain what's being tested

Example:
```python
import unittest
from modules.your_module import your_function

class TestYourModule(unittest.TestCase):
    def test_function_returns_expected_value(self):
        result = your_function(input_data)
        self.assertEqual(result, expected_value)
```

## Notes

- Integration tests require valid API credentials
- Some tests may create/modify test data in Google Sheets
- Discord tests need bot permissions in the test channel
- Rate limits may affect test execution speed