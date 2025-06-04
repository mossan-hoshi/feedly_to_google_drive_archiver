#!/usr/bin/env python3
"""
Feedly to Google Drive Archiver - Scheduler

This module implements scheduling functionality to run the archiver at regular intervals.
"""

import os
import time
import logging
import schedule
from datetime import datetime, timedelta
from dotenv import load_dotenv
from main import fetch_feedly_articles, transform_to_json_structure, generate_safe_filename
import json

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/home/sackn/repos_wsl/feedly_to_google_drive_archiver/scheduler.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


def run_archiver_job():
    """
    Run the Feedly to Google Drive archiver job.
    This function will be called by the scheduler.
    """
    try:
        logger.info("=" * 50)
        logger.info("Starting scheduled archiver job")
        logger.info("=" * 50)
        
        # Load environment variables
        load_dotenv()
        
        # Get configuration from environment variables
        feedly_token = os.getenv("FEEDLY_ACCESS_TOKEN")
        stream_id = os.getenv("FEEDLY_STREAM_ID")
        fetch_period_days = int(os.getenv("FETCH_PERIOD_DAYS", 1))  # Default to 1 day for scheduled runs
        
        if not feedly_token or not stream_id:
            logger.error("Required environment variables are missing. Please check your .env file.")
            return
        
        # Calculate timestamp for filtering (fetch articles from the last N days)
        now = datetime.now()
        older_than_date = now - timedelta(days=fetch_period_days)
        newer_than_timestamp_ms = int(older_than_date.timestamp() * 1000)
        
        logger.info(f"Fetching articles newer than: {older_than_date.isoformat()}")
        logger.info(f"Stream ID: {stream_id}")
        
        # Fetch articles from Feedly
        articles = fetch_feedly_articles(feedly_token, stream_id, newer_than_timestamp_ms)
        
        if articles:
            logger.info(f"Processing {len(articles)} articles...")
            
            # Create output directory if it doesn't exist
            output_dir = "/home/sackn/repos_wsl/feedly_to_google_drive_archiver/archived_articles"
            os.makedirs(output_dir, exist_ok=True)
            
            processed_count = 0
            for article in articles:
                try:
                    # Transform article data
                    transformed_article = transform_to_json_structure(article)
                    
                    # Generate safe filename
                    filename = generate_safe_filename(article)
                    filepath = os.path.join(output_dir, filename)
                    
                    # Save article as JSON file
                    with open(filepath, 'w', encoding='utf-8') as f:
                        json.dump(transformed_article, f, indent=2, ensure_ascii=False)
                    
                    processed_count += 1
                    logger.info(f"Saved article: {filename}")
                    logger.debug(f"Title: {transformed_article['title']}")
                    logger.debug(f"URL: {transformed_article['url']}")
                    logger.debug(f"Published: {transformed_article['publishedDate']}")
                    
                except Exception as e:
                    logger.error(f"Error processing article {article.get('id', 'unknown')}: {e}")
                    continue
            
            logger.info(f"Successfully processed and saved {processed_count} articles")
        else:
            logger.warning("No articles were fetched")
        
        logger.info("Scheduled archiver job completed successfully")
        
    except Exception as e:
        logger.error(f"Error in scheduled archiver job: {e}")


def main():
    """
    Main function to set up and run the scheduler.
    """
    logger.info("Feedly to Google Drive Archiver Scheduler starting...")
    
    # Load environment variables
    load_dotenv()
    
    # Get schedule configuration from environment variables
    schedule_hour = int(os.getenv("SCHEDULE_HOUR", 9))  # Default to 9 AM
    schedule_minute = int(os.getenv("SCHEDULE_MINUTE", 0))  # Default to 0 minutes
    
    # Set up the schedule
    schedule_time = f"{schedule_hour:02d}:{schedule_minute:02d}"
    schedule.every().day.at(schedule_time).do(run_archiver_job)
    
    logger.info(f"Scheduler configured to run daily at {schedule_time}")
    logger.info("Scheduler is now running. Press Ctrl+C to stop.")
    
    # Run the job once immediately for testing
    logger.info("Running initial job...")
    run_archiver_job()
    
    # Keep the scheduler running
    try:
        while True:
            schedule.run_pending()
            time.sleep(60)  # Check every minute
    except KeyboardInterrupt:
        logger.info("Scheduler stopped by user")
    except Exception as e:
        logger.error(f"Scheduler error: {e}")


if __name__ == "__main__":
    main()
