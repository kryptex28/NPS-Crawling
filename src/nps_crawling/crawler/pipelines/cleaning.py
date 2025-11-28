"""Pipelines for cleaning crawled data."""


class CleanTextPipeline:
    """Pipeline to clean text data in items."""
    def process_item(self, item, spider):
        """Clean the html_text field of the item."""
        return item
