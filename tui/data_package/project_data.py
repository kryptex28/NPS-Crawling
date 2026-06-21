from dataclasses import dataclass

@dataclass
class ProjectData:
    id: int
    name: str
    description: str
    categories: list[dict[str, str]]