#!/usr/bin/env python3
"""
Feedly to Google Drive Archiver

This module implements the core functionality to fetch articles from Feedly API
and archive them to Google Drive as JSON files.
"""

import os
import json
import logging
import requests
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from pathvalidate import sanitize_filename

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def fetch_feedly_articles(api_token: str, stream_id: str, newer_than_timestamp_ms: int) -> List[Dict]:
    """
    Fetch articles from Feedly API with pagination support.
    
    Args:
        api_token: Feedly API access token
        stream_id: Feedly stream ID to fetch articles from
        newer_than_timestamp_ms: Timestamp in milliseconds to filter newer articles
        
    Returns:
        List of article dictionaries containing id, title, alternate, published, engagement
    """
    base_url = "https://cloud.feedly.com/v3/streams/contents"
    headers = {
        "Authorization": f"Bearer {api_token}",
        "Content-Type": "application/json"
    }
    
    all_articles = []
    continuation = None
    
    try:
        while True:
            # Build request parameters
            params = {
                "streamId": stream_id,
                "count": 100,  # Maximum articles per request
                "newerThan": newer_than_timestamp_ms
            }
            
            # Add continuation parameter for pagination
            if continuation:
                params["continuation"] = continuation
            
            logger.info(f"Fetching articles from Feedly API. Stream: {stream_id}, Params: {params}")
            
            # Make API request
            response = requests.get(base_url, headers=headers, params=params)
            
            # Check for HTTP errors
            if response.status_code != 200:
                logger.error(f"Feedly API request failed with status {response.status_code}: {response.text}")
                if response.status_code == 401:
                    logger.error("Authentication failed. Please check your Feedly access token.")
                elif response.status_code == 429:
                    logger.error("Rate limit exceeded. Please try again later.")
                break
            
            # Parse response
            data = response.json()
            items = data.get("items", [])
            
            if not items:
                logger.info("No more articles found.")
                break
            
            # Extract relevant fields from each article
            for item in items:
                article = {
                    "id": item.get("id", ""),
                    "title": item.get("title", ""),
                    "published": item.get("published", 0),
                    "engagement": item.get("engagement", 0)
                }
                
                # Extract URL from alternate array (looking for text/html type)
                alternate_links = item.get("alternate", [])
                url = ""
                for link in alternate_links:
                    if link.get("type") == "text/html":
                        url = link.get("href", "")
                        break
                
                article["alternate"] = url
                all_articles.append(article)
            
            logger.info(f"Fetched {len(items)} articles in this batch. Total so far: {len(all_articles)}")
            
            # Check for continuation token
            continuation = data.get("continuation")
            if not continuation:
                logger.info("No continuation token found. Finished fetching all articles.")
                break
        
        logger.info(f"Successfully fetched {len(all_articles)} articles from Feedly API")
        return all_articles
        
    except requests.exceptions.RequestException as e:
        logger.error(f"Network error while fetching from Feedly API: {e}")
        return []
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse JSON response from Feedly API: {e}")
        return []
    except Exception as e:
        logger.error(f"Unexpected error while fetching from Feedly API: {e}")
        return []


def transform_to_json_structure(article_data: Dict) -> Dict:
    """
    Transform Feedly article data to the desired JSON structure.
    
    Args:
        article_data: Dictionary containing article data from Feedly API
        
    Returns:
        Dictionary with transformed structure (title, url, starCount, publishedDate)
    """
    try:
        # Convert timestamp from milliseconds to ISO 8601 format
        published_timestamp = article_data.get("published", 0)
        if published_timestamp:
            published_date = datetime.utcfromtimestamp(published_timestamp / 1000).isoformat() + 'Z'
        else:
            published_date = ""
        
        transformed = {
            "title": article_data.get("title", ""),
            "url": article_data.get("alternate", ""),
            "starCount": article_data.get("engagement", 0),
            "publishedDate": published_date
        }
        
        return transformed
        
    except Exception as e:
        logger.error(f"Error transforming article data: {e}")
        return {
            "title": "",
            "url": "",
            "starCount": 0,
            "publishedDate": ""
        }


def generate_safe_filename(article: Dict) -> str:
    """
    Generate a safe filename for the article JSON file.
    
    Args:
        article: Article dictionary containing id and published timestamp
        
    Returns:
        Safe filename string
    """
    try:
        # Extract date from published timestamp
        published_timestamp = article.get("published", 0)
        if published_timestamp:
            date_str = datetime.utcfromtimestamp(published_timestamp / 1000).strftime('%Y%m%d')
        else:
            date_str = "unknown"
        
        # Sanitize article ID for filename
        article_id = article.get("id", "unknown")
        safe_id = sanitize_filename(article_id)
        
        # Create filename
        filename = f"{date_str}_{safe_id}.json"
        
        return filename
        
    except Exception as e:
        logger.error(f"Error generating filename: {e}")
        return f"article_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"


if __name__ == "__main__":
    # This section is for local testing
    from dotenv import load_dotenv
    
    # Load environment variables from .env file
    load_dotenv()
    
    # Get configuration from environment variables
    feedly_token = os.getenv("FEEDLY_ACCESS_TOKEN")
    stream_id = os.getenv("FEEDLY_STREAM_ID")
    fetch_period_days = int(os.getenv("FETCH_PERIOD_DAYS", 7))
    
    if not feedly_token or not stream_id:
        logger.error("Required environment variables are missing. Please check your .env file.")
        exit(1)
    
    # Calculate timestamp for filtering (fetch articles from the last N days)
    now = datetime.now()
    older_than_date = now - timedelta(days=fetch_period_days)
    newer_than_timestamp_ms = int(older_than_date.timestamp() * 1000)
    
    logger.info(f"Fetching articles newer than: {older_than_date.isoformat()}")
    
    # Fetch articles from Feedly
    articles = fetch_feedly_articles(feedly_token, stream_id, newer_than_timestamp_ms)
    
    if articles:
        logger.info(f"Processing {len(articles)} articles...")
        
        for article in articles:
            # Transform article data
            transformed_article = transform_to_json_structure(article)
            
            # Generate safe filename
            filename = generate_safe_filename(article)
            
            # Convert to JSON string
            json_data = json.dumps(transformed_article, indent=2, ensure_ascii=False)
            
            logger.info(f"Processed article: {filename}")
            logger.info(f"Title: {transformed_article['title']}")
            logger.info(f"URL: {transformed_article['url']}")
            logger.info(f"Published: {transformed_article['publishedDate']}")
            logger.info("---")
    else:
        logger.warning("No articles were fetched.")
