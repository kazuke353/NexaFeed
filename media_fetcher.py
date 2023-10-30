import re
from lxml import html
from functools import lru_cache

# Pre-compile regular expressions
youtube_regex = re.compile(r'v=([A-Za-z0-9_-]+)')

def find_first_img_src(tree):
    for element in tree.iter():
        if element.tag == 'img':
            return element.get('src')
    return None

@lru_cache(maxsize=1000)
def fetch_media(entry):
    thumbnail = None
    video = None
    additional_info = {
        'tags': [tag['term'] for tag in entry.get('tags', [])],
        'creator': entry.get('author', '')
    }
    url = entry.link

    summary = getattr(entry, 'summary', '')
    tree = html.fromstring(summary) if summary else None
    thumbnail = find_first_img_src(tree) if tree else None

    if "reddit.com" in url:
        video = "reddit"

    if not thumbnail:
        if "youtube.com" in url:
            match = youtube_regex.search(url)
            if match:
                video = match.group(1)
                thumbnail = f"https://img.youtube.com/vi/{video}/hqdefault.jpg"

    return tree, summary, thumbnail, video, additional_info