#!/usr/bin/env python3
"""
Feedly API test script to check user profile and valid stream IDs
"""

import os
import requests
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

feedly_token = os.getenv("FEEDLY_ACCESS_TOKEN")

def test_user_profile():
    """Test Feedly user profile endpoint"""
    url = "https://cloud.feedly.com/v3/profile"
    headers = {
        "Authorization": f"Bearer {feedly_token}"
    }
    
    try:
        response = requests.get(url, headers=headers)
        print(f"Profile API Status: {response.status_code}")
        if response.status_code == 200:
            profile_data = response.json()
            print("User Profile:")
            print(f"  ID: {profile_data.get('id')}")
            print(f"  Email: {profile_data.get('email')}")
            print(f"  Full Name: {profile_data.get('fullName')}")
        else:
            print(f"Error: {response.text}")
    except Exception as e:
        print(f"Exception: {e}")

def test_subscriptions():
    """Test Feedly subscriptions endpoint"""
    url = "https://cloud.feedly.com/v3/subscriptions"
    headers = {
        "Authorization": f"Bearer {feedly_token}"
    }
    
    try:
        response = requests.get(url, headers=headers)
        print(f"\nSubscriptions API Status: {response.status_code}")
        if response.status_code == 200:
            subscriptions = response.json()
            print(f"Number of subscriptions: {len(subscriptions)}")
            if subscriptions:
                print("First few subscriptions:")
                for i, sub in enumerate(subscriptions[:3]):
                    print(f"  {i+1}. {sub.get('title')} - ID: {sub.get('id')}")
        else:
            print(f"Error: {response.text}")
    except Exception as e:
        print(f"Exception: {e}")

def test_categories():
    """Test Feedly categories endpoint"""
    url = "https://cloud.feedly.com/v3/categories"
    headers = {
        "Authorization": f"Bearer {feedly_token}"
    }
    
    try:
        response = requests.get(url, headers=headers)
        print(f"\nCategories API Status: {response.status_code}")
        if response.status_code == 200:
            categories = response.json()
            print(f"Number of categories: {len(categories)}")
            if categories:
                print("Categories:")
                for category in categories:
                    print(f"  - {category.get('label')} - ID: {category.get('id')}")
        else:
            print(f"Error: {response.text}")
    except Exception as e:
        print(f"Exception: {e}")

if __name__ == "__main__":
    print("Testing Feedly API endpoints...")
    test_user_profile()
    test_subscriptions()
    test_categories()
