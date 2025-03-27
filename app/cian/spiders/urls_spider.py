import gzip
import io
import json
from typing import Any, Generator, Iterable

from scrapy import Selector, Spider
from scrapy.http import Request, Response
from scrapy.spidermiddlewares.httperror import HttpError
from twisted.internet.error import DNSLookupError, TCPTimedOutError

from cian.items import UrlItem


class CianOffersSpider(Spider):
    name = "cian_offers_urls"

    version = "2025.03.26"

    allowed_domains = ["cian.ru"]
    start_urls = ["https://www.cian.ru/sitemap.xml"]

    def __init__(
        self,
        name: str | None = None,
        **kwargs: Any,
    ):
        super().__init__(name, **kwargs)

        self.logger.info("Starting CianOffersUrls spider v%s", self.version)
        self.hosts = [
            region["baseHost"]
            for region in json.load(open("regions.json", "r", encoding="utf-8"))
        ]

    def start_requests(self) -> Iterable[Request]:
        for host in self.hosts:
            yield Request(
                url=host + "/sitemap.xml",
                method="GET",
                callback=self.parse,
                errback=self.handle_error,
            )

    def parse(self, response: Response) -> Iterable[Request]:
        self.logger.info("Received initial response from %s", response.url)

        for gz_url in Selector(text=response.text).xpath("//loc/text()").getall():
            yield Request(
                url=gz_url,
                method="GET",
                callback=self.parse_gz_sitemap,
                errback=self.handle_error,
            )

    def parse_gz_sitemap(self, response: Response) -> Generator[UrlItem, None, None]:
        self.logger.info("Received initial response from %s", response.url)

        with gzip.GzipFile(fileobj=io.BytesIO(response.body), mode="rb") as f:
            for url in (
                Selector(text=f.read().decode("utf-8")).xpath("//loc/text()").getall()
            ):
                if not any(
                    pattern in url for pattern in ["/sale/flat/", "/rent/flat/"]
                ):
                    continue

                yield UrlItem(**{"url": url})

    def handle_error(self, failure) -> None:
        if failure.check(HttpError):
            self.logger.error(
                "HttpError on %s. Status code: %s",
                failure.value.response.url,
                failure.value.response.status,
            )

        elif failure.check(DNSLookupError):
            self.logger.error("DNSLookupError on %s", failure.request.url)
        elif failure.check((TimeoutError, TCPTimedOutError)):
            self.logger.error("TimeoutError on %s", failure.request.url)
