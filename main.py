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
from io import BytesIO
import google.auth
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload

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
                alternate_links = item.get("alternate", [])
                url = ""
                for link in alternate_links:
                    if link.get("type") == "text/html":
                        url = link.get("href", "")
                        break
                
                all_articles.append({
                    "id": item.get("id", ""),
                    "title": item.get("title", ""),
                    "published": item.get("published", 0),
                    "engagement": item.get("engagement", 0),
                    "alternate": url
                })
            
            continuation = data.get("continuation")
            if not continuation:
                break
        
        return all_articles
        
    except Exception as e:
        logger.error(f"Error while fetching from Feedly API: {e}")
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


def generate_batch_filename() -> str:
    """Generate filename for batch of articles"""
    try:
        current_time = datetime.now()
        return f"feedly_articles_{current_time.strftime('%Y%m%d_%H%M%S')}.json"
    except Exception as e:
        logger.error(f"Error generating filename: {e}")
        return f"feedly_articles_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"


def upload_to_google_drive_adc(folder_id: str, file_name: str, json_data_string: str) -> Optional[str]:
    try:
        credentials, project = google.auth.default(scopes=['https://www.googleapis.com/auth/drive.file'])
        service = build('drive', 'v3', credentials=credentials)
        
        file_metadata = {'name': file_name, 'parents': [folder_id]}
        media_body = MediaIoBaseUpload(BytesIO(json_data_string.encode('utf-8')), mimetype='application/json', resumable=True)
        
        file_result = service.files().create(body=file_metadata, media_body=media_body, fields='id').execute()
        return file_result.get('id')
        
    except Exception as e:
        logger.error(f"Error uploading to Google Drive using ADC: {e}")
        return None


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
    try:
        logger.info("Feedly archiver function started")
        
        feedly_token = os.environ.get("FEEDLY_ACCESS_TOKEN")
        stream_id = os.environ.get("FEEDLY_STREAM_ID") 
        google_drive_folder_id = os.environ.get("GOOGLE_DRIVE_FOLDER_ID")
        
        try:
            fetch_period_days = int(os.environ.get("FETCH_PERIOD_DAYS", "7"))
        except ValueError:
            logger.warning("FETCH_PERIOD_DAYS is not a valid integer, using default value of 7")
            fetch_period_days = 7
        
        if not feedly_token:
            logger.error("FEEDLY_ACCESS_TOKEN environment variable is missing")
            return {"error": "FEEDLY_ACCESS_TOKEN environment variable is missing"}, 400
        if not stream_id:
            logger.error("FEEDLY_STREAM_ID environment variable is missing")
            return {"error": "FEEDLY_STREAM_ID environment variable is missing"}, 400
        if not google_drive_folder_id:
            logger.error("GOOGLE_DRIVE_FOLDER_ID environment variable is missing")
            return {"error": "GOOGLE_DRIVE_FOLDER_ID environment variable is missing"}, 400
        
        # Log configuration
        logger.info(f"Configuration: Stream ID: {stream_id[:20]}..., Folder ID: {google_drive_folder_id}, Period: {fetch_period_days} days")
        
        older_than_date = datetime.now() - timedelta(days=fetch_period_days)
        newer_than_timestamp_ms = int(older_than_date.timestamp() * 1000)
        logger.info(f"Fetching articles newer than: {older_than_date.isoformat()} (timestamp: {newer_than_timestamp_ms})")
        
        logger.info("Starting article fetch from Feedly API")
        articles = fetch_feedly_articles(feedly_token, stream_id, newer_than_timestamp_ms)
        
        if not articles:
            logger.info("No articles were fetched from Feedly")
            return {"message": "No articles were fetched from Feedly", "articles_processed": 0}, 200
        
        logger.info(f"Successfully fetched {len(articles)} articles from Feedly")
        
        # Transform all articles to JSON structure
        transformed_articles = []
        for article in articles:
            try:
                transformed_article = transform_to_json_structure(article)
                transformed_articles.append(transformed_article)
            except Exception as e:
                logger.error(f"Error transforming article {article.get('id', 'unknown')}: {e}")
        
        if not transformed_articles:
            logger.warning("No articles were successfully transformed")
            return {"message": "No articles were successfully transformed", "articles_processed": 0}, 200
        
        # Create batch JSON data
        batch_data = {
            "fetch_date": datetime.now().isoformat() + 'Z',
            "total_articles": len(transformed_articles),
            "articles": transformed_articles
        }
        
        filename = generate_batch_filename()
        json_data = json.dumps(batch_data, indent=2, ensure_ascii=False)
        
        logger.info(f"Starting upload of batch file: {filename}")
        
        file_id = upload_to_google_drive_adc(google_drive_folder_id, filename, json_data)
        
        if file_id:
            success_message = f"Feedly archiver function completed: Batch file uploaded successfully with {len(transformed_articles)} articles"
            logger.info(f"Successfully uploaded batch file: {filename} (ID: {file_id})")
            
            return {
                "message": success_message,
                "articles_fetched": len(articles),
                "articles_processed": len(transformed_articles),
                "batch_file": {
                    "filename": filename,
                    "file_id": file_id,
                    "article_count": len(transformed_articles)
                }
            }, 200
        else:
            error_message = f"Failed to upload batch file: {filename}"
            logger.error(error_message)
            return {"error": error_message}, 500
        
    except Exception as e:
        logger.error(f"Unexpected error in main function: {e}")
        return {"error": f"Unexpected error in main function: {e}"}, 500


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
        # Transform all articles to JSON structure
        transformed_articles = []
        for article in articles:
            try:
                transformed_article = transform_to_json_structure(article)
                transformed_articles.append(transformed_article)
            except Exception as e:
                logger.error(f"Error transforming article {article.get('id', 'unknown')}: {e}")
        
        if transformed_articles:
            # Create batch JSON data
            batch_data = {
                "fetch_date": datetime.now().isoformat() + 'Z',
                "total_articles": len(transformed_articles),
                "articles": transformed_articles
            }
            
            filename = generate_batch_filename()
            json_data = json.dumps(batch_data, indent=2, ensure_ascii=False)
            
            if google_drive_folder_id and service_account_file:
                file_id = upload_to_google_drive(service_account_file, google_drive_folder_id, filename, json_data)
                if file_id:
                    logger.info(f"Successfully uploaded batch file: {filename} (ID: {file_id}) with {len(transformed_articles)} articles")
                else:
                    logger.error(f"Failed to upload batch file: {filename}")
            else:
                logger.info(f"Would upload batch file: {filename} with {len(transformed_articles)} articles")
        
        logger.info(f"Processed: {len(articles)} articles fetched, {len(transformed_articles)} articles transformed")
    else:
        logger.warning("No articles were fetched.")
