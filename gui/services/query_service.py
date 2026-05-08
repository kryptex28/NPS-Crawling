import os

from nps_crawling.crawler.pre_fetch_utils.sec_params import create_config_from_dict, create_search_params_from_config_dir, create_config_from_search_params
from nps_crawling.crawler.pre_fetch_utils.sec_params import SecSearchParams
from nps_crawling.config import Config

def svc_create_query(data: dict):
    parameter: SecSearchParams = create_config_from_dict(data=data)
    
    


def svc_delete_query(id: str):
    pass

def svc_get_queries() -> list[dict]:
    if not os.path.isdir(Config.GUI_QUERY_PATH):
        return []
    else:
        params: list[SecSearchParams] = create_search_params_from_config_dir(str(Config.GUI_QUERY_PATH))

        data: list[dict] = []

        for parameter in params:
            data.append(parameter.create_dict())
        return data