from rss_fetcher import RSSFetcher
from fuzzywuzzy import fuzz
import time

class Feed:
    def __init__(self, cache, config_manager):
        self.rss_fetcher = None
        self.cache = cache
        self.config_manager = config_manager

    async def get_feed_items(self, category, start, end, search_query=""):
        start_time = time.time()
        cache_key = f"{category}_{start}_{end}_{search_query}"
        if cache_key in self.cache:
            return self.cache[cache_key]
        if not self.rss_fetcher:
            self.rss_fetcher = RSSFetcher(self.config_manager)
        
        urls = self.config_manager.get(f'{category}_feed_urls', [])
        try:
            overall_status_code, feed_items, successful_urls, failed_urls, rate_limited_urls = await self.rss_fetcher.fetch_feeds(urls)
        except ValueError:
            print("Error: fetch_feeds did not return enough values.")
            feed_items = []
        
        if search_query:
            search_query_lower = search_query.lower()
            feed_items = [
                entry for entry in feed_items if any(
                    fuzz.partial_ratio(search_query_lower, entry[field].lower()) > 70 if field in entry else False
                    for field in ['title', 'summary']
                ) or (
                    fuzz.partial_ratio(search_query_lower, entry.get('additional_info', {}).get('creator', '').lower()) > 70
                )
            ]
        
        feed_items = feed_items[start:end] if feed_items else []

        # Save to cache
        self.cache[cache_key] = feed_items
        fetch_duration = time.time() - start_time

        if overall_status_code != 429:
            # Remove failed feeds from the configuration
            self.rss_fetcher.remove_failed_feeds(self.config_manager, f'{category}_feed_urls', failed_urls)

        print(f"Fetched in {fetch_duration:.2f} seconds")
        
        return feed_items