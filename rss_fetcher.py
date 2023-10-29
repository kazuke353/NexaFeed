import asyncio
from aiohttp import ClientSession, TCPConnector
from bs4 import BeautifulSoup
from collections import deque
from datetime import datetime, timezone, timedelta
import feedparser
from user_agent import generate_user_agent
from cache_manager import Cache
from media_fetcher import fetch_media

class RSSFetcher:
    def __init__(self, max_workers=20):
        self.max_workers = max_workers
        self.session = None
        self.clients = {}
        self.cache = Cache.get()
    
    def rate_limit(self, client_id, limit, time_window):
        current_time = datetime.now()
        request_info = self.clients.get(client_id, {"count": 0, "time": current_time})

        # Reset count if time_window has passed
        if current_time - request_info["time"] > timedelta(seconds=time_window):
            request_info = {"count": 1, "time": current_time}
        else:
            request_info["count"] += 1

        self.clients[client_id] = request_info
        return request_info["count"] <= limit

    def parse_date(self, date_str):
        formats = [
            '%a, %d %b %Y %H:%M:%S %z',
            '%Y-%m-%dT%H:%M:%S%z',
            '%Y-%m-%dT%H:%M:%S.%f%z',
            '%a, %d %b %Y %H:%M:%S GMT'
        ]
        for fmt in formats:
            try:
                dt = datetime.strptime(date_str, fmt)
                if dt.tzinfo is None or dt.tzinfo.utcoffset(dt) is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                return dt
            except ValueError:
                continue
        return None

    async def fetch_single_feed(self, url):
        # Check if the result is in cache
        cached_feed = self.cache.get(url)
        if cached_feed is not None:
            return cached_feed

        if not self.rate_limit(url, 1, 60):
            print("Rate limit exceeded for:", url)
            return []

        if not self.session:
            self.session = ClientSession(connector=TCPConnector(keepalive_timeout=30, ssl=False), 
                                        headers={'User-Agent': generate_user_agent()})

        try:
            async with self.session.get(url) as response:
                text = await response.text()
                feed = feedparser.parse(text)
                fetched_feed = []
                
                for entry in feed.entries:
                    if not hasattr(entry, 'published') and not hasattr(entry, 'pubDate'):
                        print(f"No published date for entry in {url}")
                        continue
                    
                    published_date = self.parse_date(getattr(entry, 'published', '') or getattr(entry, 'pubDate', ''))
                    if published_date is None:
                        continue
                    title = getattr(entry, 'title', '')
                    summary = getattr(entry, 'summary', '')
                    content = getattr(entry, 'content', [{}])[0].get('value', summary)
                    summary = BeautifulSoup(summary, 'lxml').text[:100] if summary else ''
                    source = url
                    thumbnail, video_id, additional_info = fetch_media(entry)
                    original_link = getattr(entry, 'link', '')

                    fetched_feed.append({
                        'title': title,
                        'content': content,
                        'summary': summary,
                        'source': source,
                        'thumbnail': thumbnail,
                        'video_id': video_id,
                        'additional_info': additional_info,
                        'published_date': published_date,
                        'original_link': original_link
                    })
                self.cache[url] = fetched_feed
                return fetched_feed
        except Exception as e:
            print(f"An error occurred while fetching {url}: {e}")
            return []

    async def fetch_feeds(self, urls):
        if not urls:
            print("The 'urls' parameter is empty.")
            return []

        tasks = deque()
        fetched_feeds = []

        async def fetch_and_append(url):
            feed = await self.fetch_single_feed(url)
            if feed is not None:
                fetched_feeds.append(feed)

        for url in urls:
            task = asyncio.ensure_future(fetch_and_append(url))
            tasks.append(task)

        await asyncio.gather(*tasks)

        # Flatten and sort the list of feeds by their published date
        all_feeds = [entry for sublist in fetched_feeds for entry in sublist]
        all_feeds.sort(key=lambda x: x['published_date'], reverse=True)

        return all_feeds
    
    async def close(self):
        if self.session:
            await self.session.close()
