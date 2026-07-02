from typing_extensions import Self

from data_package.config_data import ConfigData
from data_package.prompt_data import PromptData
from data_package.table_data import TableData
from nps_crawling.config import Config

from nps_crawling.db.db_adapter import DbAdapter

class ConfigModel():

    instance = None

    def __new__(cls) -> Self:
        if cls.instance is None:
            cls.instance = super().__new__(cls)
        return cls.instance

    def __init__(self) -> None:
        self.prompts: list[PromptData] = []
        self.columns: list[TableData] = []
        pass

    def update_config(self, config_data: ConfigData) -> None:
        Config.CRAWLER_GLOBAL_LIMIT = config_data.crawler_limit
        DbAdapter().ensure_table_exists()

    def get_config(self) -> ConfigData:
        return ConfigData()
    
    def add_prompt(self, data: PromptData) -> None:
        self.prompts.append(data)

    def add_column(self, data: TableData) -> None:
        self.columns.append(data)