"""
Feedly to Google Drive Archiver

Cloud Function Entry Point: main(request)
Local Testing: Run this file directly with `python main.py`

Environment Variables Required:
- FEEDLY_ACCESS_TOKEN: Feedly API access token
- FEEDLY_STREAM_ID: Feedly stream ID to fetch articles from
- GOOGLE_DRIVE_FOLDER_ID: Google Drive folder ID for uploads
- FETCH_PERIOD_DAYS: Number of days to look back for articles (default: 7)
- GCP_PROJECT_ID: Google Cloud Project ID (for Cloud Function deployment)

Local Testing Additional Variables:
- GOOGLE_SERVICE_ACCOUNT_FILE: Path to service account JSON file (local only)
"""

import os
import json
import logging
import requests
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from pathvalidate import sanitize_filename
from io import BytesIO
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
from googleapiclient.errors import HttpError

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def fetch_feedly_articles(api_token: str, stream_id: str, newer_than_timestamp_ms: int) -> List[Dict]:
    base_url = "https://cloud.feedly.com/v3/streams/contents"
    headers = {"Authorization": f"Bearer {api_token}", "Content-Type": "application/json"}
    all_articles = []
    continuation = None
    
    try:
        while True:
            params = {"streamId": stream_id, "count": 100, "newerThan": newer_than_timestamp_ms}
            if continuation:
                params["continuation"] = continuation
            
            response = requests.get(base_url, headers=headers, params=params)
            
            if response.status_code != 200:
                logger.error(f"Feedly API request failed with status {response.status_code}")
                break
            
            data = response.json()
            items = data.get("items", [])
            if not items:
                break
            
            for item in items:
                article = {
                    "id": item.get("id", ""),
                    "title": item.get("title", ""),
                    "published": item.get("published", 0),
                    "engagement": item.get("engagement", 0)
                }
                
                alternate_links = item.get("alternate", [])
                url = ""
                for link in alternate_links:
                    if link.get("type") == "text/html":
                        url = link.get("href", "")
                        break
                
                article["alternate"] = url
                all_articles.append(article)
            
            continuation = data.get("continuation")
            if not continuation:
                break
        
        return all_articles
        
    except requests.exceptions.RequestException as e:
        logger.error(f"Network error while fetching from Feedly API: {e}")
        return []
    except Exception as e:
        logger.error(f"Unexpected error while fetching from Feedly API: {e}")
        return []


def transform_to_json_structure(article_data: Dict) -> Dict:
    try:
        published_timestamp = article_data.get("published", 0)
        published_date = datetime.utcfromtimestamp(published_timestamp / 1000).isoformat() + 'Z' if published_timestamp else ""
        
        return {
            "title": article_data.get("title", ""),
            "url": article_data.get("alternate", ""),
            "starCount": article_data.get("engagement", 0),
            "publishedDate": published_date
        }
    except Exception as e:
        logger.error(f"Error transforming article data: {e}")
        return {"title": "", "url": "", "starCount": 0, "publishedDate": ""}


def generate_safe_filename(article: Dict) -> str:
    try:
        published_timestamp = article.get("published", 0)
        date_str = datetime.utcfromtimestamp(published_timestamp / 1000).strftime('%Y%m%d') if published_timestamp else "unknown"
        safe_id = sanitize_filename(article.get("id", "unknown"))
        return f"{date_str}_{safe_id}.json"
    except Exception as e:
        logger.error(f"Error generating filename: {e}")
        return f"article_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"


def upload_to_google_drive(service_account_file_path: str, folder_id: str, file_name: str, json_data_string: str) -> Optional[str]:
    try:
        credentials = service_account.Credentials.from_service_account_file(
            service_account_file_path, scopes=['https://www.googleapis.com/auth/drive.file'])
        service = build('drive', 'v3', credentials=credentials)
        
        file_metadata = {'name': file_name, 'parents': [folder_id]}
        media_body = MediaIoBaseUpload(BytesIO(json_data_string.encode('utf-8')), mimetype='application/json', resumable=True)
        
        file_result = service.files().create(body=file_metadata, media_body=media_body, fields='id').execute()
        return file_result.get('id')
        
    except Exception as e:
        logger.error(f"Error uploading to Google Drive: {e}")
        return None


def main(request):
    """
    Cloud Function entry point for Feedly to Google Drive archiver.
    Triggered via HTTP request from Cloud Scheduler.
    """
    try:
        logger.info("Feedly archiver function started")
        
        # Read environment variables from GCP Cloud Function environment
        feedly_token = os.environ.get("FEEDLY_ACCESS_TOKEN")
        stream_id = os.environ.get("FEEDLY_STREAM_ID") 
        google_drive_folder_id = os.environ.get("GOOGLE_DRIVE_FOLDER_ID")
        gcp_project_id = os.environ.get("GCP_PROJECT_ID")
        
        # Parse FETCH_PERIOD_DAYS with error handling
        try:
            fetch_period_days = int(os.environ.get("FETCH_PERIOD_DAYS", "7"))
        except ValueError:
            logger.warning("FETCH_PERIOD_DAYS is not a valid integer, using default value of 7")
            fetch_period_days = 7
        
        # Validate required environment variables
        if not feedly_token:
            logger.error("FEEDLY_ACCESS_TOKEN environment variable is missing")
            return {"error": "FEEDLY_ACCESS_TOKEN environment variable is missing"}, 400
        if not stream_id:
            logger.error("FEEDLY_STREAM_ID environment variable is missing")
            return {"error": "FEEDLY_STREAM_ID environment variable is missing"}, 400
        if not google_drive_folder_id:
            logger.error("GOOGLE_DRIVE_FOLDER_ID environment variable is missing")
            return {"error": "GOOGLE_DRIVE_FOLDER_ID environment variable is missing"}, 400
            
        # Log configuration (GCP_PROJECT_ID is optional)
        logger.info(f"Configuration: Stream ID: {stream_id[:20]}..., Folder ID: {google_drive_folder_id}, Period: {fetch_period_days} days")
        if gcp_project_id:
            logger.info(f"GCP Project ID: {gcp_project_id}")
        
        # Calculate newer_than_timestamp_ms based on FETCH_PERIOD_DAYS
        older_than_date = datetime.now() - timedelta(days=fetch_period_days)
        newer_than_timestamp_ms = int(older_than_date.timestamp() * 1000)
        logger.info(f"Fetching articles newer than: {older_than_date.isoformat()} (timestamp: {newer_than_timestamp_ms})")
        
        # Fetch articles from Feedly API
        logger.info("Starting article fetch from Feedly API")
        articles = fetch_feedly_articles(feedly_token, stream_id, newer_than_timestamp_ms)
        
        if not articles:
            logger.info("No articles were fetched from Feedly")
            return {"message": "No articles were fetched from Feedly", "articles_processed": 0}, 200
        
        logger.info(f"Successfully fetched {len(articles)} articles from Feedly")
        
        # Process and upload articles
        upload_count = 0
        error_count = 0
        processed_files = []
        
        for i, article in enumerate(articles):
            try:
                logger.debug(f"Processing article {i+1}/{len(articles)}: {article.get('title', 'Untitled')[:50]}...")
                
                transformed_article = transform_to_json_structure(article)
                filename = generate_safe_filename(article)
                json_data = json.dumps(transformed_article, indent=2, ensure_ascii=False)
                
                # TODO 2.3 will modify this to use ADC (Application Default Credentials)
                service_account_file = "/tmp/service-account-key.json"
                
                file_id = upload_to_google_drive(service_account_file, google_drive_folder_id, filename, json_data)
                
                if file_id:
                    upload_count += 1
                    processed_files.append({
                        "filename": filename, 
                        "file_id": file_id, 
                        "title": transformed_article.get('title', 'Untitled')
                    })
                    logger.info(f"Successfully uploaded: {filename} (ID: {file_id})")
                else:
                    error_count += 1
                    logger.error(f"Failed to upload: {filename}")
                    
            except Exception as e:
                error_count += 1
                logger.error(f"Error processing article {article.get('id', 'unknown')}: {e}")
        
        # Return final results
        success_message = f"Feedly archiver function completed: {upload_count}/{len(articles)} files uploaded successfully"
        logger.info(success_message)
        
        return {
            "message": success_message,
            "articles_fetched": len(articles),
            "files_uploaded": upload_count,
            "upload_errors": error_count,
            "processed_files": processed_files
        }, 200
        
    except Exception as e:
        error_message = f"Unexpected error in main function: {e}"
        logger.error(error_message, exc_info=True)
        return {"error": error_message}, 500


if __name__ == "__main__":
    from dotenv import load_dotenv
    
    load_dotenv()
    
    feedly_token = os.getenv("FEEDLY_ACCESS_TOKEN")
    stream_id = os.getenv("FEEDLY_STREAM_ID")
    fetch_period_days = int(os.getenv("FETCH_PERIOD_DAYS", 7))
    google_drive_folder_id = os.getenv("GOOGLE_DRIVE_FOLDER_ID")
    service_account_file = os.getenv("GOOGLE_SERVICE_ACCOUNT_FILE")
    
    if not feedly_token or not stream_id:
        logger.error("Required environment variables are missing. Please check your .env file.")
        exit(1)
    
    older_than_date = datetime.now() - timedelta(days=fetch_period_days)
    newer_than_timestamp_ms = int(older_than_date.timestamp() * 1000)
    
    articles = fetch_feedly_articles(feedly_token, stream_id, newer_than_timestamp_ms)
    
    if articles:
        upload_count = 0
        error_count = 0
        
        for article in articles:
            transformed_article = transform_to_json_structure(article)
            filename = generate_safe_filename(article)
            json_data = json.dumps(transformed_article, indent=2, ensure_ascii=False)
            
            if google_drive_folder_id and service_account_file:
                file_id = upload_to_google_drive(service_account_file, google_drive_folder_id, filename, json_data)
                if file_id:
                    upload_count += 1
                else:
                    error_count += 1
        
        logger.info(f"Processed: {len(articles)}, Uploaded: {upload_count}, Errors: {error_count}")
    else:
        logger.warning("No articles were fetched.")
