from nps_crawling.config import Config

def update_config_from_dict(data: dict) -> None:
    crawler_global_limit: int = data["crawler_global_limit"]

    Config.DATABASE_TABLE_NAME = data["database_table_name"]
    print(Config.DATABASE_TABLE_NAME)