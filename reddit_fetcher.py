from functools import lru_cache
import requests
from user_agent import generate_user_agent
from urllib.parse import urlsplit, urlunsplit

@lru_cache(maxsize=1000)
def fetch_reddit_media(url):
    video = None

    if "reddit.com" in url:
        # Convert Reddit URL to JSON endpoint
        parts = urlsplit(url)
        new_path = f"{parts.path.rstrip('/')}.json"
        json_url = urlunsplit((parts.scheme, parts.netloc, new_path, parts.query, parts.fragment))
        
        try:
            response = requests.get(json_url, headers={'User-agent': generate_user_agent()})
            if response.status_code == 200:
                reddit_json = response.json()
                submission_data = reddit_json[0]['data']['children'][0]['data']
                
                media_data = submission_data.get('media')
                if media_data:
                    video = media_data.get('reddit_video', {}).get('fallback_url')
                else:
                    preview_data = submission_data.get('preview', {}).get('images', [{}])[0].get('source', {}).get('url')
                    if preview_data:
                        video = preview_data
                
                print(video)
            else:
                print(f"Failed to fetch Reddit data with status code: {response.status_code}")
        except Exception as e:
            print(f"Failed to fetch Reddit data: {e}")

    return video