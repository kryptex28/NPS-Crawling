from dataclasses import dataclass

@dataclass
class ConfigData():

    crawler_limit: int = -1
    crawler_dry_run: bool = False
    crawler_delay: float = 0.1
    crawler_stats_dump: bool = False
    
    #db_table_name: str = "nps_filings_table"
    #db_connection: str = "crawler:crawler@localhost:5432/crawler"
    #db_local_mode: bool = False
#
    #pp_keyword_list: list[str] = []
    #pp_keyword_exclude: list[str] = []
    #pp_threshold_value: float = 0.5
#
    #model_model_selection: str = "svm"
    #model_persona_prompt: str = ""