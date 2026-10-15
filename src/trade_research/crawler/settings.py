"""Conservative defaults for crawling public government sources."""

BOT_NAME = "trade_cert_research"
SPIDER_MODULES = ["trade_research.crawler.spiders"]
NEWSPIDER_MODULE = "trade_research.crawler.spiders"
USER_AGENT = "TradeCertificationResearch/0.2 (+evidence-first research)"
ROBOTSTXT_OBEY = True
CONCURRENT_REQUESTS = 8
CONCURRENT_REQUESTS_PER_DOMAIN = 2
DOWNLOAD_DELAY = 0.5
DOWNLOAD_TIMEOUT = 20
DOWNLOAD_MAXSIZE = 25 * 1024 * 1024
RETRY_ENABLED = True
RETRY_TIMES = 2
AUTOTHROTTLE_ENABLED = True
AUTOTHROTTLE_START_DELAY = 0.5
AUTOTHROTTLE_MAX_DELAY = 15
COOKIES_ENABLED = False
TELNETCONSOLE_ENABLED = False
EXTENSIONS = {"scrapy.extensions.remote_control.RemoteControl": None}
LOG_LEVEL = "WARNING"
FEED_EXPORT_ENCODING = "utf-8"
