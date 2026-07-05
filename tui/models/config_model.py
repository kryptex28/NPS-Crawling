from typing_extensions import Self

from data_package.config_data import ConfigData
from data_package.prompt_data import PromptData
from data_package.table_data import TableData
from nps_crawling.config import Config
from nps_crawling.project_config import save_project_section
from utils.pipeline_reset import reset_pipeline_models


class ConfigModel:

    instance = None

    def __new__(cls) -> Self:
        """Create or return the singleton instance of ConfigModel."""
        if cls.instance is None:
            cls.instance = super().__new__(cls)
        return cls.instance

    def __init__(self) -> None:
        """Initialize the ConfigModel instance."""
        self.prompts: list[PromptData] = []
        self.columns: list[TableData] = []

    def get_config(self) -> ConfigData:
        """Retrieve the application config details, including prompts and tables."""
        Config.reload_config()
        scope = Config.THRESHOLD_KEYWORD_SCOPE or []
        try:
            query_path = str(Config.QUERY_PATH.relative_to(Config.ROOT_DIR))
        except ValueError:
            query_path = str(Config.QUERY_PATH)
        return ConfigData(
            crawl_sec_query_limit_count=Config.CRAWL_SEC_QUERY_LIMIT_COUNT,
            crawl_download_delay=Config.CRAWL_DOWNLOAD_DELAY,
            crawl_query_path=query_path,
            preprocessing_version=Config.PREPROCESSING_VERSION,
            classification_version=Config.CLASSIFICATION_VERSION,
            similarity_threshold=Config.SIMILARITY_THRESHOLD_CONTEXT_WINDOW,
            keyword_list=list(Config.LIST_OF_PHRASES_TO_FILTER_FILINGS_FOR),
            keyword_exclude=list(Config.LIST_OF_PHRASES_TO_EXCLUDE),
            threshold_keyword_scope=list(scope),
            active_project=Config.ACTIVE_PROJECT,
            database_table_name=Config.DATABASE_TABLE_NAME,
            local_db_connection=Config.LOCAL_DB_CONNECTION,
            local_mode=Config.LOCAL_MODE,
        )

    def update_config(self, config_data: ConfigData) -> None:
        """Save config updates and reload the configuration."""
        if not Config.ACTIVE_PROJECT:
            raise RuntimeError("Load a project before saving configuration.")

        save_project_section(
            "crawl",
            {
                "query_path": config_data.crawl_query_path,
                "sec_query_limit_count": config_data.crawl_sec_query_limit_count,
                "download_delay": config_data.crawl_download_delay,
            },
            Config.ROOT_DIR,
        )
        save_project_section(
            "preprocess",
            {
                "version": config_data.preprocessing_version,
                "similarity_threshold_context_window": config_data.similarity_threshold,
                "list_of_phrases_to_filter_filings_for": config_data.keyword_list,
                "list_of_phrases_to_exclude": config_data.keyword_exclude,
                "threshold_keyword_scope": config_data.threshold_keyword_scope or None,
            },
            Config.ROOT_DIR,
        )
        save_project_section(
            "classification",
            {"version": config_data.classification_version},
            Config.ROOT_DIR,
        )

        Config.reload_config()
        reset_pipeline_models()

    def add_prompt(self, data: PromptData) -> None:
        """Add a classification prompt configuration."""
        self.prompts.append(data)

    def add_column(self, data: TableData) -> None:
        """Add a table column configuration."""
        self.columns.append(data)

    def load_prompts(self) -> None:
        """Reload classification prompts from configuration."""
        pass

    def load_columns(self) -> None:
        """Reload table columns from configuration."""
        self.columns = [
            TableData(column_name=cat["name"], datatype=cat["type"])
            for cat in Config.PROJECT_CATEGORIES
        ]
