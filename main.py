from quart import Quart, render_template, jsonify, request
from functools import wraps
from config_manager import ConfigManager
from rss_fetcher import RSSFetcher
from opml_importer import OPMLImporter
from db_manager import DBManager
from cache_manager import Cache
import traceback
from datetime import timedelta
from aiohttp import ClientError, ServerTimeoutError
from ngrok_manager import NgrokManager
from sponsor_block import SponsorBlockManager
from reddit_fetcher import fetch_reddit_media
from fuzzywuzzy import fuzz
import base64
import time
from datetime import datetime, timedelta

recent_requests = {}

app = Quart(__name__)
config_manager = ConfigManager()
opml_importer = OPMLImporter(config_manager=config_manager)

cache = Cache.get()

# Dictionary to store request counts and timestamps
clients = {}

def rate_limit(client_id, limit, time_window):
    current_time = datetime.now()
    request_info = clients.get(client_id, {"count": 0, "time": current_time})

    # Reset count if time_window has passed
    if current_time - request_info["time"] > timedelta(seconds=time_window):
        request_info = {"count": 1, "time": current_time}
    else:
        request_info["count"] += 1

    clients[client_id] = request_info
    return request_info["count"] <= limit

def rate_limiter(limit, time_window):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            client_id = request.remote_addr
            if not rate_limit(client_id, limit, time_window):
                return jsonify({"error": "rate limit exceeded"}), 429
            return func(*args, **kwargs)
        return wrapper
    return decorator

class Feed:
    def __init__(self):
        self.rss_fetcher = None
        self.db_manager = DBManager

    async def get_feed_items(self, category, start, end, search_query=""):
        start_time = time.time()
        cache_key = f"{category}_{start}_{end}_{search_query}"
        if cache_key in cache:
            return cache[cache_key]
        if not self.rss_fetcher:
            self.rss_fetcher = RSSFetcher()
        
        urls = config_manager.get(f'{category}_feed_urls')
        try:
            feed_items = await self.rss_fetcher.fetch_feeds(urls)
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
        cache[cache_key] = feed_items
        fetch_duration = time.time() - start_time
        print(f"Fetched in {fetch_duration:.2f} seconds")
        
        return feed_items

feed = Feed()

@app.route('/')
async def root():
    try:
        return await render_template('index.html')
    except ClientError as ce:
        error_message = f"Client error occurred while fetching feeds: {ce}"
        traceback_info = traceback.format_exc()
        app.logger.error(f"{error_message}\nTraceback Info:\n{traceback_info}")
        return f"{error_message}\nTraceback Info:\n{traceback_info}", 400
    except ServerTimeoutError as ste:
        error_message = f"Server timeout occurred while fetching feeds: {ste}"
        traceback_info = traceback.format_exc()
        app.logger.error(f"{error_message}\nTraceback Info:\n{traceback_info}")
        return f"{error_message}\nTraceback Info:\n{traceback_info}", 504
    except Exception as e:
        error_message = f"An unexpected error occurred while fetching feeds: {e}"
        traceback_info = traceback.format_exc()
        app.logger.error(f"{error_message}\nTraceback Info:\n{traceback_info}")
        return f"{error_message}\nTraceback Info:\n{traceback_info}", 500

@app.route('/refresh', methods=['GET'])
def refresh_config():
    try:
        opml_importer.import_opml()
        global config_manager
        config_manager = ConfigManager()
        cache.clear()
        return {"status": "success", "message": "Configuration and OPML reloaded"}, 200
    except Exception as e:
        return {"status": "error", "message": str(e)}, 500

@app.route('/<string:category>/page/<int:page_num>')
async def paginate(category, page_num):
    search_query = request.args.get('q')  # Add this line to get the search query
    start = (page_num - 1) * 20
    end = start + 20
    try:
        paginated_feeds = await feed.get_feed_items(category, start, end, search_query)
    except ValueError:
        print("Error: fetch_feeds did not return enough values.")
        paginated_feeds = []
    return await render_template('feed_items.html', feed_items=paginated_feeds)

@app.route('/api/sponsorblock/<string:video_id>', methods=['GET'])
async def sponsored_segments(video_id):
    sg = SponsorBlockManager()
    segments = await sg.get_sponsored_segments(video_id)
    segments_dict = []
    for segment in segments:
        segment_dict = segment.__dict__
        if isinstance(segment_dict.get('duration'), timedelta):
            # Convert timedelta to total number of seconds
            segment_dict['duration'] = segment_dict['duration'].total_seconds()
        segments_dict.append(segment_dict)
    return jsonify({"segments": segments_dict})

@app.route('/api/reddit/<string:uri>', methods=['GET'])
async def reddit_media(uri):
    url = base64.b64decode(uri).decode()
    print(url, uri)
    media = fetch_reddit_media(url)
    return jsonify({"media": media})


@app.before_serving
async def startup():
    app_port = config_manager.get("app.port", 5000)
    ngrok_token = config_manager.get("ngrok.token", None)
    public_url = None

    if ngrok_token:
        ngrok_manager = NgrokManager(ngrok_token, app_port)
        public_url = ngrok_manager.manage_ngrok()

    if public_url:
        print(' * Public URL:', public_url)

if __name__ == "__main__":
    opml = OPMLImporter(config_manager=config_manager)
    opml.load()
    config_manager.reload_config()
    app_port = config_manager.get("app.port", 5000)

    app.run(
        host=config_manager.get("app.host", "0.0.0.0"),
        debug=config_manager.get("app.debug", False),
        port=config_manager.get("app.port", 5000)
    )
