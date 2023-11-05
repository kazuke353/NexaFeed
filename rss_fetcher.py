import asyncio
import json
import pytz
import tldextract
import traceback
from aiohttp import ClientSession, TCPConnector
from datetime import datetime, timezone, timedelta
from dateutil.parser import parse
import feedparser
from user_agent import generate_user_agent
from media_fetcher import fetch_media
import logging

logging.basicConfig(level=logging.DEBUG)

def get_website_name(url):
    try:
        # Extract the registered domain (sld + tld) using tldextract
        extracted = tldextract.extract(url)
        # The website name is usually the second-level domain (sld)
        website_name = extracted.domain
        # Capitalize the first letter of the website name
        return website_name.capitalize()
    except Exception as e:
        print(f"An error occurred: {e}")
        return None

class RSSFetcher:
    def __init__(self, db_manager, max_workers=45):
        self.db_manager = db_manager
        self.max_workers = max_workers
        self.session = None
        self.clients = {}
        self.date_attributes = ['published', 'pubDate', 'updated', 'published_date']
    
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
    
    def check_content_update(self, stored_headers, response):
        """
        Check if the content has been updated based on ETag and Last-Modified headers.

        :param stored_headers: The headers dictionary containing previously stored 'Last-Modified' and 'ETag'.
        :param response: The response object from the HTTP request.
        :return: Boolean indicating whether the content has been updated.
        """
        # Extract current ETag and Last-Modified values from the response
        current_last_modified = response.headers.get("Last-Modified")
        current_etag = response.headers.get("ETag")

        # Get the stored ETag and Last-Modified values (from previous response)
        stored_last_modified = stored_headers.get("Last-Modified")
        stored_etag = stored_headers.get("ETag")

        # If there is no stored ETag or Last-Modified, it's an initial fetch; return False (no update).
        if not stored_etag and not stored_last_modified:
            return False

        # Compare ETags if both the current and stored ETags are present.
        etag_matches = current_etag == stored_etag if current_etag and stored_etag else False

        # Only compare Last-Modified if both dates are present and could be parsed.
        last_modified_matches = False
        if current_last_modified and stored_last_modified:
            try:
                current_last_modified_dt = datetime.strptime(current_last_modified, "%a, %d %b %Y %H:%M:%S GMT")
                stored_last_modified_dt = datetime.strptime(stored_last_modified, "%a, %d %b %Y %H:%M:%S GMT")
                last_modified_matches = current_last_modified_dt <= stored_last_modified_dt
            except ValueError as e:
                print(f"Error parsing dates: {e}")

        # If both match, content has not been updated. If either is missing or they don't match, content has been updated.
        content_updated = not (etag_matches and last_modified_matches)

        return content_updated
    
    def should_update(self, url, response):
        """
        Determine if the feed should be updated based on the 'Expires' header.

        :param url: The URL of the feed.
        :param response: The response object from the HTTP request.
        :return: Boolean indicating whether the feed should be updated.
        """
        # Check if the 'Expires' header is present in the response
        expires_header = response.headers.get('Expires')
        if expires_header:
            try:
                # Parse the 'Expires' header to a datetime object
                expires_time = datetime.strptime(expires_header, "%a, %d %b %Y %H:%M:%S GMT")
                expires_time = pytz.utc.localize(expires_time)  # Localize to UTC
                
                # If the current time is before the expiration time, no update needed
                if datetime.now(pytz.utc) < expires_time:
                    return False
            except ValueError as e:
                print(f"Error parsing 'Expires' header: {e}")

        # If 'Expires' header is not present or the current time is past the expiration time, update needed
        return True
    
    def check_content_length(self, stored_content_length, response):
        """
        Check for updates based on the Content-Length header.

        :param stored_headers: The headers dictionary containing previously stored 'Content-Length'.
        :param response: The response object from the HTTP request.
        :return: Boolean indicating whether the content has been updated.
        """
        current_content_length = response.headers.get("Content-Length")

        if stored_content_length and current_content_length:
            return stored_content_length != current_content_length
        else:
            # If Content-Length is not available or not stored, cannot determine by this method.
            return None

    def parse_date(self, date_str):
        # If date_str is already a datetime object, just ensure it's timezone-aware.
        if isinstance(date_str, datetime):
            dt = date_str
            if dt.tzinfo is None or dt.tzinfo.utcoffset(dt) is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt
        
        # If date_str is a string, attempt to parse it to a datetime object.
        try:
            if isinstance(date_str, str):
                dt = parse(date_str)
                if dt.tzinfo is None or dt.tzinfo.utcoffset(dt) is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                return dt
        except (ValueError, TypeError) as e:
            print(f"Error parsing date '{date_str}': {e}")  # Debug print
            return None
    
    async def get_feed(self, limit=50, offset=0):
        print(f"Fetching page ({limit}, {offset})")
        pool = await self.db_manager.get_pool()
        async with pool.acquire() as connection:
            # You don't need to access the protected member _con directly.
            query = "SELECT * FROM feed_entries ORDER BY published_date DESC LIMIT $1 OFFSET $2"
            feeds = await connection.fetch(query, limit, offset)
            # Process entries
            processed_entries = await asyncio.gather(
                *(self.process_row_entry(entry) for entry in feeds)
            )
            
            return processed_entries
    
    async def process_row_entry(self, entry):
        published_date = None

        date_str = entry.get('published_date', None)
        if date_str:
            published_date = self.parse_date(date_str)

        if published_date is None:
            published_date = datetime.min.replace(tzinfo=timezone.utc)
        
        try:
            additional_info = json.loads(entry.get('additional_info', None))
        except json.JSONDecodeError as e:
            print(f"Error decoding JSON: {e}")
            additional_info = None

        return {
            'title': entry['title'],
            'content': entry['content'],
            'summary': entry['summary'],
            'thumbnail': entry['thumbnail'],
            'video_id': entry['video_id'],
            'additional_info': additional_info,
            'published_date': published_date,
            'original_link': entry['original_link'],
            'url': entry['url']
        }
    
    async def process_entry(self, entry):
        original_link = getattr(entry, 'link', '')
        published_date = None

        for attr in self.date_attributes:
            date_str = getattr(entry, attr, None)
            if date_str:
                published_date = self.parse_date(date_str)
                if published_date:
                    break

        if published_date is None:
            # Log a warning and default to datetime.min with timezone set to UTC
            logging.warning(f"No valid published date for entry in {original_link}")
            return {}

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

    async def fetch_single_feed(self, url):
        pool = await self.db_manager.get_pool()

        async with pool.acquire() as connection:
            conn = connection._con
            # Retrieve the latest entry and its ETag
            query = "SELECT * FROM feed_metadata WHERE url = $1 LIMIT 1"
            latest_entry = await conn.fetchrow(query, url)
            latest_date, latest_etag, latest_content_len = None, None, None
            if latest_entry:
                latest_date = latest_entry.get("last_modified")
                latest_etag = latest_entry.get("etag")
                latest_content_len = latest_entry.get("content_length")

        headers = {'User-Agent': generate_user_agent()}
        if latest_etag:
            headers["If-None-Match"] = latest_etag
        if latest_date:
            headers["If-Modified-Since"] = latest_date.strftime("%a, %d %b %Y %H:%M:%S GMT")
    
        async with ClientSession(connector=TCPConnector(keepalive_timeout=30, ssl=False), headers=headers, raise_for_status=True) as fetch_session:
            try:
                async with fetch_session.get(url) as response:
                    # Check for Internal Server Error
                    if response.status == 500:
                        return 500
                    # Check if the content has not changed
                    if response.status == 304 or self.check_content_update(headers, response):
                        return 304
                    # Check if we should update based on the 'Expires' header
                    if not self.should_update(url, response):
                        return 304
                    if self.check_content_length(latest_content_len, response):
                        return 304

                    text = await response.text()
                    feed = feedparser.parse(text)
                    feed_title = feed.feed.get('title', None)
                    # Store the new ETag from the response for next request
                    new_etag = response.headers.get("ETag")

                    # Process entries
                    processed_entries = await asyncio.gather(
                        *(self.process_entry(entry) for entry in feed.entries)
                    )
    
                    # Filter out None values if any entry failed to process
                    processed_entries = [entry for entry in processed_entries if entry is not None]

                    for entry in processed_entries:
                        entry['url'] = url
                        entry['etag'] = new_etag
                        entry['additional_info']['web_name'] = feed_title if feed_title else get_website_name(url)
                        published_date = entry['published_date']
                        if latest_date and published_date > latest_date:
                            latest_date = published_date
                        await self.db_manager.insert_data(pool, "feed_entries", entry)
                
                    await self.db_manager.insert_data(pool, "feed_metadata", {
                        'url': url,
                        'etag': new_etag,
                        'content_length': len(feed.entries),
                        'last_modified': self.parse_date(latest_date),
                        'expires': self.parse_date(response.headers.get('Expires')),
                        'last_checked': self.parse_date(datetime.now(pytz.utc))
                    }, "DO UPDATE")
                
                return 200
            except Exception as e:
                logging.error(f"An error occurred while fetching {url}: {e}\n{traceback.format_exc()}")
                return 443
    
    async def fetch_feeds(self, urls):
        if not urls:
            logging.warning("The 'urls' parameter is empty.")
            return [], []
        if self.rate_limit("Init Feeds", 1, 60):
            return [], urls
    
        tasks = []
        failed_urls = set()
    
        # Limit the number of workers using max_workers
        semaphore = asyncio.Semaphore(self.max_workers)
    
        async def fetch_and_append(url):
            async with semaphore:
                code = await self.fetch_single_feed(url)
                if code != 200:
                    failed_urls.add(url)
    
        for url in urls:
            task = asyncio.create_task(fetch_and_append(url))
            tasks.append(task)
    
        await asyncio.gather(*tasks)
    
        return failed_urls, []
    
    def remove_failed_feeds(self, config_manager, category, failed_urls):
        if config_manager and category and failed_urls:
            existing_feeds = set(config_manager.config_data.get(category, []))
            updated_feeds = existing_feeds - failed_urls
            config_manager.overwrite_category_data(category, list(updated_feeds))
            logging.info("Removed the following feeds: %s", failed_urls)