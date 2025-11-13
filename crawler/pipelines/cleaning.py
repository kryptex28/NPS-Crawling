class CleanTextPipeline:
    def process_item(self, item, spider):
        item["content_excerpt"] = " ".join(item["content_excerpt"].split())
        return item
