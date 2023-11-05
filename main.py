from quart import Quart, render_template, jsonify, request
from functools import wraps
from config_manager import ConfigManager
from db_manager import DBManager
from feed_manager import Feed
from opml_importer import OPMLImporter
from cache_manager import Cache
import os
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
opml_importer = OPMLImporter(config_manager=config_manager)
cache = Cache(config_manager).get()
feed = Feed(db_manager, config_manager)

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

@app.route('/refresh', methods=['GET'])
def refresh_config():
    try:
        cache.clear()
        opml_importer.load()
        config_manager.reload_config()
        return {"status": "success", "message": "Configuration and OPML reloaded"}, 200
    except Exception as e:
        return {"status": "error", "message": str(e)}, 500

@app.route('/<string:category>/page/<int:page_num>')
async def paginate(category, page_num):
    search_query = request.args.get('q')
    limit = config_manager.get("feed.size", 20)
    offset = (page_num - 1) * limit
    paginated_feeds = await feed.get_feed_items(category, limit, offset, search_query)
    return await render_template('feed_items.html', feed_items=paginated_feeds)

@app.route('/api/reddit/<string:uri>', methods=['GET'])
async def reddit_media(uri):
    url = base64.b64decode(uri).decode()
    print(url, uri)
    media = fetch_reddit_media(url)
    return jsonify({"media": media})

@app.route('/api/sponsorblock/<string:video_id>', methods=['GET'])
async def sponsored_segments(video_id):
    segments_dict = []
    return jsonify({"segments": segments_dict})

@app.before_serving
async def startup():
    app_port = config_manager.get("app.port", 5000)
    ngrok_token = os.environ.get('NGROK_TOKEN')
    public_url = None

    if ngrok_token:
        ngrok_manager = NgrokManager(ngrok_token, app_port)
        public_url = ngrok_manager.manage_ngrok()

    if public_url:
        print(' * Public URL:', public_url)
    
    ngrok_token = None

if __name__ == "__main__":
    opml_importer.load()
    config_manager.reload_config()
    app.run(
        host=config_manager.get("app.host", "0.0.0.0"),
        debug=config_manager.get("app.debug", False),
        port=config_manager.get("app.port", 5000)
    )
