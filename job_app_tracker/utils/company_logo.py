import requests
from urllib.parse import urlparse
import logging

def get_company_logo_url(url):
    """
    Extract company logo (favicon) URL from a given website URL.
    Returns None if unable to fetch the logo.
    """
    if not url:
        return None
    
    try:
        # Parse the URL to get the base domain
        parsed_url = urlparse(url)
        base_url = f"{parsed_url.scheme}://{parsed_url.netloc}"
        
        # First try Google Favicon service
        google_favicon_url = f"https://www.google.com/s2/favicons?domain={base_url}&sz=128"
        
        # Test if the favicon exists
        response = requests.head(google_favicon_url)
        if response.status_code == 200:
            return google_favicon_url
            
        # Fallback to direct favicon.ico
        favicon_url = f"{base_url}/favicon.ico"
        response = requests.head(favicon_url)
        if response.status_code == 200:
            return favicon_url
            
    except Exception as e:
        logging.error(f"Error fetching company logo for {url}: {str(e)}")
        
    return None 