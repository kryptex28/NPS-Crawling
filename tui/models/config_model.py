from typing_extensions import Self

from data_package.ConfigData import ConfigData
from nps_crawling.config import Config

class ConfigModel():

    instance = None

    def __new__(cls) -> Self:
        if cls.instance is None:
            cls.instance = super().__new__(cls)
        return cls.instance

    def __init__(self) -> None:
        pass

    def update_config(self, config_data: ConfigData) -> None:
        Config.CRAWLER_GLOBAL_LIMIT = config_data.crawler_limit

    def get_config(self) -> ConfigData:
        return ConfigData()