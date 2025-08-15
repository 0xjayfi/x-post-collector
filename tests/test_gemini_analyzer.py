"""
Unit tests for Gemini AI Analyzer module
"""

import unittest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime
from dataclasses import dataclass

from modules.gemini_analyzer import (
    GeminiAnalyzer,
    SheetAnalyzer,
    RateLimitManager,
    ProjectInfo,
    ProjectSummary
)


class TestRateLimitManager(unittest.TestCase):
    """Test rate limit management"""
    
    def setUp(self):
        self.rate_limiter = RateLimitManager(daily_limit=100)
    
    def test_initial_state(self):
        """Test initial rate limiter state"""
        self.assertEqual(self.rate_limiter.daily_requests, 0)
        self.assertEqual(self.rate_limiter.minute_requests, 0)
        self.assertTrue(self.rate_limiter.can_make_request())
    
    def test_daily_limit(self):
        """Test daily limit enforcement"""
        self.rate_limiter.daily_requests = 100
        self.assertFalse(self.rate_limiter.can_make_request())
    
    def test_minute_limit(self):
        """Test minute limit enforcement"""
        self.rate_limiter.minute_requests = 14
        self.assertFalse(self.rate_limiter.can_make_request())
    
    def test_record_request(self):
        """Test request recording"""
        self.rate_limiter.record_request()
        self.assertEqual(self.rate_limiter.daily_requests, 1)
        self.assertEqual(self.rate_limiter.minute_requests, 1)
    
    @patch('modules.gemini_analyzer.datetime')
    def test_daily_reset(self, mock_datetime):
        """Test daily counter reset"""
        # Set initial time
        initial_time = datetime(2024, 1, 1, 10, 0)
        mock_datetime.now.return_value = initial_time
        
        self.rate_limiter.last_reset = initial_time
        self.rate_limiter.daily_requests = 50
        
        # Move to next day
        next_day = datetime(2024, 1, 2, 10, 0)
        mock_datetime.now.return_value = next_day
        
        self.assertTrue(self.rate_limiter.can_make_request())
        # Daily counter should be reset
        self.assertEqual(self.rate_limiter.daily_requests, 0)


class TestGeminiAnalyzer(unittest.TestCase):
    """Test Gemini AI analyzer"""
    
    def setUp(self):
        with patch('modules.gemini_analyzer.genai.configure'):
            self.analyzer = GeminiAnalyzer(api_key="test_key", daily_limit=100)
    
    @patch('modules.gemini_analyzer.genai.GenerativeModel')
    def test_initialization(self, mock_model):
        """Test analyzer initialization"""
        with patch('modules.gemini_analyzer.genai.configure') as mock_configure:
            analyzer = GeminiAnalyzer(api_key="test_key")
            mock_configure.assert_called_once_with(api_key="test_key")
            self.assertIsNotNone(analyzer.model)
            self.assertIsNotNone(analyzer.rate_limiter)
    
    def test_is_new_project_empty_content(self):
        """Test project detection with empty content"""
        self.assertFalse(self.analyzer.is_new_project(""))
        self.assertFalse(self.analyzer.is_new_project("   "))
        self.assertFalse(self.analyzer.is_new_project("short"))
    
    @patch.object(GeminiAnalyzer, '_make_request')
    def test_is_new_project_positive(self, mock_request):
        """Test positive project detection"""
        mock_request.return_value = "YES"
        content = "Check out this new DeFi protocol launching next week!"
        
        result = self.analyzer.is_new_project(content)
        
        self.assertTrue(result)
        mock_request.assert_called_once()
    
    @patch.object(GeminiAnalyzer, '_make_request')
    def test_is_new_project_negative(self, mock_request):
        """Test negative project detection"""
        mock_request.return_value = "NO"
        content = "Bitcoin price is up 10% today"
        
        result = self.analyzer.is_new_project(content)
        
        self.assertFalse(result)
    
    def test_extract_project_info_twitter_link(self):
        """Test extracting username from Twitter link"""
        with patch.object(self.analyzer, '_make_request') as mock_request:
            mock_request.return_value = "A new DeFi lending protocol"
            
            content = "Check out this project"
            link = "https://twitter.com/testproject/status/123"
            
            info = self.analyzer.extract_project_info(content, link)
            
            self.assertIsNotNone(info)
            self.assertEqual(info.username, "testproject")
            self.assertEqual(info.twitter_link, link)
            self.assertEqual(info.bio, "A new DeFi lending protocol")
    
    def test_extract_project_info_x_link(self):
        """Test extracting username from X.com link"""
        with patch.object(self.analyzer, '_make_request') as mock_request:
            mock_request.return_value = "NFT collection"
            
            content = "New NFT drop"
            link = "https://x.com/nftproject"
            
            info = self.analyzer.extract_project_info(content, link)
            
            self.assertIsNotNone(info)
            self.assertEqual(info.username, "nftproject")
    
    @patch.object(GeminiAnalyzer, '_make_request')
    def test_generate_summary(self, mock_request):
        """Test summary generation"""
        mock_request.return_value = "A DeFi protocol for automated yield farming."
        
        summary = self.analyzer.generate_summary(
            "New protocol launch",
            "Automated yield farming platform"
        )
        
        self.assertEqual(summary, "A DeFi protocol for automated yield farming.")
    
    @patch.object(GeminiAnalyzer, '_make_request')
    def test_generate_summary_truncation(self, mock_request):
        """Test summary truncation for long responses"""
        # Generate a response with more than 35 words
        long_response = " ".join(["word"] * 40)
        mock_request.return_value = long_response
        
        summary = self.analyzer.generate_summary("content", "bio")
        
        # Should be truncated to 30 words + "..."
        words = summary.split()
        self.assertTrue(len(words) <= 31)  # 30 words + "..."
        self.assertTrue(summary.endswith("..."))
    
    @patch.object(GeminiAnalyzer, '_make_request')
    def test_batch_analyze_projects(self, mock_request):
        """Test batch project analysis"""
        mock_request.return_value = "Post 1: YES\nPost 2: NO\nPost 3: YES"
        
        posts = [
            (2, {'content': 'New token launch'}),
            (3, {'content': 'Bitcoin price update'}),
            (4, {'content': 'NFT collection dropping'})
        ]
        
        results = self.analyzer.batch_analyze_projects(posts)
        
        self.assertEqual(len(results), 3)
        self.assertEqual(results[0], (2, True))
        self.assertEqual(results[1], (3, False))
        self.assertEqual(results[2], (4, True))
    
    def test_create_daily_draft_empty(self):
        """Test daily draft with no summaries"""
        draft = self.analyzer.create_daily_draft([])
        self.assertEqual(draft, "No new projects found today.")
    
    def test_create_daily_draft_with_summaries(self):
        """Test daily draft generation with summaries"""
        summaries = [
            ProjectSummary(
                date="2024-01-15",
                project_info=ProjectInfo(
                    username="defiproject",
                    twitter_link="https://twitter.com/defiproject",
                    bio="DeFi lending"
                ),
                ai_summary="Lending protocol with high yields",
                row_index=2
            ),
            ProjectSummary(
                date="2024-01-15",
                project_info=ProjectInfo(
                    username="nftdrop",
                    twitter_link="https://x.com/nftdrop",
                    bio="NFT collection"
                ),
                ai_summary="Exclusive NFT art collection",
                row_index=3
            )
        ]
        
        draft = self.analyzer.create_daily_draft(summaries)
        
        self.assertIn("New/Trending Projects on 2024-01-15", draft)
        self.assertIn("[@defiproject](https://twitter.com/defiproject)", draft)
        self.assertIn("[@nftdrop](https://x.com/nftdrop)", draft)
        self.assertIn("Lending protocol with high yields", draft)
        self.assertIn("Exclusive NFT art collection", draft)


class TestSheetAnalyzer(unittest.TestCase):
    """Test Sheet analyzer integration"""
    
    def setUp(self):
        self.mock_sheets = Mock()
        self.mock_sheets.sheet_id = "test_sheet_id"
        self.mock_sheets.service = Mock()
        
        with patch('modules.gemini_analyzer.genai.configure'):
            self.mock_gemini = GeminiAnalyzer(api_key="test_key")
        
        self.analyzer = SheetAnalyzer(self.mock_sheets, self.mock_gemini)
    
    def test_initialization(self):
        """Test sheet analyzer initialization"""
        self.assertEqual(self.analyzer.sheets, self.mock_sheets)
        self.assertEqual(self.analyzer.gemini, self.mock_gemini)
    
    def test_ensure_columns_exist_adds_missing(self):
        """Test adding missing columns"""
        # Mock existing headers without AI columns
        mock_response = {
            'values': [['date', 'time', 'content', 'post_link', 'author', 'author_link']]
        }
        
        self.mock_sheets.service.spreadsheets().values().get().execute.return_value = mock_response
        
        ai_col, draft_col = self.analyzer.ensure_columns_exist()
        
        # Should add new columns
        self.assertEqual(ai_col, 6)  # Index 6 for AI Summary
        self.assertEqual(draft_col, 7)  # Index 7 for Daily Post Draft
        
        # Should update headers
        self.mock_sheets.service.spreadsheets().values().update.assert_called_once()
    
    def test_ensure_columns_exist_already_present(self):
        """Test when columns already exist"""
        # Mock headers with AI columns already present
        mock_response = {
            'values': [['date', 'time', 'content', 'post_link', 'author', 
                       'author_link', 'AI Summary', 'Daily Post Draft']]
        }
        
        self.mock_sheets.service.spreadsheets().values().get().execute.return_value = mock_response
        
        ai_col, draft_col = self.analyzer.ensure_columns_exist()
        
        self.assertEqual(ai_col, 6)
        self.assertEqual(draft_col, 7)
        
        # Should not update headers
        self.mock_sheets.service.spreadsheets().values().update.assert_not_called()
    
    @patch.object(SheetAnalyzer, '_process_batch')
    def test_analyze_all_rows(self, mock_process):
        """Test analyzing all rows"""
        # Mock sheet data
        mock_data = {
            'values': [
                ['date', 'time', 'author', 'post_link', 'content', 'author_link'],
                ['2024-01-15', '10:00', 'user1', 'https://twitter.com/proj1', 'New DeFi launch', 'discord.com/user1'],
                ['2024-01-15', '11:00', 'user2', 'https://x.com/proj2', 'NFT drop tomorrow', 'discord.com/user2']
            ]
        }
        
        self.mock_sheets.read_sheet.return_value = mock_data
        
        # Mock batch processing results
        mock_summary = ProjectSummary(
            date="2024-01-15",
            project_info=ProjectInfo("proj1", "https://twitter.com/proj1", "DeFi"),
            ai_summary="New DeFi protocol",
            row_index=2
        )
        mock_process.return_value = [mock_summary]
        
        summaries = self.analyzer.analyze_all_rows()
        
        self.assertEqual(len(summaries), 1)
        self.assertEqual(summaries[0].project_info.username, "proj1")
    
    def test_write_summaries(self):
        """Test writing summaries to sheet"""
        summaries = [
            ProjectSummary(
                date="2024-01-15",
                project_info=ProjectInfo("proj1", "link1", "bio1"),
                ai_summary="Summary 1",
                row_index=2
            ),
            ProjectSummary(
                date="2024-01-15",
                project_info=ProjectInfo("proj2", "link2", "bio2"),
                ai_summary="Summary 2",
                row_index=3
            )
        ]
        
        self.analyzer.write_summaries(summaries, ai_summary_col=6)
        
        # Should call batch update
        self.mock_sheets.service.spreadsheets().values().batchUpdate.assert_called_once()
        
        # Check the update data
        call_args = self.mock_sheets.service.spreadsheets().values().batchUpdate.call_args
        body = call_args[1]['body']
        
        self.assertEqual(len(body['data']), 2)
        self.assertEqual(body['data'][0]['range'], 'G2')  # Column G (index 6), row 2
        self.assertEqual(body['data'][0]['values'], [['Summary 1']])
        self.assertEqual(body['data'][1]['range'], 'G3')  # Column G, row 3
        self.assertEqual(body['data'][1]['values'], [['Summary 2']])
    
    def test_generate_and_write_daily_draft(self):
        """Test generating and writing daily draft"""
        summaries = [
            ProjectSummary(
                date="2024-01-15",
                project_info=ProjectInfo("proj1", "https://twitter.com/proj1", "bio1"),
                ai_summary="Summary 1",
                row_index=2
            )
        ]
        
        with patch.object(self.mock_gemini, 'create_daily_draft') as mock_create:
            mock_create.return_value = "Daily draft content"
            
            self.analyzer.generate_and_write_daily_draft(summaries, daily_draft_col=7)
            
            # Should write to column H (index 7), row 2
            self.mock_sheets.service.spreadsheets().values().update.assert_called_once()
            
            call_args = self.mock_sheets.service.spreadsheets().values().update.call_args
            self.assertEqual(call_args[1]['range'], 'H2')
            self.assertEqual(call_args[1]['body']['values'], [['Daily draft content']])


if __name__ == '__main__':
    unittest.main()