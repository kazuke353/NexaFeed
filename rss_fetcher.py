import asyncio
from aiohttp import ClientSession, TCPConnector
from collections import deque
from datetime import datetime, timezone, timedelta
from dateutil.parser import parse
import feedparser
from user_agent import generate_user_agent
from cache_manager import Cache
from media_fetcher import fetch_media

class RSSFetcher:
    def __init__(self, config_manager=None, max_workers=20):
        self.max_workers = max_workers
        self.session = None
        self.clients = {}
        self.cache = Cache(config_manager).get()
        self.date_attributes = ['published', 'pubDate', 'updated']
    
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
        try:
            dt = parse(date_str)
            if dt.tzinfo is None or dt.tzinfo.utcoffset(dt) is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt
        except (ValueError, TypeError):
            return None
    
    async def fetch_content_from_url(self, url):
        async with self.session.get(url) as response:
            return await response.text()
    
    async def process_entry(self, entry):
        original_link = getattr(entry, 'link', '')
        published_date = getattr(entry, 'published_date', '')
        if not published_date:
            print(f"No valid published date for entry in {original_link}")
            return None

        tree, summary, thumbnail, video_id, additional_info = fetch_media(entry)
        title = getattr(entry, 'title', '')
        summary = tree.text_content()[:100] if tree is not None else summary
        content = getattr(entry, 'content', [{}])[0].get('value', summary)

        return {
            'title': title,
            'content': content,
            'summary': summary,
            'thumbnail': thumbnail,
            'video_id': video_id,
            'additional_info': additional_info,
            'published_date': published_date,
            'original_link': original_link
        }

    async def process_entries_range(self, cached_feed, start, end):
        entries_to_process = cached_feed[start:end]
        tasks = [asyncio.create_task(self.process_entry(entry)) for entry in entries_to_process]
        processed_entries = await asyncio.gather(*tasks)
        return [entry for entry in processed_entries if entry is not None]

    async def fetch_single_feed(self, url):
        # Check if the result is in cache
        cached_feed = self.cache.get(url)
        if cached_feed is not None:
            return 200, cached_feed

        if self.rate_limit(url, 1, 60):
            return 429, []

        if not self.session:
            self.session = ClientSession(connector=TCPConnector(keepalive_timeout=30, ssl=False), 
                                        headers={'User-Agent': generate_user_agent()})

        try:
            async with self.session.get(url) as response:
                text = await response.text()
                feed = feedparser.parse(text)
                self.cache[url] = feed.entries  # Cache raw entries
                return 200, feed.entries
        except Exception as e:
            print(f"An error occurred while fetching {url}: {e}")
            return 443, []

    async def fetch_feeds(self, urls):
        if not urls:
            print("The 'urls' parameter is empty.")
            return 444, []  # You can use a different status code for an empty URL list

        tasks = deque()
        fetched_feeds = []
        successful_urls = set()
        failed_urls = set()
        rate_limited_urls = set()
        overall_status_code = 200  # Default status code

        async def fetch_and_append(url):
            nonlocal overall_status_code  # Access the outer variable
            code, feed = await self.fetch_single_feed(url)
            if code == 200 and feed:
                fetched_feeds.append(feed)
                successful_urls.add(url)
            elif code == 429:  # Assuming 449 is your rate limit code
                rate_limited_urls.add(url)
                overall_status_code = 429  # Update overall status if rate limited
            else:
                failed_urls.add(url)
                overall_status_code = 443  # Update overall status for generic failure

        for url in urls:
            task = asyncio.ensure_future(fetch_and_append(url))
            tasks.append(task)

        await asyncio.gather(*tasks)

        # Flatten the list of feeds and process dates simultaneously
        all_feeds = []
        for sublist in fetched_feeds:
            for entry in sublist:
                # Parse the date and store it in entry.published_date
                entry.published_date = next(
                    (self.parse_date(getattr(entry, attr, '')) for attr in self.date_attributes if getattr(entry, attr, '')),
                    datetime.min.replace(tzinfo=timezone.utc)
                )
                all_feeds.append(entry)

        # Now sort based on the stored dates
        all_feeds.sort(key=lambda entry: entry.published_date, reverse=True)

        return overall_status_code, all_feeds, successful_urls, failed_urls, rate_limited_urls
    
    def remove_failed_feeds(self, config_manager, category, failed_urls):
        if config_manager and category and failed_urls:
            existing_feeds = set(config_manager.config_data.get(category, []))
            updated_feeds = existing_feeds - failed_urls
            config_manager.overwrite_category_data(category, list(updated_feeds))
            print("Removed the following feeds: ", failed_urls)