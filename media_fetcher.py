import re
from lxml import html
from functools import lru_cache

# Pre-compile regular expressions
youtube_regex = re.compile(r'(?:youtube\.com/watch\?v=|youtu\.be/)([\w-]+)')

def find_first_img_src(tree):
    """
    Find the first image source in the given HTML tree.

    :param tree: The parsed HTML tree.
    :return: The src attribute of the first img tag, or None if not found.
    """
    return next((element.get('src') for element in tree.iter('img')), None) if tree is not None else None

@lru_cache(maxsize=1000)
def fetch_media(entry):
    """
    Fetch media information from a feed entry.

    :param entry: The feed entry.
    :return: A tuple containing the HTML tree, content, thumbnail, video, and additional info.
    """
    # Extract basic information
    url = getattr(entry, 'link', '')

    content = ''
    if 'content' in entry and isinstance(entry['content'], list) and entry['content']:
        content = entry['content'][0].get('value', '')  # Assumes the first item in 'content' list is the full content
    if not content:
        content = getattr(entry, 'summary', '')
    tree = html.fromstring(content) if content else None

    additional_info = {
        'web_name': [],
        'tags': [tag['term'] for tag in entry.get('tags', [])],
        'creator': entry.get('author', '')
    }

    # Determine the media type and thumbnail
    thumbnail, video = determine_media(url, tree, entry)

    return tree, content, thumbnail, video, additional_info

def determine_media(url, tree, entry):
    """
    Determine the media type and thumbnail for a feed entry.

    :param url: The URL of the feed entry.
    :param tree: The parsed HTML tree.
    :param entry: The feed entry.
    :return: A tuple containing the thumbnail and video.
    """
    thumbnail = None
    video = None

    if "reddit.com" in url:
        video = "reddit"

    media_thumbnail = getattr(entry, 'media_thumbnail', None)

    # Extract the URL from the first dictionary in the media_thumbnail list
    thumbnail_url = None
    if media_thumbnail and isinstance(media_thumbnail, list) and media_thumbnail:
        first_thumbnail = media_thumbnail[0]  # Get the first item in the list
        thumbnail_url = first_thumbnail.get('url')
    
    thumbnail = thumbnail_url or find_first_img_src(tree)
    if ("youtube.com" in url or "youtu.be" in url):
        match = youtube_regex.search(url)
        if match:
            video = match.group(1)
            if not thumbnail:
                thumbnail = f"https://img.youtube.com/vi/{video}/maxresdefault.jpg"

    return thumbnail, video