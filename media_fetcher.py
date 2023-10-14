import re
from bs4 import BeautifulSoup
from functools import lru_cache

# Pre-compile regular expressions
youtube_regex = re.compile(r'v=([A-Za-z0-9_-]+)')
pornhub_regex = re.compile(r'viewkey=([A-Za-z0-9_-]+)')

@lru_cache(maxsize=1000)
def fetch_media(entry):
    thumbnail = None
    video_id = None
    additional_info = {
        'tags': [tag['term'] for tag in entry.get('tags', [])],
        'creator': entry.get('author', '')
    }
    url = entry.link

    if "youtube.com" in url:
        match = youtube_regex.search(url)
        if match:
            video_id = match.group(1)
            thumbnail = f"https://img.youtube.com/vi/{video_id}/hqdefault.jpg"
    elif "pornhub.com" in url:
        match = pornhub_regex.search(url)
        if match:
            video_id = match.group(1)
            thumbnail = f"https://www.pornhub.com/embed/{video_id}/thumbnail.jpg"
    else:
        soup = BeautifulSoup(entry.summary, 'lxml')
        thumbnail_tag = soup.find('img')
        thumbnail = thumbnail_tag['src'] if thumbnail_tag else None

    return thumbnail, video_id, additional_info
