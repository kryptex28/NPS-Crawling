from scrapy.exceptions import DropItem

class NpsMentionFilterPipeline:
    def process_item(self, item, spider):
        return item
