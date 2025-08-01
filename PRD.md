# Project goal

This project is to build a python script that can be used to collect twitter posts in a Discord channel and send them to a sheet of a Google Sheets file. 

# Workflow 

1. At a specific time of a day (e.g., 08:00 pm), the script will check the Discord channel for posts in the last 24 hours.  
2. The script will collect the posts and send them to a sheet of a Google Sheets file. 
3. The sheet has the following columns:
    - Date (YYYY-MM-DD)
    - Time (HH:MM)
    - Post Content
    - Post Link (the link to the post)
    - Author (the author of the post)
    - Author Link (the link to the author's profile)

    Therefore, the collected posts should be in the above-mentioned format before being sent to the sheet.  

# Requirements 

- Python 3.10 or higher
- Discord API
- Google Sheets API

