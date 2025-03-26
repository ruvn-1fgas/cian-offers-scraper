from typing import Any, Generator, Iterable
from urllib.parse import urljoin

from scrapy import Spider
from scrapy.http import Request, Response
from scrapy.spidermiddlewares.httperror import HttpError
from scrapy.utils.project import get_project_settings
from twisted.internet.error import DNSLookupError, TCPTimedOutError
import json
import re

from cian.items import OfferItem


class CianOffersSpider(Spider):
    name = "carbide"

    version = "2025.03.18"

    allowed_domains = ["cian.ru"]
    start_urls = [
        "https://www.cian.ru/",
    ]

    def __init__(self, name: str | None = None, **kwargs: Any) -> None:
        self.logger.info("Starting CianOffers spider %s", self.version)
        super().__init__(name, **kwargs)

        self.settings = get_project_settings()

    def start_requests(self) -> Iterable[Request]:
        return super().start_requests()

    def parse(self, response: Response) -> Iterable[Request]:
        self.logger.info("Received initial response from %s", response.url)

        yield from self.parse_category(response)

    def parse_category(self, response: Response) -> Iterable[Request]:
        self.logger.info("Parsing category %s", response.url)

        for entry in response.xpath("//div[@class='p_list']//a/@href").getall():
            yield Request(
                url=urljoin(response.url, entry),
                method="GET",
                callback=(
                    self.parse_category if not "html" in entry else self.parse_product
                ),
                errback=self.handle_error,
            )

        for entry in response.xpath("//div[@class='page_con']//a/@href").getall():
            if "javascript" in entry:
                continue

            yield Request(
                url=urljoin(response.url, entry),
                method="GET",
                callback=self.parse_category,
                errback=self.handle_error,
            )

    def parse_product(self, response: Response) -> Generator[OfferItem, None, None]:
        self.logger.info("Parsing product %s", response.url)

        item = {}
        item["url"] = response.url
        item["title"] = (
            response.xpath("//p[contains(@class,'e_text-5 s_title')]/text()")
            .get("")
            .strip()
        )

        description = response.xpath(
            "//div[contains(@class,'e_container-43 s_layout')]//text()"
        ).getall()
        description += response.xpath(
            "//div[contains(@class,'e_loop_sub-45 s_list')]//text()"
        ).getall()
        item["description"] = "\n".join(
            [_.strip().title() for _ in description if _.strip()]
        )

        item["image_urls"] = response.xpath(
            "//li[contains(@class,'static-img')]//img/@lazy"
        ).getall()
        table = response.xpath("//div[contains(@class,'e_container-27')]//table")
        header = []
        rows = []
        for index, tr in enumerate(table.xpath(".//tr")):
            cols = tr.xpath("./td")
            if not cols:
                continue

            row = [
                "\n".join(
                    [_.strip() for _ in col.xpath(".//text()").getall() if _.strip()]
                ).strip()
                for col in cols
            ]

            if index == 0:
                header = row
                continue

            rows.append(row)

        item["table_header"] = header
        item["table_rows"] = rows

        params = {
            "tid": "product",
            "siteType": "BUSINESS",
            "appId": self.get_app_id(response),
            "id": self.get_detail_id(response),
            "instance": self.get_instance_id(response),
            "pageType": self.get_page_type(response),
            "pageName": self.get_page_name(response),
        }

        yield Request(
            url="https://ru.oke-carbide.com.cn/nportal/fwebapi/cms/lowcode/crumbs/getCrumbs?"
            + self.dict_to_params(params),
            callback=self.parse_breadcrumbs,
            errback=self.handle_error,
            meta={"item": item},
            dont_filter=True,
        )

    def get_app_id(self, response: Response) -> str:
        app_id = (
            re.search(r"\"appId\":\s?\"(.+)\",\s?\"pageMother", response.text)
            .group(1)
            .strip()
        )
        return app_id

    def get_detail_id(self, response: Response) -> str:
        detail_id = (
            re.search(r"\"_detailId\":\s?\"(.+)\",\s?\"renderInfo", response.text)
            .group(1)
            .strip()
        )
        return detail_id

    def get_instance_id(self, response: Response) -> str:
        instance = (
            re.search(r"\"instanceId\":\s?\"(.+)\",\s?\"pageId", response.text)
            .group(1)
            .strip()
        )
        return instance

    def get_page_type(self, response: Response) -> str:
        page_type = (
            re.search(r"\"pageType\":\s?\"(.+)\",\s?\"contentType", response.text)
            .group(1)
            .strip()
        )
        return page_type

    def get_page_name(self, response: Response) -> str:
        page_name = (
            re.search(r"\"name\":\s?\"(.+)\",\s?\"filename", response.text)
            .group(1)
            .strip()
        )
        return page_name

    def get_page_id(self, response: Response) -> str:
        page_id = (
            re.search(r"\"pageId\":\s?\"(.+)\",\s?\"pageName", response.text)
            .group(1)
            .strip()
        )
        return page_id

    def dict_to_params(self, data: dict) -> str:
        return "&".join(
            [f"{key}={value}" for key, value in data.items() if value is not None]
        )

    def parse_breadcrumbs(self, response: Response) -> Iterable[Request]:
        item = response.meta["item"]

        self.logger.info("Parsing breadcrumbs for %s", item["url"])

        data = response.json()["data"]["list"]
        item["breadcrumbs"] = [_[0] for _ in data]

        yield OfferItem(**item)

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
