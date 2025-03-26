from typing import Any, Generator, Iterable

from scrapy import Spider
from scrapy.http import Request, Response
from scrapy.spidermiddlewares.httperror import HttpError
from twisted.internet.error import DNSLookupError, TCPTimedOutError

from cian.items import RegionItem


class CianRegionsSpider(Spider):
    name = "cian_regions"

    version = "2025.03.26"

    allowed_domains = ["cian.ru"]
    start_urls = [
        "https://api.cian.ru/geo-temp-layer/v1/get-federal-subjects-of-russia/"
    ]

    total_urls = 0

    def __init__(
        self,
        name: str | None = None,
        **kwargs: Any,
    ):
        super().__init__(name, **kwargs)

        self.logger.info("Starting CianRegions spider v%s", self.version)

    def start_requests(self) -> Iterable[Request]:
        return super().start_requests()

    def parse(self, response: Response) -> Iterable[Request]:
        self.logger.info("Received initial response from %s", response.url)

        for entry in response.json()["items"]:
            yield Request(
                url=f"https://spb.cian.ru/cian-api/site/v1/get-region/?regionId={entry['id']}",
                method="GET",
                callback=self.parse_region,
                errback=self.handle_error,
                meta={"region": entry},
            )

    def parse_region(self, response: Response) -> Generator[RegionItem, None, None]:
        self.logger.info("Parsing region %s", response.meta["region"]["displayName"])

        yield RegionItem(**response.json()["data"])

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
