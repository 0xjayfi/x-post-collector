"""
Gemini AI Analyzer Module

Analyzes Google Sheets content to identify new crypto/Web3 projects
and generates structured daily summaries using Google's Gemini AI.
"""

import time
import logging
from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional, Dict, Tuple
import google.generativeai as genai

from modules.sheets_handler import GoogleSheetsHandler

logger = logging.getLogger(__name__)


@dataclass
class ProjectInfo:
    """Information about a crypto/Web3 project"""
    username: str
    twitter_link: str
    bio: str


@dataclass
class ProjectSummary:
    """Summary of a project with AI analysis"""
    date: str
    project_info: ProjectInfo
    ai_summary: str
    row_index: int


class RateLimitManager:
    """Manage Gemini API free tier limits"""
    
    def __init__(self, daily_limit: int = 1400):
        self.daily_limit = daily_limit
        self.daily_requests = 0
        self.minute_requests = 0
        self.last_reset = datetime.now()
        self.last_minute = datetime.now()
        
    def can_make_request(self) -> bool:
        """Check if within rate limits"""
        now = datetime.now()
        
        # Reset daily counter
        if now.date() > self.last_reset.date():
            self.daily_requests = 0
            self.last_reset = now
            logger.info("Rate limit daily counter reset")
        
        # Reset minute counter
        if (now - self.last_minute).seconds >= 60:
            self.minute_requests = 0
            self.last_minute = now
        
        # Check limits (conservative to leave buffer)
        if self.daily_requests >= self.daily_limit:
            logger.warning(f"Daily rate limit reached: {self.daily_requests}/{self.daily_limit}")
            return False
        if self.minute_requests >= 14:  # Leave 1 buffer from 15
            logger.debug(f"Minute rate limit reached: {self.minute_requests}/14")
            return False
            
        return True
    
    def record_request(self):
        """Record API call"""
        self.daily_requests += 1
        self.minute_requests += 1
        logger.debug(f"Recorded request - Daily: {self.daily_requests}, Minute: {self.minute_requests}")
    
    def wait_if_needed(self):
        """Wait if rate limit is hit"""
        if not self.can_make_request():
            if self.minute_requests >= 14:
                # Wait for minute reset
                wait_time = 60 - (datetime.now() - self.last_minute).seconds
                logger.info(f"Rate limit: waiting {wait_time} seconds")
                time.sleep(wait_time + 1)
                self.minute_requests = 0
                self.last_minute = datetime.now()
            else:
                # Daily limit reached
                logger.error("Daily rate limit reached. Cannot process more requests today.")
                raise Exception("Daily rate limit reached")


class GeminiAnalyzer:
    """Handles Gemini AI operations for content analysis"""
    
    def __init__(self, api_key: str, model: str = 'gemini-1.5-flash', daily_limit: int = 1400):
        """
        Initialize Gemini analyzer
        
        Args:
            api_key: Google AI Studio API key
            model: Gemini model to use (default: gemini-1.5-flash for free tier)
            daily_limit: Daily request limit for rate limiting
        """
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel(model)
        self.rate_limiter = RateLimitManager(daily_limit)
        logger.info(f"Initialized GeminiAnalyzer with model: {model}")
    
    def _make_request(self, prompt: str, temperature: float = 0.3) -> str:
        """Make a rate-limited request to Gemini API"""
        self.rate_limiter.wait_if_needed()
        
        try:
            response = self.model.generate_content(
                prompt,
                generation_config={
                    "temperature": temperature,
                    "max_output_tokens": 512,
                }
            )
            self.rate_limiter.record_request()
            return response.text
        except Exception as e:
            error_msg = str(e).lower()
            if "quota" in error_msg or "429" in error_msg:
                logger.warning("Hit API rate limit")
                raise Exception("RATE_LIMITED")
            elif "api_key" in error_msg or "authentication" in error_msg:
                logger.error("Invalid API key")
                raise Exception("AUTH_ERROR")
            else:
                logger.error(f"Gemini API error: {e}")
                raise
    
    def is_new_project(self, content: str) -> bool:
        """
        Determine if post is about a new crypto/Web3 project
        
        Args:
            content: Post content to analyze
            
        Returns:
            True if post is about a new project, False otherwise
        """
        if not content or len(content.strip()) < 10:
            return False
        
        # Truncate very long content to save tokens
        content = content[:1000] if len(content) > 1000 else content
        
        prompt = f"""Analyze this Discord post containing a Twitter/X link.
Determine if this is announcing or discussing a NEW crypto/Web3 project.

Post content: {content}

Respond with only "YES" or "NO".

Criteria for YES:
- Mentions new token launch, IDO, or TGE
- Announces new protocol or dApp
- Introduces new NFT collection
- New DeFi platform or tool
- New blockchain or L2
- Mentions Bio or Description 

Criteria for NO:
- General market discussion
- Price talk about existing tokens
- News about established projects
- Personal opinions without new project info"""
        
        try:
            response = self._make_request(prompt, temperature=0.1)
            result = response.strip().upper() == "YES"
            logger.debug(f"Project detection for content '{content[:50]}...': {result}")
            return result
        except Exception as e:
            logger.error(f"Error detecting new project: {e}")
            return False
    
    def extract_project_info(self, content: str) -> Optional[ProjectInfo]:
        """
        Extract project information from post content
        
        Args:
            content: Post content (contains embedded Twitter/X info)
            
        Returns:
            ProjectInfo object or None if extraction fails
        """
        # Truncate content for token efficiency
        content = content[:1500] if len(content) > 1500 else content
        
        prompt = f"""Extract Twitter/X project information from this Discord post that contains an embedded Twitter/X post.

Post content: {content}

Look for:
1. The Twitter/X username of the PROJECT being discussed (starts with @)
2. The Twitter/X link to the project's post or profile
3. The project's description or bio from the embedded content

Return in this exact format:
USERNAME: @username
LINK: https://twitter.com/username or https://x.com/username
DESCRIPTION: Brief project description

If any information is not found, use "unknown" for username, "no link" for link, and "No description provided" for description."""
        
        try:
            response = self._make_request(prompt, temperature=0.2)
            
            # Parse the response
            username = "unknown"
            twitter_link = ""
            bio = "No description provided"
            
            for line in response.split('\n'):
                line = line.strip()
                if line.startswith('USERNAME:'):
                    username = line.replace('USERNAME:', '').strip()
                    username = username.replace('@', '')  # Remove @ if present
                elif line.startswith('LINK:'):
                    twitter_link = line.replace('LINK:', '').strip()
                elif line.startswith('DESCRIPTION:'):
                    bio = line.replace('DESCRIPTION:', '').strip()
            
            # If no link was extracted, try to construct from username
            if (not twitter_link or twitter_link == "no link") and username != "unknown":
                twitter_link = f"https://x.com/{username}"
            
            return ProjectInfo(
                username=username,
                twitter_link=twitter_link,
                bio=bio if bio else "No description provided"
            )
        except Exception as e:
            logger.error(f"Error extracting project info: {e}")
            return None
    
    def generate_summary(self, content: str, bio: str) -> str:
        """
        Generate concise project summary
        
        Args:
            content: Original post content
            bio: Project bio/description
            
        Returns:
            Concise summary string
        """
        # Truncate inputs for token efficiency
        content = content[:500] if len(content) > 500 else content
        bio = bio[:300] if len(bio) > 300 else bio
        
        prompt = f"""Create a 1-2 sentence summary of this crypto project.

Post: {content}
Bio/Description: {bio}

Focus on:
- What the project does
- Key innovation or utility
- Target market or use case

Keep under 20 words. Be specific and informative. If you cannot provide a summary, respond with "No info yet"."""
        
        try:
            summary = self._make_request(prompt, temperature=0.3)
            summary = summary.strip()
            # Ensure summary is not too long
            words = summary.split()
            if len(words) > 35:
                summary = " ".join(words[:30]) + "..."
            return summary
        except Exception as e:
            logger.error(f"Error generating summary: {e}")
            return "Summary generation failed"
    
    def batch_analyze_projects(self, posts: List[Tuple[int, Dict]]) -> List[Tuple[int, bool]]:
        """
        Analyze multiple posts in a single API call to save quota
        
        Args:
            posts: List of (row_index, post_data) tuples
            
        Returns:
            List of (row_index, is_new_project) tuples
        """
        if not posts:
            return []
        
        # Build combined prompt
        post_texts = []
        for idx, (row_idx, post) in enumerate(posts[:5]):  # Max 5 per batch
            content = post.get('content', '')[:200]  # Limit content length
            post_texts.append(f"Post {idx + 1}: {content}")
        
        combined_prompt = f"""Analyze each post below. For each, respond YES if it's about a new crypto project, NO otherwise.

{chr(10).join(post_texts)}

Response format (one per line):
Post 1: YES/NO
Post 2: YES/NO
..."""
        
        try:
            response = self._make_request(combined_prompt, temperature=0.1)
            results = []
            
            lines = response.strip().split('\n')
            for i, (row_idx, _) in enumerate(posts[:5]):
                if i < len(lines):
                    line = lines[i].upper()
                    is_project = "YES" in line
                    results.append((row_idx, is_project))
                else:
                    results.append((row_idx, False))
            
            return results
        except Exception as e:
            logger.error(f"Error in batch analysis: {e}")
            # Return all as False on error
            return [(row_idx, False) for row_idx, _ in posts[:5]]
    
    def create_daily_draft(self, summaries: List[ProjectSummary]) -> str:
        """
        Format all summaries into structured daily post
        
        Args:
            summaries: List of project summaries
            
        Returns:
            Formatted daily draft string
        """
        if not summaries:
            return "No new projects found today."
        
        # Group by date
        grouped = {}
        for summary in summaries:
            date = summary.date
            if date not in grouped:
                grouped[date] = []
            grouped[date].append(summary)
        
        # Format output
        draft_lines = []
        for date, projects in sorted(grouped.items()):
            draft_lines.append(f"🚀 New/Trending Projects on {date}:")
            draft_lines.append("")
            
            for project in projects:
                username = project.project_info.username
                link = project.project_info.twitter_link
                summary = project.ai_summary
                
                line = f"☘️ [@{username}]({link}): {summary}\n"
                draft_lines.append(line)
            
            draft_lines.append("")  # Empty line between dates
        
        return "\n".join(draft_lines)


class SheetAnalyzer:
    """Integrates Gemini analyzer with Google Sheets"""
    
    def __init__(self, sheets_handler: GoogleSheetsHandler, gemini_analyzer: GeminiAnalyzer):
        """
        Initialize sheet analyzer
        
        Args:
            sheets_handler: Google Sheets handler instance
            gemini_analyzer: Gemini AI analyzer instance
        """
        self.sheets = sheets_handler
        self.gemini = gemini_analyzer
        logger.info("Initialized SheetAnalyzer")
    
    def ensure_columns_exist(self) -> Tuple[int, int]:
        """
        Add AI Summary and Daily Post Draft columns if missing
        
        Returns:
            Tuple of (ai_summary_col_index, daily_draft_col_index)
        """
        try:
            # Get current headers
            sheet_data = self.sheets.get_sheet_data()
            result = {'values': sheet_data[:1] if sheet_data else [[]]}
            
            headers = result.get('values', [[]])[0] if result.get('values') else []
            
            ai_summary_col = -1
            daily_draft_col = -1
            
            # Check for existing columns
            for i, header in enumerate(headers):
                if header == 'AI Summary':
                    ai_summary_col = i
                elif header == 'Daily Post Draft':
                    daily_draft_col = i
            
            # Check if columns need to be added
            needs_update = False
            
            if ai_summary_col == -1:
                # Add after Content column (assuming it's column F, index 5)
                new_col_index = len(headers)
                headers.append('AI Summary')
                ai_summary_col = new_col_index
                needs_update = True
                
            if daily_draft_col == -1:
                # Add as last column
                new_col_index = len(headers)
                headers.append('Daily Post Draft')
                daily_draft_col = new_col_index
                needs_update = True
            
            # Update headers if needed
            if needs_update:
                # Use append_data to add headers
                # First, get all current data
                all_rows = self.sheets.get_sheet_data()
                
                # Update the header row
                if all_rows:
                    all_rows[0] = headers
                else:
                    all_rows = [headers]
                
                # Clear and rewrite the sheet
                self.sheets.clear_sheet(preserve_headers=False)
                self.sheets.append_data(all_rows)
                logger.info("Added missing columns to sheet")
            
            return ai_summary_col, daily_draft_col
            
        except Exception as e:
            logger.error(f"Error ensuring columns exist: {e}")
            raise
    
    def analyze_all_rows(self) -> List[ProjectSummary]:
        """
        Process all rows efficiently with rate limiting
        
        Returns:
            List of project summaries
        """
        summaries = []
        
        try:
            # Read all data
            rows = self.sheets.get_sheet_data()
            
            if len(rows) <= 1:  # No data or only headers
                logger.info("No data rows to analyze")
                return summaries
            
            headers = rows[0]
            data_rows = rows[1:]
            
            # Find column indices
            content_idx = headers.index('content') if 'content' in headers else 4
            post_link_idx = headers.index('post_link') if 'post_link' in headers else 3
            date_idx = headers.index('date') if 'date' in headers else 0
            
            # Check for AI Summary column
            ai_summary_idx = headers.index('AI Summary') if 'AI Summary' in headers else -1
            
            # Batch process rows
            batch = []
            for row_idx, row in enumerate(data_rows, start=2):  # Start from row 2 (after header)
                # Skip if already analyzed
                if ai_summary_idx >= 0 and len(row) > ai_summary_idx and row[ai_summary_idx]:
                    continue
                
                # Get row data safely
                content = row[content_idx] if len(row) > content_idx else ""
                post_link = row[post_link_idx] if len(row) > post_link_idx else ""
                date = row[date_idx] if len(row) > date_idx else ""
                
                if content and post_link:
                    batch.append((row_idx, {
                        'content': content,
                        'post_link': post_link,
                        'date': date
                    }))
                
                # Process batch when full or at end
                if len(batch) >= 5:
                    summaries.extend(self._process_batch(batch))
                    batch = []
                    time.sleep(4)  # Rate limiting between batches
            
            # Process remaining batch
            if batch:
                summaries.extend(self._process_batch(batch))
            
            logger.info(f"Analyzed {len(summaries)} new projects")
            return summaries
            
        except Exception as e:
            logger.error(f"Error analyzing rows: {e}")
            return summaries
    
    def _process_batch(self, batch: List[Tuple[int, Dict]]) -> List[ProjectSummary]:
        """
        Process a batch of rows
        
        Args:
            batch: List of (row_index, row_data) tuples
            
        Returns:
            List of project summaries
        """
        summaries = []
        
        # First, batch check which are new projects
        project_checks = self.gemini.batch_analyze_projects(batch)
        
        # Process each identified project
        for (row_idx, is_project), (_, row_data) in zip(project_checks, batch):
            if is_project:
                content = row_data['content']
                date = row_data['date']
                
                # Extract project info from content (contains embedded Twitter/X info)
                project_info = self.gemini.extract_project_info(content)
                if project_info:
                    # Generate summary
                    ai_summary = self.gemini.generate_summary(content, project_info.bio)
                    
                    summaries.append(ProjectSummary(
                        date=date,
                        project_info=project_info,
                        ai_summary=ai_summary,
                        row_index=row_idx
                    ))
                    
                    logger.debug(f"Processed project at row {row_idx}: {project_info.username}")
        
        return summaries
    
    def write_summaries(self, summaries: List[ProjectSummary], ai_summary_col: int):
        """
        Write AI summaries to the sheet
        
        Args:
            summaries: List of project summaries
            ai_summary_col: Column index for AI Summary
        """
        if not summaries:
            return
        
        try:
            # Read current sheet data
            all_rows = self.sheets.get_sheet_data()
            
            # Ensure we have enough columns in each row
            for row_idx in range(len(all_rows)):
                while len(all_rows[row_idx]) <= ai_summary_col:
                    all_rows[row_idx].append('')
            
            # Update the AI summary column for each processed row
            for summary in summaries:
                if summary.row_index - 1 < len(all_rows):  # row_index is 1-based
                    all_rows[summary.row_index - 1][ai_summary_col] = summary.ai_summary
            
            # Clear and rewrite the entire sheet
            self.sheets.clear_sheet(preserve_headers=False)
            self.sheets.append_data(all_rows)
            
            logger.info(f"Written {len(summaries)} AI summaries to sheet")
                
        except Exception as e:
            logger.error(f"Error writing summaries: {e}")
    
    def generate_and_write_daily_draft(self, summaries: List[ProjectSummary], daily_draft_col: int):
        """
        Generate and write daily draft to the sheet
        
        Args:
            summaries: List of project summaries
            daily_draft_col: Column index for Daily Post Draft
        """
        try:
            # Generate daily draft
            daily_draft = self.gemini.create_daily_draft(summaries)
            
            # Read current sheet data
            all_rows = self.sheets.get_sheet_data()
            
            # Ensure we have at least 2 rows (header + first data row)
            while len(all_rows) < 2:
                all_rows.append([])
            
            # Ensure the second row has enough columns
            while len(all_rows[1]) <= daily_draft_col:
                all_rows[1].append('')
            
            # Set the daily draft in the second row (first data row)
            all_rows[1][daily_draft_col] = daily_draft
            
            # Clear and rewrite the entire sheet
            self.sheets.clear_sheet(preserve_headers=False)
            self.sheets.append_data(all_rows)
            
            logger.info("Written daily draft to sheet")
            
        except Exception as e:
            logger.error(f"Error writing daily draft: {e}")
    
    def run_daily_analysis(self):
        """
        Run the complete daily analysis workflow
        """
        logger.info("Starting daily analysis")
        
        try:
            # Ensure columns exist
            ai_summary_col, daily_draft_col = self.ensure_columns_exist()
            
            # Analyze all rows
            summaries = self.analyze_all_rows()
            
            if summaries:
                # Write individual summaries
                self.write_summaries(summaries, ai_summary_col)
                
                # Generate and write daily draft
                self.generate_and_write_daily_draft(summaries, daily_draft_col)
                
                logger.info(f"Daily analysis complete: {len(summaries)} projects processed")
            else:
                logger.info("No new projects found in daily analysis")
                
        except Exception as e:
            logger.error(f"Error in daily analysis: {e}")
            raise