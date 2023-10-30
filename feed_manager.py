from rss_fetcher import RSSFetcher
from fuzzywuzzy import fuzz
import time

class Feed:
    def __init__(self, config_manager):
        self.rss_fetcher = None
        self.config_manager = config_manager
        self.urls = None
        self.feed = []
    
    async def init_fetch(self, category):
        start_time = time.time()
        if not self.rss_fetcher:
            self.rss_fetcher = RSSFetcher(self.config_manager)
        
        self.urls = self.config_manager.get(f'{category}_feed_urls', [])
        try:
            overall_status_code, feed_items, successful_urls, failed_urls, rate_limited_urls = await self.rss_fetcher.fetch_feeds(self.urls)
        except ValueError:
            print("Error: init_fetch did not return enough values.")
            feed_items = []
        
        if rate_limited_urls or overall_status_code == 429:
            return []

        if self.config_manager.get_boolean("feed.autoclean", False) and overall_status_code != 429:
            # Remove failed feeds from the configuration
            self.rss_fetcher.remove_failed_feeds(self.config_manager, f'{category}_feed_urls', failed_urls)

        fetch_duration = time.time() - start_time
        print(f"Fetched in {fetch_duration:.2f} seconds")
        
        return feed_items

    async def get_feed_items(self, category, start, end, search_query=""):
        start_time = time.time()
        feed_items = []

        if not self.feed:
            self.feed = await self.init_fetch(category)
            if not self.feed:
                return []  # Early exit if feed fetching fails

        if search_query:
            search_query_lower = search_query.lower()
            filtered_feed = [
                entry for entry in self.feed if any(
                    fuzz.partial_ratio(search_query_lower, entry[field].lower()) > 70 if field in entry else False
                    for field in ['title', 'summary']
                ) or (
                    fuzz.partial_ratio(search_query_lower, entry.get('additional_info', {}).get('creator', '').lower()) > 70
                )
            ]
        else:
            filtered_feed = self.feed

        # Validate range
        start = max(0, min(start, len(filtered_feed)))
        end = max(start, min(end, len(filtered_feed)))

        feed_items = await self.rss_fetcher.process_entries_range(filtered_feed, start, end)

        fetch_duration = time.time() - start_time
        print(f"Fetched in {fetch_duration:.2f} seconds")
        
        return feed_items
