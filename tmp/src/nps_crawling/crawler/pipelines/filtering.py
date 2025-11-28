"""Pipelines for filtering crawled data."""


class NpsMentionFilterPipeline:
    """Pipeline to filter items for NPS mentions."""
    def process_item(self, item, spider):
        """Filter items that mention NPS."""
        return item
