"""Text cleaning pipeline for preprocessing HTML content."""

import re

from bs4 import BeautifulSoup

from nps_crawling.config import Config


class CleanTextPipeline(Config):
    """Text cleaning pipeline class."""

    def cleaning_workflow(self, dict_batch):
        """Clean a batch of items by processing their 'html_text' fields."""
        cleaned_batch = []

        for item in dict_batch:
            cleaned_item = self.process_item(item)
            cleaned_batch.append(cleaned_item)

        return cleaned_batch

    def process_item(self, item: dict) -> dict:
        """Clean the 'html_text' field of an item by removing HTML tags.

        Normalizing whitespace, and stripping signature markers.
        """
        if "html_text" in item and isinstance(item["html_text"], str):
            # Parse HTML content into plain text
            soup = BeautifulSoup(item["html_text"], "html.parser")

            # Extract visible text while keeping spaces between elements
            text = soup.get_text(separator=" ", strip=True)

            # Replace non-breaking spaces with normal spaces
            text = text.replace("\xa0", " ")

            # Remove signature-like markers such as '/s/ Name'
            text = re.sub(r'By:\s*/s/\s*[A-Za-z .-]+', '', text, flags=re.IGNORECASE)  # By: /s/ Name Name2
            text = re.sub(r'/s/\s*[A-Za-z .-]+', '', text)  # /s/ Name Name2

            # Store cleaned text back into the item
            item["html_text"] = text

        return item
