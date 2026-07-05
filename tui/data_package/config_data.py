from dataclasses import dataclass, field


@dataclass
class ConfigData:
    """Editable pipeline settings surfaced in the TUI configuration screen."""

    crawl_sec_query_limit_count: int = 10_000
    crawl_download_delay: float = 0.2
    crawl_query_path: str = "query"
    crawler_dry_run: bool = False

    preprocessing_version: str = "version_2"
    classification_version: str = "version_1"
    similarity_threshold: float = 0.8
    keyword_list: list[str] = field(default_factory=list)
    keyword_exclude: list[str] = field(default_factory=list)
    threshold_keyword_scope: list[str] = field(default_factory=list)

    active_project: str | None = None
    database_table_name: str = "default"
    local_db_connection: str = ""
    local_mode: bool = False
