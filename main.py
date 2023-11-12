from quart import Quart, render_template, jsonify, request
from functools import wraps
from config_manager import ConfigManager
from db_manager import DBManager
from feed_manager import Feed
from cache_manager import Cache
import os
import xml.etree.ElementTree as ET
import traceback
from datetime import timedelta
from aiohttp import ClientError, ServerTimeoutError
from ngrok_manager import NgrokManager
from reddit_fetcher import fetch_reddit_media
import base64
from datetime import datetime, timedelta
from dotenv import load_dotenv
load_dotenv()

recent_requests = {}

app = Quart(__name__)
db_manager = DBManager()
config_manager = ConfigManager()
cache = Cache(config_manager).get()
feed = Feed(db_manager, config_manager)

# Dictionary to store request counts and timestamps
clients = {}

async def rate_limit(client_id, limit, time_window):
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
        async def wrapper(*args, **kwargs):
            client_id = request.remote_addr
            if not await rate_limit(client_id, limit, time_window):
                return jsonify({"error": "rate limit exceeded"}), 429
            return await func(*args, **kwargs)
        return wrapper
    return decorator

def handle_route_errors(f):
    @wraps(f)
    async def decorated_function(*args, **kwargs):
        try:
            return await f(*args, **kwargs)
        except ClientError as ce:
            return log_and_respond("Client error occurred", ce, 400)
        except ServerTimeoutError as ste:
            return log_and_respond("Server timeout occurred", ste, 504)
        except Exception as e:
            return log_and_respond("An unexpected error occurred", e, 500)
    return decorated_function

def log_and_respond(message, exception, status_code):
    error_message = f"{message}: {exception}"
    traceback_info = traceback.format_exc()
    app.logger.error(f"{error_message}\nTraceback Info:\n{traceback_info}")
    return f"{error_message}\nTraceback Info:\n{traceback_info}", status_code

@app.route('/')
@handle_route_errors
async def root():
    return await render_template('index.html')

@app.route('/api/fetch/<int:category>')
@rate_limiter(limit=2, time_window=1)
async def paginate(category):
    last_id = request.args.get('last_id')
    last_pd = request.args.get('last_pd')
    search_query = request.args.get('q')
    force_init = request.args.get('force_init', False)

    limit = config_manager.get("feed.size", 20)
    paginated_feeds = await feed.get_feed_items(category, limit, last_id, last_pd, search_query, force_init)
    return jsonify(feed_items=paginated_feeds)

@app.route('/refresh', methods=['GET'])
@rate_limiter(limit=1, time_window=60)
def refresh_config():
    try:
        cache.clear()
        config_manager.reload_config()
        return {"status": "success", "message": "Configuration and OPML reloaded"}, 200
    except Exception as e:
        return {"status": "error", "message": str(e)}, 500

@app.route('/api/reddit/<string:uri>', methods=['GET'])
async def reddit_media(uri):
    url = base64.b64decode(uri).decode()
    media = fetch_reddit_media(url)
    return jsonify({"media": media})

@app.route('/api/sidebar')
async def render_sidebar():
    return await render_template('sidebar.html')

@app.route('/api/categories')
async def get_categories():
    categories = await feed.get_categories()
    return jsonify(categories=categories)

@app.route('/api/categories/feeds/<int:category_id>')
async def get_feeds(category_id):
    feeds = await feed.get_feeds(category_id)
    return jsonify(feeds=feeds)

@app.route('/api/categories', methods=['POST'])
async def add_category():
    data = await request.get_json()
    category_name = data.get('name')
    if category_name:
        await feed.add_category(category_name)
        return jsonify({"message": "Category added successfully"}), 200
    return jsonify({"error": "Category name is required"}), 400

@app.route('/api/categories/<int:category_id>', methods=['DELETE'])
async def remove_category(category_id):
    # First, remove all feeds associated with this category
    await feed.remove_feeds_by_category(category_id)
    await feed.remove_category(category_id)
    return jsonify({"message": "Category removed successfully"}), 200

@app.route('/api/categories/feeds/<int:category_id>', methods=['POST'])
async def add_feed(category_id):
    data = await request.get_json()
    feed_url = data.get('url')
    if feed_url:
        await feed.add_feed(category_id, feed_url)
        return jsonify({"message": "Feed added successfully"}), 200
    return jsonify({"error": "Feed URL is required"}), 400

@app.route('/api/categories/feeds/<int:feed_id>', methods=['DELETE'])
async def remove_feed(feed_id):
    await feed.remove_feed(feed_id)
    return jsonify({"message": "Feed removed successfully"}), 200

@app.route('/api/categories/<int:category_id>/import', methods=['POST'])
async def import_opml(category_id):
    # Check if the post request has the file part
    if 'opml' not in await request.files:
        return jsonify({'error': 'No file part'}), 400

    file = (await request.files)['opml']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400

    try:
        # Parse the OPML file
        tree = ET.parse(file)
        root = tree.getroot()

        # Extract feeds from the OPML file
        feeds = []
        for outline in root.findall(".//outline[@type='rss']"):
            feed = {
                'name': outline.get('title', ''),
                'url': outline.get('xmlUrl', ''),
                'category_id': category_id
            }
            feeds.append(feed)

        pool = await db_manager.get_pool()
        # Insert feeds into the database
        await db_manager.insert_many(
            pool=pool,  # Database connection pool
            table_name='feeds',
            data_list=feeds,
            on_conflict_action="DO NOTHING"
        )

        return jsonify({'feeds': feeds}), 201

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.before_serving
async def startup():
    try:
        app_port = config_manager.get("app.port", 5000)
        ngrok_token = os.environ.get('NGROK_TOKEN')
        public_url = None

        if ngrok_token:
            app.ngrok_manager = NgrokManager(ngrok_token, app_port)
            public_url = await app.ngrok_manager.manage_ngrok()

        if public_url:
            print(' * Public URL:', public_url)
    except Exception as e:
        print(f"Error during startup: {e}")

@app.after_serving
async def cleanup():
    pool = await db_manager.get_pool()
    await pool.close()

    if hasattr(app, 'ngrok_manager'):
        app.ngrok_manager.terminate_ngrok()

if __name__ == "__main__":
    config_manager.reload_config()
    app.run(
        host=config_manager.get("app.host", "0.0.0.0"),
        debug=config_manager.get("app.debug", False),
        port=config_manager.get("app.port", 5000)
    )
