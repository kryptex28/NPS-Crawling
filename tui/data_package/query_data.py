from dataclasses import (
    dataclass, 
    field
    )

@dataclass
class QueryData:
    id: str = ""
    query_base: str = ""
    keyword: str = ""
    entity: str = ""
    cik: str = ""
    entity_title: str = ""
    filing_category: str = ""
    filing_types: list[str] = field(default_factory=list)
    date_range: str = "all"
    from_date: str = ""
    to_date: str = ""
    limit: int = -1
    selected: bool = False
    created_at: str = ""

    def summary(self) -> str:
        parts = []
        if self.keyword:
            parts.append(f'q="{self.keyword}"')
        if self.entity:
            parts.append(f"entity={self.entity}")
        if self.filing_types:
            parts.append(f"types={','.join(self.filing_types[:3])}{'…' if len(self.filing_types) > 3 else ''}")
        if self.date_range != "all":
            parts.append(f"date={self.date_range}")
        return "  |  ".join(parts) if parts else "(empty query)"