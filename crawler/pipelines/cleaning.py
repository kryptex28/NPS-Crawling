from scrapy.exceptions import DropItem
from bs4 import BeautifulSoup
import re


class CleanTextPipeline:

    def process_item(self, item: dict, spider) -> dict:
        """
        Clean the 'html_text' field of an item by removing HTML tags,
        normalizing whitespace, and stripping signature markers.
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
