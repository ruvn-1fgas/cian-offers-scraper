import base64

import pymongo
from itemadapter import ItemAdapter

from cian.items import OfferItem


class MongoDBPipeline:
    collection = "offers"

    def __init__(self, mongodb_uri, mongodb_db):
        self.mongodb_uri = mongodb_uri
        self.mongodb_db = mongodb_db

        self.client = pymongo.MongoClient(self.mongodb_uri)

        if self.mongodb_db not in self.client.list_database_names():
            self.client[self.mongodb_db].create_collection(
                self.collection, capped=False
            )

        self.db = self.client[self.mongodb_db]

    @classmethod
    def from_crawler(cls, crawler):
        return cls(
            mongodb_uri=crawler.settings.get("MONGODB_URI"),
            mongodb_db=crawler.settings.get("MONGODB_DATABASE", "offers"),
        )

    def open_spider(self, spider):
        pass

    def close_spider(self, spider):
        self.client.close()

    def process_item(self, item, spider):
        if not isinstance(item, OfferItem):
            return item

        adapter = ItemAdapter(item)
        img_path = adapter.get("screenshot_path")

        if img_path:
            adapter["screenshot_base64"] = self._convert_image_to_base64(img_path)
            del adapter["screenshot_path"]

        self.db[self.collection].insert_one(adapter.asdict())

        return item

    def _convert_image_to_base64(self, img_path):
        with open(img_path, "rb") as image_file:
            encoded_string = base64.b64encode(image_file.read()).decode("utf-8")
        return encoded_string
