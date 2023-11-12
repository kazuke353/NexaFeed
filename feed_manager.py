from rss_fetcher import RSSFetcher
import time

class Feed:
    def __init__(self, db_manager, config_manager):
        self.rss_fetcher = None
        self.db_manager = db_manager
        self.config_manager = config_manager
        self.urls = None
    
    async def get_categories(self):
        categories = await self.db_manager.select_data("categories")
        return categories

    async def get_feeds(self, category):
        if not category:
            return []
        condition = {"category_id": category}
        feeds = await self.db_manager.select_data("feeds", condition)
        return feeds

    async def add_category(self, category_name):
        pool = await self.db_manager.get_pool()
        data = {"name": category_name}
        await self.db_manager.insert_data(pool, "categories", data)

    async def remove_category(self, category_id):
        condition = {"id": category_id}
        await self.db_manager.delete_data("categories", condition)

    async def add_feed(self, category_id, feed_url):
        pool = await self.db_manager.get_pool()
        data = {"name": feed_url, "url": feed_url, "category_id": category_id}
        await self.db_manager.insert_data(pool, "feeds", data)

    async def remove_feed(self, feed_id):
        condition = {"id": feed_id}
        await self.db_manager.delete_data("feeds", condition)
    
    async def remove_feeds_by_category(self, category_id):
        condition = {"category_id": category_id}
        await self.db_manager.delete_data("feeds", condition)
    
    async def init_fetch(self, category):
        start_time = time.time()

        if not self.rss_fetcher:
            self.rss_fetcher = RSSFetcher(self.db_manager)
        
        # Initialize self.urls as a dictionary if it hasn't been already
        if self.urls is None:
            self.urls = {}

        # Ensure the category exists in the dictionary and has a list initialized
        if category not in self.urls:
            feeds = await self.get_feeds(category)
            self.urls[category] = [feed['url'] for feed in feeds]

        pool = await self.db_manager.get_pool()
        try:
            failed_urls, rate_limited_urls = await self.rss_fetcher.fetch_feeds(self.urls[category], pool)
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

    async def get_feed_items(self, category, limit, last_id=None, last_pd=None, search_query=None, force_init=False):
        start_time = time.time()
        feed_items = []

        if not self.rss_fetcher:
            self.rss_fetcher = RSSFetcher(self.db_manager)

        if force_init:
            response = await self.init_fetch(category)
            if not response:
                return []

        feed_items = await self.rss_fetcher.get_feed(category, limit, last_id, last_pd, search_query)

        fetch_duration = time.time() - start_time
        print(f"Fetched in {fetch_duration:.2f} seconds")
        
        return feed_items
