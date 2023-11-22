import asyncio
import re
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
from db_manager import QueryBuilder
import logging
import yake
from lxml import etree
from io import BytesIO

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

# Compile the regular expression for performance
CLEAN_TEXT_PATTERN = re.compile(r'<[^<]+?>|http\S+|[^A-Za-z ]+')
def clean_text(text):
    """
    Clean the input text by removing HTML tags, URLs, special characters, and numbers.

    Args:
    text (str): The text to be cleaned.

    Returns:
    str: The cleaned text.
    """
    return CLEAN_TEXT_PATTERN.sub('', text)

def is_valid_tag(tag):
    """
    Check if the tag is valid by ensuring it's not a URL, not purely numerical, and within a certain length range.

    Args:
    tag (str): The tag to be validated.

    Returns:
    bool: True if the tag is valid, False otherwise.
    """
    return not (re.match(r'https?://\S+', tag) or re.fullmatch(r'\d+', tag) or len(tag) < 3 or len(tag) > 50)

def extract_tags_from_entry(text, max_ngram_size=3, numOfKeywords=5, deduplication_threshold=0.9):
    try:
        yake_extractor = yake.KeywordExtractor(n=max_ngram_size, dedupLim=deduplication_threshold, top=numOfKeywords, features=None)
        yake_keywords = [kw for kw, _ in yake_extractor.extract_keywords(text)]

        # Optionally, apply additional filtering for tags
        tags = [tag for tag in yake_keywords if is_valid_tag(tag)]

        return tags
    except Exception as e:
        print("An error occurred in extract_tags_from_entry:", e)
        return []

class RSSFetcher:
    BASE_QUERY = "SELECT * FROM feed_entries"
    ORDER_AND_LIMIT = "ORDER BY published_date DESC, id DESC LIMIT $1::bigint"

    def __init__(self, db_manager, max_workers=200):
        self.feed_metadata = {}
        self.db_manager = db_manager
        self.max_workers = max_workers
        self.namespaces = {
            'dc': 'http://purl.org/dc/elements/1.1/'
        }
        self.date_attributes = ['pubDate', 'published', 'dc:date', 'date', 'published_date']

    def remove_old_entries(self, feed_xml, last_updated_date, url=""):
        if not last_updated_date or not isinstance(last_updated_date, datetime):
            print("Invalid last_updated_date")
            return feed_xml, False

        try:
            feed_xml_bytes = feed_xml.encode('utf-8')
            with BytesIO(feed_xml_bytes) as feed_xml_io:
                tree = etree.parse(feed_xml_io)
                root = tree.getroot()
                root_of_interest = root[0] if len(root) > 0 else None

                if root_of_interest is None:
                    print("No appropriate root element found in XML")
                    return feed_xml, False

                items_to_remove = [elem for elem in root_of_interest if elem.tag == 'item' and self.is_entry_old(elem, last_updated_date)]
                new_entries_found = len(items_to_remove) < len(root_of_interest)
                for item in items_to_remove:
                    root_of_interest.remove(item)

                xml_string = etree.tostring(root_of_interest, pretty_print=True, encoding='unicode')
                return xml_string, new_entries_found

        except etree.XMLSyntaxError as e:
            print(f"XML parsing error for {url}: {e}")
            return feed_xml, False

    def is_entry_old(self, elem, last_updated_date):
        for attr in self.date_attributes:
            xpath = self.create_xpath(attr)
            date_str = elem.find(xpath)
            if date_str is not None and date_str.text:
                published_date = self.parse_date(date_str.text)
                if published_date and published_date <= last_updated_date:
                    return True
        return False

    def create_xpath(self, attr):
        """
        Create an XPath query string based on the attribute.

        :param attr: The attribute to create an XPath query for.
        :return: The XPath query string.
        """
        if 'dc:' in attr:
            return './/{{{}}}{}'.format(self.namespaces['dc'], attr.split(':')[1])
        return './/{}'.format(attr)

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
    
    async def get_feed(self, pool, category, limit=50, last_id=None, last_pd=None, search_query=None, threshold=0.25):
        print(f"Fetching feed with limit {limit}")
        last_pd = self.parse_date(last_pd)
        query_builder = QueryBuilder()
        query_builder.where("category_id = %s", int(category))

        if last_id is not None and last_pd is not None:
            query_builder.where("(published_date < %s OR (published_date = %s AND id < %s))", last_pd, last_pd, int(last_id))

        if search_query:
            # TODO:
            # Validate and sanitize search_query here to avoid sql injection or other exploits
            # ...

            search_condition = "((similarity(title, %s) > %s OR EXISTS (SELECT 1 FROM jsonb_array_elements_text(additional_info->'tags') AS tag WHERE similarity(tag, %s) > %s ) OR similarity(additional_info->>'creator', %s) > %s) OR title ILIKE %s OR additional_info->>'creator' ILIKE %s OR url ILIKE %s)"
            query_builder.where(search_condition, search_query, threshold, search_query, threshold, search_query, threshold, f"%{search_query}%", f"%{search_query}%", f"%{search_query}%")

        query_builder.orderBy("published_date DESC, id DESC").limit(int(limit))
        query, params = query_builder.build()

        feeds = await self.db_manager.select_data(pool, "feed_entries", query, params)
        return feeds
    
    async def process_entry(self, category, entry, url, feed_title_raw=None):
        # Directly use dict.get for attributes that are dicts
        original_link = entry.get('link', '')

        # Initialize published_date
        published_date = self.get_published_date(entry, url)

        # If there is no valid published date, log a warning and skip processing this entry
        if not published_date:
            logging.warning(f"No valid published date for entry in {original_link}")
            return None, None  # Return None values instead of empty dict and date

        # Fetch media information from entry
        tree, summary, thumbnail, video_id, additional_info = fetch_media(entry)
        
        title = entry.get('title', '')
        # Use summary from content if available, fallback to the fetched summary, and limit to 100 characters
        summary = tree.text_content() if tree is not None else summary
        content = str(entry.get('content', [{}])[0].get('value', summary))

        creator = additional_info.get('creator', '')
        website_name = get_website_name(url)

        additional_info['web_name'] = select_title(feed_title_raw, creator, website_name)

        #tags = extract_tags_from_entry(clean_text(title + ' ' + content))
        #if tags:
        #    additional_info['tags'] = additional_info.get('tags', []) + tags

        # Build the processed entry dict
        processed_entry = {
            'url': url,
            'category_id': category,
            'title': title,
            'content': content,
            'thumbnail': thumbnail,
            'video_id': video_id,
            'additional_info': additional_info,
            'published_date': published_date,
            'original_link': original_link
        }

        return processed_entry, published_date

    def get_published_date(self, entry, url):
        for attr in self.date_attributes:
            date_str = getattr(entry, attr, None)
            if date_str:
                published_date = self.parse_date(date_str)
                if published_date:
                    return published_date
        
        #logging.warning(f"No valid published date found in entry ({entry.get('title', '')}, {url})\n{entry}")
        return datetime.min.replace(tzinfo=timezone.utc)

    async def fetch_single_feed(self, category, url):
        fm_latest_entry, fm_latest_date, fm_latest_etag, fm_latest_expires, fm_latest_content_len, fm_last_checked, fm_latest_title = None, None, None, None, None, None, None
        if url in self.feed_metadata:
            fm_latest_entry = self.feed_metadata[url]
            fm_latest_date = fm_latest_entry.get("last_modified")
            fm_latest_etag = fm_latest_entry.get("etag")
            fm_latest_expires = fm_latest_entry.get("expires")
            fm_latest_content_len = fm_latest_entry.get("content_length")
            fm_last_checked = fm_latest_entry.get("last_checked")
            fm_latest_title = fm_latest_entry.get("latest_title")
            if not fm_latest_date and fm_last_checked:
                fm_latest_date = fm_last_checked

        headers = {'User-Agent': generate_user_agent()}
        if fm_latest_etag:
            headers["If-None-Match"] = fm_latest_etag
        if fm_latest_date:
            headers["If-Modified-Since"] = fm_latest_date.strftime("%a, %d %b %Y %H:%M:%S GMT")
    
        async with ClientSession(connector=TCPConnector(limit=self.max_workers, keepalive_timeout=10, ssl=False), headers=headers) as fetch_session:
            try:
                async with fetch_session.get(url) as response:
                    # Check for Internal Server Error
                    if response.status != 200:
                        return [], [], response.status
                    text = await response.text()
                    should_parse = True
                    if fm_latest_date:
                        text, should_parse = self.remove_old_entries(text, self.parse_date(fm_latest_date), url)
                    if not should_parse:
                        return [], [], 304
                    feed = feedparser.parse(text, etag=fm_latest_etag, modified=headers.get("If-Modified-Since"), request_headers=headers, response_headers=response.headers)

                    feed_status_code = getattr(feed, 'status', None)
                    if feed_status_code and feed_status_code != 200:
                        print(url, " returned status: ", feed_status_code)
                        return [], [], feed_status_code
                    entries = feed.entries
                    len_entries = len(entries)
                    if not entries or len_entries == 0:
                        return [], [], 304
                    
                    print(len_entries)
                    feed_title_raw = feed.feed.get('title', None)
                    # Store the new ETag from the response for next request
                    new_etag = response.headers.get("ETag")

                    # Process entries and collect published dates concurrently
                    processed_entries_and_dates = await asyncio.gather(
                        *(self.process_entry(category, entry, url, feed_title_raw) for entry in entries)
                    )

                    processed_entries = []
                    if processed_entries_and_dates:
                        # Separate the processed entries from their published dates
                        processed_entries, published_dates = zip(*processed_entries_and_dates)

                        # Filter out None values if any entry failed to process
                        processed_entries = [entry for entry in processed_entries if entry is not None]

                        # Calculate the latest date from the non-None published dates
                        fm_latest_date = max((date for date in published_dates if date), default=None)
                
                    metadata_update = {
                        'url': url,
                        'etag': new_etag or fm_latest_etag,
                        'content_length': len_entries,
                        'last_modified': fm_latest_date or self.date_now,
                        'expires': self.parse_date(response.headers.get('Expires')) or self.date_now,
                        'last_checked': self.date_now,
                        'latest_title': ""
                    }
                
                return processed_entries, metadata_update, 200
            except Exception as e:
                logging.error(f"An error occurred while fetching {url}: {e}\n{traceback.format_exc()}")
                return [], [], 443
    
    async def fetch_feeds(self, category, urls, pool):
        if not urls:
            logging.warning("The 'urls' parameter is empty.")
            return [], []

        tasks = []
        failed_urls = set()
        updated_urls = []
        all_processed_entries = []  # Collect all processed entries here
        metadata_updates = []  # Collect metadata updates here
        self.date_now = self.parse_date(datetime.now(pytz.utc))
        semaphore = asyncio.Semaphore(self.max_workers)

        async def fetch_and_process(url):
            async with semaphore:
                processed_entries, metadata_update, code = await self.fetch_single_feed(category, url)
                if code != 200:
                    failed_urls.add(url)
                else:
                    updated_urls.append(url)
                    all_processed_entries.extend(processed_entries)
                    if metadata_update:
                        metadata_updates.append(metadata_update)

        async with pool.acquire() as connection:
            query = "SELECT * FROM feed_metadata WHERE url = ANY($1)"
            feed_metadata_entries = await connection.fetch(query, urls)
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