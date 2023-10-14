from quart import Quart, render_template, redirect, url_for, jsonify
from config_manager import ConfigManager
from rss_fetcher import RSSFetcher
from opml_importer import OPMLImporter
from db_manager import DBManager
from cache_manager import Cache
import traceback
from aiohttp import ClientError, ServerTimeoutError
from sponsor_block import SponsorBlockManager
from pyngrok import ngrok
import json
import os

app = Quart(__name__)
config_manager = ConfigManager()
opml_importer = OPMLImporter(config_manager=config_manager)
rss_fetcher = RSSFetcher(config_manager=config_manager, max_workers=10)
sg = SponsorBlockManager()
DBManager.create_tables()

cache = Cache.get()

# Function to check if ngrok is already running on a specific port
def is_ngrok_running(port):
    try:
        tunnels = ngrok.get_tunnels()
        for tunnel in tunnels:
            if f"http://localhost:{port}" == tunnel.local_url or f"https://localhost:{port}" == tunnel.local_url:
                return True, tunnel.public_url
        return False, None
    except Exception as e:
        if "ERR_NGROK_108" in str(e):
            print("Cannot start another ngrok instance, account limited to 1 simultaneous session.")
            if os.path.exists("ngrok_url.json"):
                with open("ngrok_url.json", "r") as f:
                    data = json.load(f)
                    return True, data.get("public_url", None)
            else:
                return True, None
        else:
            print(f"An error occurred while checking ngrok status: {e}")
            return False, None

class Feed:
    def __init__(self, rss_fetcher):
        self.rss_fetcher = rss_fetcher
        self.db_manager = DBManager

    async def get_feed_items(self, category, start, end):
        cache_key = f"{category}_{start}_{end}"
        if cache_key in cache:
            return cache[cache_key]
        
        urls = config_manager.get(f'{category}_feed_urls')
        try:
            feed_items = await self.rss_fetcher.fetch_feeds(urls, start, end)
        except ValueError:
            print("Error: fetch_feeds did not return enough values.")
            feed_items = []
        
        # Save to cache
        cache[cache_key] = feed_items
        
        return feed_items

feed = Feed(rss_fetcher)

@app.route('/')
async def root():
    return redirect(url_for('index', category='main'))

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
    start = (page_num - 1) * 20
    end = start + 20
    paginated_feeds = await feed.get_feed_items(category, start, end)
    return await render_template('feed_items.html', feed_items=paginated_feeds)

@app.route('/<string:category>')
async def index(category):
    try:
        all_feeds = await feed.get_feed_items(category, 0, 20)
        return await render_template('index.html', feed_items=all_feeds)
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

from datetime import timedelta

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

if __name__ == "__main__":
    app_port = config_manager.get("app.port", 5000)
    token = config_manager.get("ngrok.token", "")
    if token:
        # Check if ngrok is already running
        ngrok_running, public_url = is_ngrok_running(app_port)

        if not ngrok_running:
            # Initialize ngrok settings
            ngrok.set_auth_token()
            ngrok_tunnel = ngrok.connect(app_port)
            print('Public URL:', ngrok_tunnel.public_url)
        else:
            print('ngrok is already running.')
            print('Public URL:', public_url)

    app.run(
        host=config_manager.get("app.host", "127.0.0.1"),
        debug=config_manager.get("app.debug", False),
        port=app_port
    )
