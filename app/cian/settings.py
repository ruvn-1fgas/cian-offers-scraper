# Scrapy settings for cian project
#
# For simplicity, this file contains only settings considered important or
# commonly used. You can find more set# Scrapy settings for gosuslugi_accredited project
#
#     https://docs.scrapy.org/en/latest/topics/settings.html
#     https://docs.scrapy.org/en/latest/topics/downloader-middleware.html
#     https://docs.scrapy.org/en/latest/topics/spider-middleware.html
import inspect
import os
import sys
from datetime import datetime

from dotenv import load_dotenv

from cian.items import *

load_dotenv()

BOT_NAME = "cian"


# Proxy Configuration
PROXY_ENABLED = False

# Logging Configuration
LOG_LEVEL = "INFO"
os.makedirs("logs", exist_ok=True)
LOG_FILE = f"./logs/{datetime.now().strftime('%Y.%m.%d')}.log"

SPIDER_MODULES = ["cian.spiders"]
NEWSPIDER_MODULE = "cian.spiders"

DEFAULT_HEADERS = {}

# User Agent
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 YaBrowser/24.4.0.0 Safari/537.36"

# Robots.txt
ROBOTSTXT_OBEY = False

# Concurrency Settings
CONCURRENT_REQUESTS = 16
CONCURRENT_REQUESTS_PER_DOMAIN = 16

DOWNLOAD_DELAY = 0.25 / 16

# Cookies
COOKIES_ENABLED = True
COOKIES_DEBUG = False

# Headers
DEFAULT_REQUEST_HEADERS = {}

# Pipelines
ITEM_PIPELINES = {
    "cian.pipelines.MongoDBPipeline": 100,
}

# Handlers
DOWNLOAD_HANDLERS = {}


# Downloader Middlewares
DOWNLOADER_MIDDLEWARES = {}

# Extensions
EXTENSIONS = {}

# Reactor and Encoding
REQUEST_FINGERPRINTER_IMPLEMENTATION = "2.7"
TWISTED_REACTOR = "twisted.internet.asyncioreactor.AsyncioSelectorReactor"
FEED_EXPORT_ENCODING = "utf-8"


# Feed Export Configuration
FEED_TEMPLATE = {
    "format": "json",
    "encoding": "utf-8",
    "store_empty": False,
    "fields": None,
    "overwrite": True,
}

ITEM_CLASSES = [
    cls
    for name, cls in inspect.getmembers(
        sys.modules[f"{BOT_NAME}.items"], inspect.isclass
    )
    if hasattr(cls, "feed_name") and cls != DynamicItem
]

FEEDS = {
    f"./data/{item_class.feed_name}_{datetime.now().strftime('%Y.%m.%d')}.json": {
        **FEED_TEMPLATE,
        "item_classes": [item_class],
    }
    for item_class in ITEM_CLASSES
}

# Proxy Configuration
if PROXY_ENABLED:
    DOWNLOADER_MIDDLEWARES.update(
        {
            "rotating_proxies.middlewares.RotatingProxyMiddleware": 610,
            "rotating_proxies.middlewares.BanDetectionMiddleware": 620,
        }
    )

    ROTATING_PROXY_LIST_PATH = os.getenv("ROTATING_PROXY_LIST_PATH")
    ROTATING_PROXY_LIST_X_KEY = os.getenv("ROTATING_PROXY_LIST_X_KEY")

PLAYWRIGHT_BROWSER_TYPE = "chromium"
PLAYWRIGHT_MAX_PAGES_PER_CONTEXT = 4
PLAYWRIGHT_LAUNCH_OPTIONS = {
    "headless": False,
    "timeout": 2 * 1000,
    "args": [
        "--disable-blink-features=AutomationControlled",
        "--use-gl=swiftshader",
        "--enable-automation",
        "--unsafely-disable-devtools-self-xss-warnings",
        "--disable-site-isolation-trials",
        "--no-experiments",
        "--no-sandbox",
        "--disable-web-security",
        "--disable-site-isolation-trials",
        "--blink-settings=imagesEnabled=false",
        "--disable-gpu",
        "--disable-software-rasterizer",
    ],
}
PLAYWRIGHT_DEFAULT_NAVIGATION_TIMEOUT = 30 * 1000

MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
MONGO_DATABASE = "offers"
