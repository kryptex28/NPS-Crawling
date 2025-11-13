from scrapy.exceptions import DropItem

class NpsMentionFilterPipeline:
    def process_item(self, item, spider):
        if not item.get("content_excerpt"):
            raise DropItem("No NPS mention found")
        return item
