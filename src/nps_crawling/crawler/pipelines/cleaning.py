"""Pipeline to clean HTML text from scraped items."""

import re

from bs4 import BeautifulSoup


class CleanTextPipeline:
    """Pipeline to clean HTML text from items."""

    def process_item(self, item, spider):
        """Process an item.

        Clean the 'html_text' field of an item by removing HTML tags,
        normalizing whitespace, and stripping signature markers.
        """
        #if "html_text" in item and isinstance(item["html_text"], str):
        if item["core_text"] is not None and item['filing'].file_container_type in ['html', 'xml', 'htm']:
            # Parse HTML content into plain text
            soup = BeautifulSoup(item["core_text"], "html.parser")

            # Extract visible text while keeping spaces between elements
            text = soup.get_text(separator=" ", strip=True)

            # Replace non-breaking spaces with normal spaces
            text = text.replace("\xa0", " ")

            # Remove signature-like markers such as '/s/ Name'
            text = re.sub(r'By:\s*/s/\s*[A-Za-z .-]+', '', text, flags=re.IGNORECASE)  # By: /s/ Name Name2
            text = re.sub(r'/s/\s*[A-Za-z .-]+', '', text)  # /s/ Name Name2

            # Store cleaned text back into the item
            item["core_text"] = text

        return item