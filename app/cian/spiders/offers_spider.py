import json
import os
from typing import Any, Generator, Iterable

from scrapy_playwright.page import PageMethod
from scrapy import Spider
from scrapy.http import Request, Response
from scrapy.spidermiddlewares.httperror import HttpError
from twisted.internet.error import DNSLookupError, TCPTimedOutError

from cian.items import OfferItem

os.makedirs("images", exist_ok=True)


class CianOffersSpider(Spider):
    name = "cian_offers"

    custom_settings = {
        "DOWNLOAD_HANDLERS": {
            "http": "scrapy_playwright.handler.ScrapyPlaywrightDownloadHandler",
            "https": "scrapy_playwright.handler.ScrapyPlaywrightDownloadHandler",
        }
    }

    version = "2025.03.26"

    allowed_domains = ["cian.ru"]
    start_urls = ["https://www.cian.ru/sitemap.xml"]

    def __init__(
        self,
        name: str | None = None,
        **kwargs: Any,
    ):
        super().__init__(name, **kwargs)

        self.logger.info("Starting CianOffers spider v%s", self.version)

        self.start_urls = [
            _["url"] for _ in json.load(open("urls.json", "r", encoding="utf-8"))
        ][: int(1e6)]

    def start_requests(self) -> Iterable[Request]:
        for url in self.start_urls:

            offer_id = url.split("/")[-2]

            yield Request(
                url=url,
                method="GET",
                callback=self.parse_offer,
                errback=self.handle_error,
                meta={
                    "playwright": True,
                    "playwright_page_methods": [
                        PageMethod(
                            "screenshot", path=f"images/{offer_id}.png", full_page=True
                        ),
                    ],
                    "offer_id": offer_id,
                },
            )

    def parse_offer(self, response: Response) -> Generator[OfferItem, None, None]:
        self.logger.info("Parsing offer %s", response.url)

        data = json.loads(self.extract_script(response))

        item = {}

        item["url"] = response.url
        item["image_urls"] = data["image"]
        item["plain_html"] = response.text
        item["screenshot_path"] = f"images/{response.meta['offer_id']}.png"
        yield OfferItem(**item)

    def extract_script(self, response: Response) -> str:
        return response.xpath("//script[@type='application/ld+json']/text()").get()

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
