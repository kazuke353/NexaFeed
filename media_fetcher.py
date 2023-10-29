import re
from bs4 import BeautifulSoup
from functools import lru_cache
import requests
from user_agent import generate_user_agent
from urllib.parse import urlsplit, urlunsplit

# Pre-compile regular expressions
youtube_regex = re.compile(r'v=([A-Za-z0-9_-]+)')

@lru_cache(maxsize=1000)
def fetch_media(entry):
    thumbnail = None
    video = None
    additional_info = {
        'tags': [tag['term'] for tag in entry.get('tags', [])],
        'creator': entry.get('author', '')
    }
    url = entry.link

    soup = BeautifulSoup(entry.summary, 'lxml')
    thumbnail_tag = soup.find('img')
    thumbnail = thumbnail_tag['src'] if thumbnail_tag else None

    if "reddit.com" in url:
        video = "XD"

    if not thumbnail:
        if "youtube.com" in url:
            match = youtube_regex.search(url)
            if match:
                video = match.group(1)
                thumbnail = f"https://img.youtube.com/vi/{video}/hqdefault.jpg"

    return thumbnail, video, additional_info