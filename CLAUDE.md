# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Discord-to-Google Sheets integration project that collects Twitter posts from a Discord channel and archives them to Google Sheets on a daily schedule.

## Key Architecture

The system consists of 5 main modules as outlined in the flowchart:

1. **Scheduler Module**: Runs daily at 08:00 PM to trigger the collection process
2. **Discord Handler**: Connects to Discord API, fetches posts from the last 24 hours
3. **Data Processor**: Extracts and formats post data (date, time, content, links, author info)
4. **Google Sheets Handler**: Authenticates with Google Sheets API and appends data to the spreadsheet
5. **Logger Module**: Handles logging for success, errors, and empty results

## Data Format

The Google Sheets output contains these columns:
- Date (YYYY-MM-DD)
- Time (HH:MM)
- Post Content
- Post Link (the link to the post)
- Author (the author of the post)
- Author Link (the link to the author's profile)

## Development Setup

Since no implementation files exist yet, when building this project:

1. Set up Python 3.10+ environment
2. Install required packages for Discord API (discord.py) and Google Sheets API (google-api-python-client)
3. Configure authentication credentials for both Discord and Google Sheets APIs
4. Implement the workflow as described in PRD.md and visualized in discord-to-sheets-flowchart.mermaid

## Testing Approach

When implementing, consider:
- Unit tests for each module (scheduler, Discord handler, data processor, Google Sheets handler)
- Integration tests for the full workflow
- Mock Discord API responses for testing without hitting rate limits
- Test error handling for API failures and network issues