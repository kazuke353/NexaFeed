
from rss_fetcher import RSSFetcher
from fuzzywuzzy import fuzz
import time

class Feed:
    def __init__(self, db_manager, config_manager):
        self.rss_fetcher = None
        self.db_manager = db_manager
        self.config_manager = config_manager
        self.urls = None
        self.feed = False
    
    async def init_fetch(self, category):
        start_time = time.time()
        if not self.rss_fetcher:
            self.rss_fetcher = RSSFetcher(self.db_manager)
        
        self.urls = self.config_manager.get(f'{category}_feed_urls', [])
        pool = await self.db_manager.get_pool()
        try:
            failed_urls, rate_limited_urls = await self.rss_fetcher.fetch_feeds(self.urls, pool)
        except ValueError:
            print("Error: init_fetch did not return enough values.")
        
        if rate_limited_urls:
            return False

        if self.config_manager.get_boolean("feed.autoclean", False) and not rate_limited_urls and failed_urls:
            # Remove failed feeds from the configuration
            self.rss_fetcher.remove_failed_feeds(self.config_manager, f'{category}_feed_urls', failed_urls)

        fetch_duration = time.time() - start_time
        print(f"Fetched in {fetch_duration:.2f} seconds")
        
        return True

    async def get_feed_items(self, category, limit, offset, search_query=""):
        start_time = time.time()
        feed_items = []

        if not self.feed:
            self.feed = await self.init_fetch(category)
            if not self.feed:
                return []  # Early exit if feed fetching fails

        feed_items = await self.rss_fetcher.get_feed(limit, offset)

        fetch_duration = time.time() - start_time
        print(f"Fetched in {fetch_duration:.2f} seconds")
        
        return feed_items
