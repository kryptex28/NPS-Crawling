from nps_crawling.config import Config

def update_config_from_dict(data: dict) -> None:

    crawler_global_limit: int = data.get("crawler_global_limit", -1)
    crawler_dry_run: bool = data.get("crawler_dry_run", False)
    crawler_delay: float = data.get("crawler_delay", 0.1)
    crawler_user_agent: str = data.get("crawler_user_agent", "")
    crawler_stats_dump: bool = data.get("crawler_stats_dump", True)

    database_table_name: str = data.get("database_table_name", "nps_filings")
    database_connection_string: str = data.get("database_connection_string", "")
    database_local_mode: bool = data.get("database_local_mode", False)

    preprocessing_keyword_str: str = data.get("preprocessing_keyword_list", "")
    preprocessing_keyword_list: list[str] = preprocessing_keyword_str.split(",")
    preprocessing_keyword_exclude_str: str = data.get("preprocessing_keyword_exclude_list", "")
    preprocessing_keyword_exclude_list: list[str] = preprocessing_keyword_exclude_str.split(",")
    preprocessing_threshold_value: float = data.get("preprocessing_threshold_value", 0.5)
    
    model_selection: str = str(data.get("model_selection", "svm")).upper()
    model_persona: str = data.get("model_persona_prompt", "")


    Config.DATABASE_TABLE_NAME = database_table_name
    Config.LOCAL_MODE = database_local_mode

    Config.LIST_OF_PHRASES_TO_FILTER_FILINGS_FOR = preprocessing_keyword_list.copy()
    Config.LIST_OF_PHRASES_TO_FILTER_FILINGS_FOR = preprocessing_keyword_exclude_list.copy()
    Config.SIMILARITY_THRESHOLD_CONTEXT_WINDOW = preprocessing_threshold_value

    Config.MODEL = model_selection
    Config.OLLAMA_PERSONA = model_persona