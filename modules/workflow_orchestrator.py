"""
Workflow Orchestrator Module

This module orchestrates the complete pipeline:
1. Discord data collection
2. AI analysis with Gemini
3. Publishing to X/Typefully
4. Archiving processed posts
"""

from typing import Dict, Optional
import logging
from datetime import datetime

from modules.sheets_handler import GoogleSheetsHandler
from modules.gemini_analyzer import GeminiAnalyzer, SheetAnalyzer
from modules.x_publisher import create_publisher, SheetPublisher
from modules.archive_handler import ArchiveHandler

logger = logging.getLogger(__name__)


class WorkflowOrchestrator:
    """Orchestrate the complete workflow from Discord to Archive"""
    
    def __init__(
        self,
        sheets_handler: GoogleSheetsHandler,
        gemini_api_key: str = None,
        publisher_config: Dict = None
    ):
        """
        Initialize the workflow orchestrator
        
        Args:
            sheets_handler: GoogleSheetsHandler instance
            gemini_api_key: Optional Gemini API key for AI analysis
            publisher_config: Optional config for X/Typefully publishing
        """
        self.sheets = sheets_handler
        self.gemini_api_key = gemini_api_key
        self.publisher_config = publisher_config or {}
        
        # Initialize components
        self.gemini = None
        self.publisher = None
        self.archiver = ArchiveHandler(sheets_handler)
        
        # Initialize Gemini if API key provided
        if gemini_api_key:
            try:
                self.gemini = GeminiAnalyzer(api_key=gemini_api_key)
                logger.info("Gemini analyzer initialized")
            except Exception as e:
                logger.error(f"Failed to initialize Gemini: {e}")
        
        # Initialize publisher if config provided
        if publisher_config and publisher_config.get('type'):
            try:
                self.publisher = self._create_publisher(publisher_config)
                logger.info(f"Publisher initialized: {publisher_config['type']}")
            except Exception as e:
                logger.error(f"Failed to initialize publisher: {e}")
    
    def _create_publisher(self, config: Dict):
        """Create publisher based on configuration"""
        pub_type = config.get('type', '').lower()
        
        if pub_type == 'twitter' or pub_type == 'x':
            return create_publisher(
                'twitter',
                api_key=config.get('api_key'),
                api_secret=config.get('api_secret'),
                access_token=config.get('access_token'),
                access_token_secret=config.get('access_token_secret')
            )
        elif pub_type == 'typefully':
            return create_publisher(
                'typefully',
                api_key=config.get('api_key'),
                hours_delay=config.get('hours_delay', 0)
            )
        else:
            logger.warning(f"Unknown publisher type: {pub_type}")
            return None
    
    def run_analysis(self) -> Dict:
        """
        Run AI analysis on sheet data
        
        Returns:
            Dictionary with analysis results
        """
        results = {
            'success': False,
            'projects_found': 0,
            'posts_analyzed': 0,
            'errors': []
        }
        
        if not self.gemini:
            results['errors'].append("Gemini analyzer not initialized")
            return results
        
        try:
            logger.info("Starting AI analysis...")
            analyzer = SheetAnalyzer(self.sheets, self.gemini)
            
            # Ensure columns exist
            ai_summary_col, ai_processed_col, daily_draft_col = analyzer.ensure_columns_exist()
            
            # Analyze all rows
            project_summaries, all_processed = analyzer.analyze_all_rows()
            
            results['projects_found'] = len(project_summaries)
            results['posts_analyzed'] = len(all_processed)
            
            # Write summaries and mark processed
            if all_processed:
                analyzer.write_summaries(all_processed, ai_summary_col, ai_processed_col)
                logger.info(f"Wrote {len(all_processed)} AI summaries/statuses")
            
            # Generate and write daily draft
            if project_summaries:
                analyzer.generate_and_write_daily_draft(project_summaries, daily_draft_col)
                logger.info("Generated daily draft")
            
            results['success'] = True
            logger.info(f"Analysis complete: {results['projects_found']} projects, "
                       f"{results['posts_analyzed']} posts analyzed")
            
        except Exception as e:
            logger.error(f"Analysis failed: {e}")
            results['errors'].append(str(e))
        
        return results
    
    def run_publishing(self) -> Dict:
        """
        Run publishing workflow
        
        Returns:
            Dictionary with publishing results
        """
        results = {
            'success': False,
            'published': False,
            'url': None,
            'post_id': None,
            'errors': []
        }
        
        if not self.publisher:
            results['errors'].append("Publisher not initialized")
            return results
        
        try:
            logger.info("Starting publishing workflow...")
            
            # Create SheetPublisher wrapper
            sheet_publisher = SheetPublisher(self.publisher, self.sheets)
            
            # Find first row with daily draft
            sheet_data = self.sheets.get_sheet_data()
            
            if len(sheet_data) < 2:
                results['errors'].append("No data rows in sheet")
                return results
            
            headers = sheet_data[0]
            draft_col_idx = headers.index('Daily Post Draft') if 'Daily Post Draft' in headers else -1
            
            if draft_col_idx == -1:
                results['errors'].append("Daily Post Draft column not found")
                return results
            
            # Find first non-empty draft
            row_to_publish = None
            for idx, row in enumerate(sheet_data[1:], start=2):
                if len(row) > draft_col_idx and row[draft_col_idx] and row[draft_col_idx].strip():
                    row_to_publish = idx
                    break
            
            if not row_to_publish:
                results['errors'].append("No draft found to publish")
                return results
            
            # Publish from sheet
            logger.info(f"Publishing from row {row_to_publish}")
            publish_result = sheet_publisher.publish_from_sheet(row_to_publish)
            
            if publish_result.success:
                results['success'] = True
                results['published'] = True
                results['url'] = publish_result.url
                results['post_id'] = publish_result.post_id
                logger.info(f"Published successfully: {publish_result.url or publish_result.post_id}")
            else:
                results['errors'].append(publish_result.error_msg)
                logger.error(f"Publishing failed: {publish_result.error_msg}")
            
        except Exception as e:
            logger.error(f"Publishing failed: {e}")
            results['errors'].append(str(e))
        
        return results
    
    def run_archiving(self) -> Dict:
        """
        Run archive workflow
        
        Returns:
            Dictionary with archive results
        """
        logger.info("Starting archive workflow...")
        return self.archiver.run_archive_workflow()
    
    def run_complete_workflow(self) -> Dict:
        """
        Run the complete workflow:
        1. AI Analysis (if Gemini configured)
        2. Publishing (if publisher configured)
        3. Archiving (always runs)
        
        Returns:
            Dictionary with complete workflow results
        """
        results = {
            'timestamp': datetime.now().isoformat(),
            'analysis': None,
            'publishing': None,
            'archiving': None,
            'overall_success': False,
            'summary': []
        }
        
        logger.info("="*60)
        logger.info("Starting complete workflow")
        logger.info("="*60)
        
        # Step 1: AI Analysis (optional)
        if self.gemini:
            logger.info("Step 1: Running AI analysis...")
            results['analysis'] = self.run_analysis()
            
            if results['analysis']['success']:
                results['summary'].append(
                    f"✅ Analyzed {results['analysis']['posts_analyzed']} posts, "
                    f"found {results['analysis']['projects_found']} projects"
                )
            else:
                results['summary'].append(
                    f"❌ Analysis failed: {results['analysis']['errors']}"
                )
        else:
            logger.info("Step 1: Skipping AI analysis (not configured)")
            results['summary'].append("⏭️  AI analysis skipped (not configured)")
        
        # Step 2: Publishing (optional)
        if self.publisher:
            logger.info("Step 2: Running publishing...")
            results['publishing'] = self.run_publishing()
            
            if results['publishing']['success']:
                results['summary'].append(
                    f"✅ Published successfully: {results['publishing']['url'] or results['publishing']['post_id']}"
                )
            else:
                results['summary'].append(
                    f"❌ Publishing failed: {results['publishing']['errors']}"
                )
        else:
            logger.info("Step 2: Skipping publishing (not configured)")
            results['summary'].append("⏭️  Publishing skipped (not configured)")
        
        # Step 3: Archiving (always runs)
        logger.info("Step 3: Running archive workflow...")
        results['archiving'] = self.run_archiving()
        
        if results['archiving']['success']:
            results['summary'].append(
                f"✅ Archived {results['archiving']['posts_archived']} posts"
            )
        else:
            results['summary'].append(
                f"❌ Archiving failed: {results['archiving']['errors']}"
            )
        
        # Determine overall success
        results['overall_success'] = all([
            results['analysis']['success'] if results['analysis'] else True,
            results['publishing']['success'] if results['publishing'] else True,
            results['archiving']['success'] if results['archiving'] else False
        ])
        
        # Log summary
        logger.info("="*60)
        logger.info("Workflow Complete")
        logger.info("-"*60)
        for line in results['summary']:
            logger.info(line)
        logger.info("="*60)
        
        return results
    
    def run_daily_task(self) -> Dict:
        """
        Run the daily scheduled task
        This is what should be called by the scheduler
        
        Returns:
            Dictionary with task results
        """
        logger.info(f"Running daily task at {datetime.now()}")
        return self.run_complete_workflow()