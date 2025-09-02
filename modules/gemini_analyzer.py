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
    keywords: Optional[str] = None  # Optional keywords field


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
    
    def __init__(self, api_key: str, model: str = 'gemini-1.5-flash', daily_limit: int = 1400, generation_mode: str = 'summary'):
        """
        Initialize Gemini analyzer
        
        Args:
            api_key: Google AI Studio API key
            model: Gemini model to use (default: gemini-1.5-flash for free tier)
            daily_limit: Daily request limit for rate limiting
            generation_mode: Generation mode ('summary' or 'keywords', default: 'summary')
        """
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel(model)
        self.rate_limiter = RateLimitManager(daily_limit)
        self.generation_mode = generation_mode
        logger.info(f"Initialized GeminiAnalyzer with model: {model}, mode: {generation_mode}")
    
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
        
        prompt = f"""Analyze this post containing a Twitter/X link. Determine if this is announcing or discussing a NEW crypto/Web3 project. 

Post content: {content}

Respond with only "YES" or "NO".

Criteria for YES:
- Mentions new token launch, IDO, or TGE
- Mentions new project 
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

        logger.debug(f"Project detection prompt: {prompt}")
        
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
    
    def generate_keywords(self, content: str, bio: str) -> str:
        """
        Generate 3-5 keywords that best describe the project
        
        Args:
            content: Original post content
            bio: Project bio/description
            
        Returns:
            Comma-separated keywords string
        """
        # Truncate inputs for token efficiency
        content = content[:500] if len(content) > 500 else content
        bio = bio[:300] if len(bio) > 300 else bio
        
        prompt = f"""Extract 3-5 keywords that best describe this crypto project.

Post: {content}
Bio/Description: {bio}

Requirements:
- Generate EXACTLY 3-5 keywords
- Focus on: project type, sector, technology, use case, and key features
- Be specific and relevant to crypto/Web3 space
- Return ONLY the keywords separated by commas
- No explanations, just keywords

Example format: DeFi, yield farming, automated, cross-chain, liquidity"""
        
        try:
            keywords = self._make_request(prompt, temperature=0.2)
            keywords = keywords.strip()
            # Clean up and validate keywords
            keyword_list = [k.strip() for k in keywords.split(',')]
            # Ensure we have 3-5 keywords
            if len(keyword_list) < 3:
                return "crypto, Web3, project"
            elif len(keyword_list) > 5:
                keyword_list = keyword_list[:5]
            return ", ".join(keyword_list)
        except Exception as e:
            logger.error(f"Error generating keywords: {e}")
            return "crypto, Web3, project"
    
    def analyze_single_row(self, row_idx: int, post_data: Dict) -> Tuple[Optional[ProjectSummary], str]:
        """
        Analyze a single row for new project detection with 6-second delays between API calls
        
        Args:
            row_idx: Row index in the sheet
            post_data: Dictionary containing 'content', 'post_link', 'date'
            
        Returns:
            Tuple of (ProjectSummary if new project, AI analysis string)
        """
        content = post_data.get('content', '')
        date = post_data.get('date', '')
        
        if not content:
            return None, "Not new project related"
        
        try:
            # Step 1: Check if it's a new project
            logger.debug(f"Analyzing row {row_idx}: Checking if new project...")
            is_new = self.is_new_project(content)
            
            # Step 2: Wait 6 seconds after first API call
            logger.debug(f"Row {row_idx}: Waiting 6 seconds after new project check...")
            time.sleep(6)
            
            if is_new:
                logger.debug(f"Row {row_idx}: Identified as new project")
                
                # Step 3: Extract project info and generate analysis
                project_info = self.extract_project_info(content)
                
                if project_info:
                    # Generate analysis based on mode (another API call)
                    if self.generation_mode == 'keywords':
                        ai_analysis = self.generate_keywords(content, project_info.bio)
                        keywords = ai_analysis
                        ai_summary = f"Keywords: {ai_analysis}"  # For backward compatibility
                    else:  # Default to summary mode
                        ai_analysis = self.generate_summary(content, project_info.bio)
                        keywords = None
                        ai_summary = ai_analysis
                    
                    # Step 4: Wait 6 seconds after second API call
                    logger.debug(f"Row {row_idx}: Waiting 6 seconds after {self.generation_mode} generation...")
                    time.sleep(6)
                    
                    summary = ProjectSummary(
                        date=date,
                        project_info=project_info,
                        ai_summary=ai_summary,
                        row_index=row_idx,
                        keywords=keywords
                    )
                    
                    logger.info(f"Row {row_idx}: New project @{project_info.username} - {ai_analysis[:50]}...")
                    return summary, ai_summary
                else:
                    logger.debug(f"Row {row_idx}: Could not extract project info")
                    # Step 4: Wait even if extraction failed
                    logger.debug(f"Row {row_idx}: Waiting 6 seconds after project info extraction...")
                    time.sleep(6)
                    return None, "Not new project related"
            else:
                logger.debug(f"Row {row_idx}: Not a new project")
                return None, "Not new project related"
                
        except Exception as e:
            if "RATE_LIMITED" in str(e):
                logger.error(f"Rate limited at row {row_idx}")
                raise
            else:
                logger.error(f"Error analyzing row {row_idx}: {e}")
                return None, "Analysis failed"
    
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
                #link = project.project_info.twitter_link
                
                # Use keywords if available and in keywords mode, otherwise use summary
                if self.generation_mode == 'keywords' and project.keywords:
                    content = f"[{project.keywords}]"
                else:
                    content = project.ai_summary
                
                line = f"☘️ @{username}: {content}\n" 
                # markdown format, not supported by either X or Typefully
                # line = f"☘️ [@{username}]({link}): {content}\n"
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
        self.generation_mode = gemini_analyzer.generation_mode
        logger.info(f"Initialized SheetAnalyzer with generation mode: {self.generation_mode}")
    
    def ensure_columns_exist(self) -> Tuple[int, int, int, int]:
        """
        Add AI Summary/Keywords, AI processed, and Daily Post Draft columns if missing
        
        Returns:
            Tuple of (ai_summary_col_index, ai_processed_col_index, daily_draft_col_index, ai_keywords_col_index)
        """
        try:
            # Get current headers
            sheet_data = self.sheets.get_sheet_data()
            result = {'values': sheet_data[:1] if sheet_data else [[]]}
            
            headers = result.get('values', [[]])[0] if result.get('values') else []
            
            ai_summary_col = -1
            ai_keywords_col = -1
            ai_processed_col = -1
            daily_draft_col = -1
            
            # Check for existing columns (case-insensitive)
            for i, header in enumerate(headers):
                header_lower = header.lower()
                if header_lower == 'ai summary':
                    ai_summary_col = i
                elif header_lower == 'ai keywords':
                    ai_keywords_col = i
                elif header_lower == 'ai processed':
                    ai_processed_col = i
                elif header_lower == 'daily post draft':
                    daily_draft_col = i
            
            # Check if columns need to be added
            needs_update = False
            
            # Always ensure AI Summary column exists for backward compatibility
            if ai_summary_col == -1:
                # Add after Content column (assuming it's column F, index 5)
                new_col_index = len(headers)
                headers.append('AI Summary')
                ai_summary_col = new_col_index
                needs_update = True
            
            # Add AI Keywords column if in keywords mode and doesn't exist
            if self.generation_mode == 'keywords' and ai_keywords_col == -1:
                # Insert after AI Summary column
                insert_index = ai_summary_col + 1
                if insert_index <= len(headers):
                    headers.insert(insert_index, 'AI Keywords')
                    ai_keywords_col = insert_index
                    # Adjust other columns if needed
                    if ai_processed_col >= insert_index:
                        ai_processed_col += 1
                    if daily_draft_col >= insert_index:
                        daily_draft_col += 1
                else:
                    headers.append('AI Keywords')
                    ai_keywords_col = len(headers) - 1
                needs_update = True
            
            # Add AI processed column if it doesn't exist
            if ai_processed_col == -1:
                # Insert after AI Summary/Keywords columns
                insert_index = max(ai_summary_col, ai_keywords_col) + 1
                if insert_index <= len(headers):
                    headers.insert(insert_index, 'AI processed')
                    ai_processed_col = insert_index
                    # Adjust daily_draft_col if it was already set and comes after
                    if daily_draft_col >= insert_index:
                        daily_draft_col += 1
                else:
                    headers.append('AI processed')
                    ai_processed_col = len(headers) - 1
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
            
            return ai_summary_col, ai_processed_col, daily_draft_col, ai_keywords_col
            
        except Exception as e:
            logger.error(f"Error ensuring columns exist: {e}")
            raise
    
    def analyze_all_rows(self) -> Tuple[List[ProjectSummary], List[Tuple[int, str]]]:
        """
        Process all rows individually with delays to avoid rate limiting
        
        Returns:
            Tuple of (List of project summaries, List of all processed rows with AI summaries)
        """
        summaries = []
        all_processed_rows = []
        
        try:
            # Read all data
            rows = self.sheets.get_sheet_data()
            
            if len(rows) <= 1:  # No data or only headers
                logger.info("No data rows to analyze")
                return summaries, all_processed_rows
            
            headers = rows[0]
            data_rows = rows[1:]
            
            # Find column indices (case-insensitive)
            # Convert headers to lowercase for comparison
            headers_lower = [h.lower() for h in headers]
            content_idx = headers_lower.index('content') if 'content' in headers_lower else 4
            post_link_idx = headers_lower.index('post link') if 'post link' in headers_lower else 3
            date_idx = headers_lower.index('date') if 'date' in headers_lower else 0
            
            # Check for AI Summary column (case-insensitive)
            ai_summary_idx = -1
            for idx, header in enumerate(headers):
                if header.lower() == 'ai summary':
                    ai_summary_idx = idx
                    break
            
            # Check for AI processed column to skip already processed rows (case-insensitive)
            ai_processed_idx = -1
            for idx, header in enumerate(headers):
                if header.lower() == 'ai processed':
                    ai_processed_idx = idx
                    break
            
            # Process rows individually
            skipped_count = 0
            processed_count = 0
            
            logger.info(f"Starting individual row analysis for {len(data_rows)} rows")
            
            for row_idx, row in enumerate(data_rows, start=2):  # Start from row 2 (after header)
                # Skip if already analyzed (check both AI Summary and AI processed columns)
                if ai_summary_idx >= 0 and len(row) > ai_summary_idx and row[ai_summary_idx]:
                    skipped_count += 1
                    continue
                if ai_processed_idx >= 0 and len(row) > ai_processed_idx and row[ai_processed_idx] == 'TRUE':
                    skipped_count += 1
                    continue
                
                # Get row data safely
                content = row[content_idx] if len(row) > content_idx else ""
                post_link = row[post_link_idx] if len(row) > post_link_idx else ""
                date = row[date_idx] if len(row) > date_idx else ""
                
                if content and post_link:
                    try:
                        # Analyze single row with built-in delays
                        logger.info(f"Processing row {row_idx} ({processed_count + 1} of {len(data_rows) - skipped_count})")
                        
                        post_data = {
                            'content': content,
                            'post_link': post_link,
                            'date': date
                        }
                        
                        # Analyze the row (includes 4-second delays between API calls)
                        project_summary, ai_summary = self.gemini.analyze_single_row(row_idx, post_data)
                        
                        # Record the result
                        all_processed_rows.append((row_idx, ai_summary))
                        
                        if project_summary:
                            summaries.append(project_summary)
                        
                        processed_count += 1
                        
                        # Log progress every 5 rows
                        if processed_count % 5 == 0:
                            logger.info(f"Progress: {processed_count} rows analyzed, {len(summaries)} new projects found")
                        
                    except Exception as e:
                        if "RATE_LIMITED" in str(e):
                            logger.warning(f"Rate limited after processing {processed_count} rows")
                            # Return what we have so far
                            break
                        else:
                            logger.error(f"Error processing row {row_idx}: {e}")
                            # Mark as failed but continue
                            all_processed_rows.append((row_idx, "Analysis failed"))
            
            if skipped_count > 0:
                logger.info(f"Skipped {skipped_count} already processed rows")
            
            logger.info(f"Completed: Analyzed {processed_count} new rows, found {len(summaries)} new projects")
            return summaries, all_processed_rows
            
        except Exception as e:
            logger.error(f"Error analyzing rows: {e}")
            return summaries, all_processed_rows
    
    # Removed _process_batch method as we're no longer doing batch processing
    
    def write_summaries(self, all_processed: List[Tuple[int, str]], ai_summary_col: int, ai_processed_col: int, ai_keywords_col: int = -1):
        """
        Write AI summaries/keywords and AI processed status to the sheet
        
        Args:
            all_processed: List of (row_index, ai_analysis) tuples for all processed rows
            ai_summary_col: Column index for AI Summary
            ai_processed_col: Column index for AI processed
            ai_keywords_col: Column index for AI Keywords (optional, -1 if not present)
        """
        if not all_processed:
            return
        
        try:
            # Read current sheet data
            all_rows = self.sheets.get_sheet_data()
            
            # Ensure we have enough columns in each row
            max_col = max(ai_summary_col, ai_processed_col, ai_keywords_col if ai_keywords_col != -1 else 0)
            for row_idx in range(len(all_rows)):
                while len(all_rows[row_idx]) <= max_col:
                    all_rows[row_idx].append('')
            
            # Update the appropriate columns for each processed row
            for row_index, ai_analysis in all_processed:
                if row_index - 1 < len(all_rows):  # row_index is 1-based
                    # Write the analysis to the appropriate column
                    if self.generation_mode == 'keywords' and ai_keywords_col != -1:
                        # Extract just the keywords (remove "Keywords: " prefix if present)
                        if ai_analysis.startswith("Keywords: "):
                            keywords_only = ai_analysis.replace("Keywords: ", "")
                            all_rows[row_index - 1][ai_keywords_col] = keywords_only
                        else:
                            all_rows[row_index - 1][ai_keywords_col] = ai_analysis
                        # Also write to summary column for backward compatibility
                        all_rows[row_index - 1][ai_summary_col] = ai_analysis
                    else:
                        all_rows[row_index - 1][ai_summary_col] = ai_analysis
                    
                    all_rows[row_index - 1][ai_processed_col] = "TRUE"
            
            # Clear and rewrite the entire sheet
            self.sheets.clear_sheet(preserve_headers=False)
            self.sheets.append_data(all_rows)
            
            mode_text = "keywords" if self.generation_mode == 'keywords' else "summaries"
            logger.info(f"Written {len(all_processed)} AI {mode_text} to sheet")
                
        except Exception as e:
            logger.error(f"Error writing {self.generation_mode}: {e}")
    
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
        logger.info(f"Starting daily analysis in {self.generation_mode} mode")
        
        try:
            # Ensure columns exist (now returns 4 values)
            ai_summary_col, ai_processed_col, daily_draft_col, ai_keywords_col = self.ensure_columns_exist()
            
            # Analyze all rows
            summaries, all_processed_rows = self.analyze_all_rows()
            
            if all_processed_rows:
                # Write all AI summaries/keywords (including "Not new project related")
                self.write_summaries(all_processed_rows, ai_summary_col, ai_processed_col, ai_keywords_col)
                
                # Generate and write daily draft only if there are actual projects
                if summaries:
                    self.generate_and_write_daily_draft(summaries, daily_draft_col)
                    mode_text = "keywords" if self.generation_mode == 'keywords' else "summaries"
                    logger.info(f"Daily analysis complete ({mode_text} mode): {len(all_processed_rows)} rows processed, {len(summaries)} new projects found")
                else:
                    logger.info(f"Daily analysis complete: {len(all_processed_rows)} rows processed, no new projects found")
            else:
                logger.info("No rows to analyze")
                
        except Exception as e:
            logger.error(f"Error in daily analysis: {e}")
            raise