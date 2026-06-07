import os
from os.path import isdir, join

from nps_crawling.crawler.pre_fetch_utils.sec_params import create_config_from_dict, create_search_params_from_config_dir, store_config, get_search_params_from_id
from nps_crawling.crawler.pre_fetch_utils.sec_params import SecSearchParams
from nps_crawling.config import Config

def svc_create_query(data: dict):
    parameter: SecSearchParams = create_config_from_dict(data=data)
    parameter.query_base = "https://efts.sec.gov/LATEST/search-index?"
    store_config(path=Config.GUI_QUERY_PATH, parameter=parameter)

    return True

def svc_delete_query(id: str):
    if os.path.isdir(Config.GUI_QUERY_PATH):
        os.remove(join(Config.GUI_QUERY_PATH, f"{id}.json"))
        return True
    else:
        return False

def svc_get_queries() -> list[dict]:
    if not os.path.isdir(Config.GUI_QUERY_PATH):
        return []
    
    params: list[SecSearchParams] = create_search_params_from_config_dir(str(Config.GUI_QUERY_PATH))
    return [{"id": p.id, **p.create_dict()} for p in params]