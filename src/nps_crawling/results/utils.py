"""Results pipeline module."""

import logging

from nps_crawling.config import Config

logger = logging.getLogger(__name__)


class ResultsPipeline(Config):
    """Results pipeline class."""
    def __init__(self):
        """Initialize the ResultsPipeline."""
        pass

    def results_workflow(self):
        """Results workflow method."""
        return None
