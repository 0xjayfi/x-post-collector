"""Utility functions for timezone handling."""

import time
import platform
from datetime import datetime


def get_local_timezone_name() -> str:
    """
    Get the local timezone abbreviation (e.g., PST, EST, CST, etc.)
    
    Returns:
        String with timezone abbreviation or offset
    """
    # Get the timezone name from time.tzname
    # time.tzname returns a tuple like ('PST', 'PDT') for standard and daylight saving time
    if time.daylight and time.localtime().tm_isdst:
        # Currently in daylight saving time
        tz_name = time.tzname[1]
    else:
        # Standard time
        tz_name = time.tzname[0]
    
    # Handle UTC offset format (like '+08' or '-05')
    if tz_name.startswith(('+', '-')) and len(tz_name) <= 4:
        # Convert to UTC format
        try:
            offset_hours = int(tz_name[:3])
            if offset_hours >= 0:
                tz_name = f"UTC+{abs(offset_hours)}"
            else:
                tz_name = f"UTC{offset_hours}"
        except (ValueError, IndexError):
            # Keep original if conversion fails
            pass
    # Clean up the timezone name - sometimes it might be longer like "Pacific Standard Time"
    elif len(tz_name) > 5:
        # Try to get abbreviation from long name
        words = tz_name.split()
        if len(words) >= 2:
            # Take first letter of each word (e.g., "Pacific Standard Time" -> "PST")
            abbrev = ''.join(word[0] for word in words if word and word[0].isupper())
            if abbrev:
                tz_name = abbrev
    
    # Special handling for common timezone patterns
    tz_mappings = {
        'China Standard Time': 'CST',
        'China Daylight Time': 'CDT',
        'Eastern Standard Time': 'EST',
        'Eastern Daylight Time': 'EDT',
        'Central Standard Time': 'CST',
        'Central Daylight Time': 'CDT',
        'Mountain Standard Time': 'MST',
        'Mountain Daylight Time': 'MDT',
        'Pacific Standard Time': 'PST',
        'Pacific Daylight Time': 'PDT',
    }
    
    # Check if we have a known long name
    for long_name, short_name in tz_mappings.items():
        if long_name in tz_name:
            return short_name
    
    return tz_name


def get_time_column_header() -> str:
    """
    Get the time column header with local timezone.
    
    Returns:
        String like "Time (PST)" or "Time (EST)"
    """
    tz_name = get_local_timezone_name()
    return f"Time ({tz_name})"