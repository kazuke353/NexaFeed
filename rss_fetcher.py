import asyncio
import json
import pytz
import tldextract
import traceback
from rapidfuzz import fuzz
from aiohttp import ClientSession, TCPConnector
from datetime import datetime, timezone, timedelta
from dateutil.parser import parse
import feedparser
from user_agent import generate_user_agent
from media_fetcher import fetch_media
import logging

logging.basicConfig(level=logging.INFO)

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
    

def select_title(feed_title, creator, website_name):
    # If feed title and creator are the same, discard the feed title.
    if feed_title == creator:
        feed_title = None
    
    # Prepare a list to hold the titles
    titles = []

    # If the website name is valid, add it first
    if website_name:
        titles.append(website_name)

    # Check if feed title and website name are similar
    if feed_title:
        if not is_close(feed_title, website_name):
            # If not similar, add feed_title after website_name
            titles.append(feed_title)
    
    return titles

def is_close(str1, str2, threshold=80):  # Note: threshold is 0-100
    return fuzz.ratio(str1.lower(), str2.lower()) > threshold

class RSSFetcher:
    BASE_QUERY = "SELECT * FROM feed_entries"
    ORDER_AND_LIMIT = "ORDER BY published_date DESC, id DESC LIMIT $1::bigint"

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
    
    async def get_feed(self, limit=50, last_id=None, last_pd=None, search_query=None, threshold=0.3):
        print(f"Fetching feed with limit {limit}")
        pool = await self.db_manager.get_pool()
        parameters = [int(limit)]

        # Initialize the where_clause as an empty string
        where_clause = ""

        # If a search query is provided, add to the WHERE clause
        if search_query:
            where_clause += """
                WHERE (similarity(title, $2) > $3 OR similarity(content, $2) > $3 
                OR similarity(additional_info->>'creator', $2) > $3) 
                OR url ILIKE $2
            """
            parameters.extend([search_query, threshold])

        # If pagination parameters exist, append them to the WHERE clause
        if last_pd and last_id:
            # If a search query already exists, add AND otherwise WHERE
            where_clause += f"{' AND' if 'WHERE' in where_clause else ' WHERE'} (published_date, id) < (${'4' if search_query else '2'}, ${'5' if search_query else '3'})"
            parameters.extend([self.parse_date(last_pd), int(last_id)])

        query = f"{self.BASE_QUERY} {where_clause} {self.ORDER_AND_LIMIT}"

        # Make sure parameters are in the correct order and the correct amount
        expected_param_count = 1 + (2 if search_query else 0) + (2 if last_pd and last_id else 0)
        assert len(parameters) == expected_param_count, f"Expected {expected_param_count} parameters, got {len(parameters)}"

        async with pool.acquire() as connection:
            feeds = await connection.fetch(query, *parameters)

        # Process entries
        processed_entries = await asyncio.gather(
            *(self.process_row_entry(entry) for entry in feeds)
        )

        # Update the last_id and last_pd for pagination if we have entries
        if processed_entries:
            last_entry = processed_entries[-1]
            last_id, last_pd = last_entry.get('id'), last_entry.get('published_date')

        return processed_entries, last_id, last_pd

    async def process_row_entry(self, entry):
        # Use a dictionary comprehension to extract the fields and use .get() to provide defaults
        entry_fields = {field: entry.get(field, None) for field in ('id', 'title', 'content', 'summary', 'thumbnail', 'video_id', 'original_link', 'url')}
        
        # Parse the published date or use the minimum datetime if not available
        entry_fields['published_date'] = self.parse_date(entry.get('published_date')) if entry.get('published_date') else datetime.min.replace(tzinfo=timezone.utc)

        # Attempt to load additional_info or set to None if any JSONDecodeError occurs
        try:
            entry_fields['additional_info'] = json.loads(entry.get('additional_info', '{}'))
        except json.JSONDecodeError as e:
            print(f"Error decoding JSON: {e}")
            entry_fields['additional_info'] = None

        return entry_fields
    
    async def process_entry(self, entry, url, feed_title_raw=None):
        # Directly use dict.get for attributes that are dicts
        original_link = entry.get('link', '')

        # Initialize published_date
        published_date = self.get_published_date(entry)

        # If there is no valid published date, log a warning and skip processing this entry
        if not published_date:
            logging.warning(f"No valid published date for entry in {original_link}")
            return None, None  # Return None values instead of empty dict and date

        # Fetch media information from entry
        tree, summary, thumbnail, video_id, additional_info = fetch_media(entry)
        
        # Use summary from content if available, fallback to the fetched summary, and limit to 100 characters
        summary = tree.text_content() if tree is not None else summary
        content = entry.get('content', [{}])[0].get('value', summary)

        creator = additional_info.get('creator', '')
        website_name = get_website_name(url)

        additional_info['web_name'] = select_title(feed_title_raw, creator, website_name)

        # Build the processed entry dict
        processed_entry = {
            'url': url,
            'title': entry.get('title', ''),
            'content': content,
            'summary': summary,
            'thumbnail': thumbnail,
            'video_id': video_id,
            'additional_info': additional_info,
            'published_date': published_date,
            'original_link': original_link
        }

        return processed_entry, published_date

    def get_published_date(self, entry):
        for attr in self.date_attributes:
            date_str = getattr(entry, attr, None)
            if date_str:
                published_date = self.parse_date(date_str)
                if published_date:
                    return published_date
        
        logging.warning("No valid published date found in entry.")
        return datetime.min.replace(tzinfo=timezone.utc)

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

                    feed_title_raw = feed.feed.get('title', None)
                    # Store the new ETag from the response for next request
                    new_etag = response.headers.get("ETag")

                    # Process entries and collect published dates concurrently
                    processed_entries_and_dates = await asyncio.gather(
                        *(self.process_entry(entry, url, feed_title_raw) for entry in feed.entries)
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