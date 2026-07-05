from dataclasses import dataclass

@dataclass
class ProjectData:
    id: int
    name: str
    description: str
    crawl_config: str = ""
    preprocess_config: str = ""
    classification_config: str = ""