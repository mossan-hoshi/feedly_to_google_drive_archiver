#!/usr/bin/env python3
"""
Test script for Google Drive API client functionality

This script tests the Google Drive upload functionality with a sample JSON file.
"""

import os
import json
import logging
from datetime import datetime
from dotenv import load_dotenv
from main import upload_to_google_drive

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def test_google_drive_upload():
    """Test Google Drive upload functionality with a sample file."""
    
    # Load environment variables
    load_dotenv()
    
    # Get configuration
    folder_id = os.getenv("GOOGLE_DRIVE_FOLDER_ID")
    service_account_file = os.getenv("GOOGLE_SERVICE_ACCOUNT_FILE")
    
    if not folder_id:
        logger.error("GOOGLE_DRIVE_FOLDER_ID environment variable is not set")
        return False
    
    if not service_account_file:
        logger.error("GOOGLE_SERVICE_ACCOUNT_FILE environment variable is not set")
        return False
    
    if not os.path.exists(service_account_file):
        logger.error(f"Service account file does not exist: {service_account_file}")
        return False
    
    # Create sample JSON data
    sample_article = {
        "title": "Test Article for Google Drive Upload",
        "url": "https://example.com/test-article",
        "starCount": 42,
        "publishedDate": datetime.now().isoformat() + 'Z'
    }
    
    # Convert to JSON string
    json_data = json.dumps(sample_article, indent=2, ensure_ascii=False)
    
    # Generate test filename
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f"test_upload_{timestamp}.json"
    
    logger.info("Starting Google Drive upload test...")
    logger.info(f"Folder ID: {folder_id}")
    logger.info(f"Service Account File: {service_account_file}")
    logger.info(f"Test Filename: {filename}")
    
    # Attempt upload
    file_id = upload_to_google_drive(
        service_account_file,
        folder_id,
        filename,
        json_data
    )
    
    if file_id:
        logger.info(f"✅ Test successful! File uploaded with ID: {file_id}")
        logger.info(f"📁 File URL: https://drive.google.com/file/d/{file_id}/view")
        return True
    else:
        logger.error("❌ Test failed! Could not upload file to Google Drive")
        return False


if __name__ == "__main__":
    logger.info("=" * 60)
    logger.info("GOOGLE DRIVE API CLIENT TEST")
    logger.info("=" * 60)
    
    success = test_google_drive_upload()
    
    logger.info("=" * 60)
    if success:
        logger.info("🎉 All tests passed!")
    else:
        logger.error("💥 Test failed. Please check your configuration.")
    logger.info("=" * 60)
