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

        # Compare ETags if both the current and stored ETags are present.
        etag_updated = (current_etag is not None) and (current_etag != stored_etag)

        # Compare Last-Modified dates if both are present and can be parsed.
        last_modified_updated = False
        if current_last_modified and stored_last_modified:
            try:
                current_last_modified_dt = datetime.strptime(current_last_modified, "%a, %d %b %Y %H:%M:%S GMT")
                stored_last_modified_dt = datetime.strptime(stored_last_modified, "%a, %d %b %Y %H:%M:%S GMT")
                last_modified_updated = current_last_modified_dt > stored_last_modified_dt
            except ValueError as e:
                # Log the error for debugging purposes
                print(f"Error parsing dates: {e}")
                # If there is an error in parsing the dates, we can assume content update to be cautious.
                last_modified_updated = True

        # If either the ETag or Last-Modified header has changed, the content has been updated.
        content_updated = etag_updated or last_modified_updated

        return content_updated
    
    def should_update(self, stored_expires, response):
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
                if stored_expires == expires_time:
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
    
    async def get_feed(self, limit=50, offset=0, search_query=None, threshold=0.3):
        print(f"Fetching page ({limit}, {offset})")
        pool = await self.db_manager.get_pool()
        async with pool.acquire() as connection:
            if search_query:
                query = """
                    SELECT * FROM feed_entries 
                    WHERE (published_date, id) < ($1, $2) AND similarity(title, $4) > $5 OR similarity(content, $4) > $5 OR similarity(additional_info->>'author', $4) > $5
                    ORDER BY published_date DESC, id 
                    DESC
                    LIMIT $3
                """
                safe_search_query = f"%{search_query}%"
                feeds = await connection.fetch(query, self.last_pd, self.last_id, limit, safe_search_query, threshold)
            else:
                query = """
                    SELECT * FROM feed_entries 
                    WHERE (published_date, id) < 
                    ($1, $2)
                    ORDER BY published_date DESC, id 
                    DESC
                    LIMIT $3
                """
                feeds = await connection.fetch(query, self.last_pd, self.last_id, limit)

            # Process entries
            processed_entries = await asyncio.gather(
                *(self.process_row_entry(entry) for entry in feeds)
            )

            last_entry = processed_entries.last()
            self.last_id, self.last_pd = last_entry['id'], last_entry['published_date']

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
    
    async def process_entry(self, entry, url, feed_title=None):
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
        additional_info['web_name'] = feed_title

        processed_entry = {
            'url': url,
            'title': title,
            'content': content,
            'summary': summary,
            'thumbnail': thumbnail,
            'video_id': video_id,
            'additional_info': additional_info,
            'published_date': published_date,
            'original_link': original_link
        }
    
        return processed_entry, processed_entry.get('published_date')

    async def fetch_single_feed(self, url):
        latest_entry, latest_date, latest_etag, latest_content_len = None, None, None, None
        if url in self.feed_metadata:
            latest_entry = self.feed_metadata[url]
            latest_date = latest_entry.get("last_modified")
            latest_etag = latest_entry.get("etag")
            latest_expires = latest_entry.get("expires")
            latest_content_len = latest_entry.get("content_length")
            if not latest_date:
                latest_date = self.date_now

        headers = {'User-Agent': generate_user_agent()}
        if latest_etag:
            headers["If-None-Match"] = latest_etag
        if latest_date:
            headers["If-Modified-Since"] = latest_date.strftime("%a, %d %b %Y %H:%M:%S GMT")
    
        async with ClientSession(connector=TCPConnector(keepalive_timeout=10, ssl=False), headers=headers) as fetch_session:
            try:
                async with fetch_session.get(url) as response:
                    # Check for Internal Server Error
                    if response.status != 200:
                        return [], [], response.status
                    if latest_entry:
                        # Check if the content has not changed
                        if self.check_content_update(headers, response):
                            return [], [], 304

                    text = await response.text()
                    feed = feedparser.parse(text, etag=latest_etag, modified=headers.get("If-Modified-Since"), request_headers=headers, response_headers=response.headers)

                    feed_status_code = getattr(feed, 'status', None)
                    if feed_status_code and feed_status_code != 200:
                        print(url, " returned status: ", feed_status_code)
                        return [], [], feed_status_code

                    feed_title = feed.feed.get('title', None) or get_website_name(url)
                    # Store the new ETag from the response for next request
                    new_etag = response.headers.get("ETag")

                    # Process entries and collect published dates concurrently
                    processed_entries_and_dates = await asyncio.gather(
                        *(self.process_entry(entry, url, feed_title) for entry in feed.entries)
                    )

                    processed_entries = []
                    if processed_entries_and_dates:
                        # Separate the processed entries from their published dates
                        processed_entries, published_dates = zip(*processed_entries_and_dates)

                        # Filter out None values if any entry failed to process
                        processed_entries = [entry for entry in processed_entries if entry is not None]

                        # Calculate the latest date from the non-None published dates
                        latest_date = max((date for date in published_dates if date), default=None)
                
                    metadata_update = {
                        'url': url,
                        'etag': new_etag,
                        'content_length': len(feed.entries),
                        'last_modified': latest_date or self.date_now,
                        'expires': self.parse_date(response.headers.get('Expires')) or self.date_now,
                        'last_checked': self.date_now
                    }
                
                return processed_entries, metadata_update, 200
            except Exception as e:
                logging.error(f"An error occurred while fetching {url}: {e}\n{traceback.format_exc()}")
                return [], [], 443
    
    async def fetch_feeds(self, urls, pool):
        if not urls:
            logging.warning("The 'urls' parameter is empty.")
            return [], []
        if self.rate_limit("Init Feeds", 1, 60):
            return [], urls

        tasks = []
        failed_urls = set()
        updated_urls = []
        all_processed_entries = []  # Collect all processed entries here
        metadata_updates = []  # Collect metadata updates here
        self.date_now = self.parse_date(datetime.now(pytz.utc))

        async def fetch_and_process(url):
            processed_entries, metadata_update, code = await self.fetch_single_feed(url)
            if code != 200:
                failed_urls.add(url)
            else:
                updated_urls.append(url)
                all_processed_entries.extend(processed_entries)
                if metadata_update:
                    metadata_updates.append(metadata_update)

        async with pool.acquire() as connection:
            conn = connection._con
            query = "SELECT * FROM feed_metadata WHERE url = ANY($1)"
            feed_metadata_entries = await conn.fetch(query, urls)
            self.feed_metadata = {entry['url']: entry for entry in feed_metadata_entries}

        for url in urls:
            task = asyncio.create_task(fetch_and_process(url))
            tasks.append(task)

        await asyncio.gather(*tasks)

        # Now use insert_many for all processed entries
        if all_processed_entries:
            await self.db_manager.insert_many(pool, "feed_entries", all_processed_entries)
        # And for all metadata updates
        if metadata_updates:
            await self.db_manager.insert_many(pool, "feed_metadata", metadata_updates, "DO UPDATE")

        return failed_urls, []
    
    def remove_failed_feeds(self, config_manager, category, failed_urls):
        if config_manager and category and failed_urls:
            existing_feeds = set(config_manager.config_data.get(category, []))
            updated_feeds = existing_feeds - failed_urls
            config_manager.overwrite_category_data(category, list(updated_feeds))
            logging.info("Removed the following feeds: %s", failed_urls)