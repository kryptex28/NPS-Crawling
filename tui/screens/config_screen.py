from __future__ import annotations

from textual import on
from textual.containers import Container, Horizontal, ScrollableContainer, Vertical
from textual.screen import ModalScreen
from textual.validation import Number
from textual.widgets import Button, Input, Label, Select, Static, Switch

from data_package.config_data import ConfigData
from models.config_model import ConfigModel
from nps_crawling.config import Config


class ConfigScreen(ModalScreen):
    CSS_PATH = "config_screen.tcss"

    def __init__(self):
        super().__init__()
        self.model = ConfigModel()

    def compose(self):
        with Container():
            yield Static("Configuration", classes="dialog-title")
            with ScrollableContainer():
                yield Static("Active project", classes="section-header")
                with Vertical(classes="config-row"):
                    yield Label("Project")
                    yield Input("", id="cfg-active-project", disabled=True)

                yield Static("Crawler configuration", classes="section-header")

                with Vertical(classes="config-row"):
                    yield Label("Query path (relative to repo root)")
                    yield Input("", id="cfg-query-path")

                with Vertical(classes="config-row"):
                    yield Label("Result limit")
                    yield Input("", id="cfg-global-limit", validators=[Number(minimum=-1)])

                with Horizontal(classes="switch-row"):
                    yield Label("Dry run")
                    yield Switch(False, id="cfg-dry-run")

                with Vertical(classes="config-row"):
                    yield Label("Delay between requests (s)")
                    yield Input("", id="cfg-delay", validators=[Number(minimum=0)])

                yield Static("Database (environment)", classes="section-header")

                with Vertical(classes="config-row"):
                    yield Label("Table name")
                    yield Input("", id="cfg-table-name", disabled=True)

                with Vertical(classes="config-row"):
                    yield Label("Connection string")
                    yield Input("", id="cfg-conn-string", disabled=True)

                with Horizontal(classes="switch-row"):
                    yield Label("Local mode")
                    yield Switch(False, id="cfg-local-mode", disabled=True)

                yield Static("Preprocessing configuration", classes="section-header")

                with Vertical(classes="config-row"):
                    yield Label("Preprocessing version")
                    yield Input("", id="cfg-preprocessing-version")

                with Vertical(classes="config-row"):
                    yield Label("Keyword list (comma-separated)")
                    yield Input("", id="cfg-keyword-list")

                with Vertical(classes="config-row"):
                    yield Label("Keyword exclude list (comma-separated)")
                    yield Input("", id="cfg-keyword-exclude")

                with Vertical(classes="config-row"):
                    yield Label("Threshold keyword scope (comma-separated)")
                    yield Input("", id="cfg-threshold-scope")

                with Vertical(classes="config-row"):
                    yield Label("Similarity threshold")
                    yield Input("", id="cfg-similarity-threshold", validators=[Number(minimum=0, maximum=1)])

                yield Static("Classification configuration", classes="section-header")

                with Vertical(classes="config-row"):
                    yield Label("Classification version")
                    yield Input("", id="cfg-classification-version")

            with Horizontal(classes="dialog-footer"):
                yield Button("Save", variant="primary", id="cfg-save")
                yield Button("Cancel", variant="default", id="cfg-cancel")

    def on_mount(self) -> None:
        self._populate(self.model.get_config())

    def _populate(self, config_data: ConfigData) -> None:
        self.query_one("#cfg-active-project", Input).value = config_data.active_project or ""
        self.query_one("#cfg-query-path", Input).value = config_data.crawl_query_path
        self.query_one("#cfg-global-limit", Input).value = str(
            config_data.crawl_sec_query_limit_count,
        )
        self.query_one("#cfg-dry-run", Switch).value = config_data.crawler_dry_run
        self.query_one("#cfg-delay", Input).value = str(config_data.crawl_download_delay)
        self.query_one("#cfg-table-name", Input).value = config_data.database_table_name
        self.query_one("#cfg-conn-string", Input).value = config_data.local_db_connection
        self.query_one("#cfg-local-mode", Switch).value = config_data.local_mode
        self.query_one("#cfg-preprocessing-version", Input).value = (
            config_data.preprocessing_version
        )
        self.query_one("#cfg-classification-version", Input).value = (
            config_data.classification_version
        )
        self.query_one("#cfg-keyword-list", Input).value = ", ".join(config_data.keyword_list)
        self.query_one("#cfg-keyword-exclude", Input).value = ", ".join(
            config_data.keyword_exclude,
        )
        self.query_one("#cfg-threshold-scope", Input).value = ", ".join(
            config_data.threshold_keyword_scope,
        )
        self.query_one("#cfg-similarity-threshold", Input).value = str(
            config_data.similarity_threshold,
        )

    def _parse_csv_list(self, raw: str) -> list[str]:
        return [part.strip() for part in raw.split(",") if part.strip()]

    @on(Button.Pressed, "#cfg-save")
    def save(self) -> None:
        if not Config.ACTIVE_PROJECT:
            self.app.notify(
                "Load a project before saving configuration.",
                severity="warning",
            )
            return

        try:
            config_data = ConfigData(
                crawl_query_path=self.query_one("#cfg-query-path", Input).value.strip(),
                crawl_sec_query_limit_count=int(
                    self.query_one("#cfg-global-limit", Input).value,
                ),
                crawl_download_delay=float(self.query_one("#cfg-delay", Input).value),
                crawler_dry_run=self.query_one("#cfg-dry-run", Switch).value,
                preprocessing_version=self.query_one(
                    "#cfg-preprocessing-version",
                    Input,
                ).value.strip(),
                classification_version=self.query_one(
                    "#cfg-classification-version",
                    Input,
                ).value.strip(),
                keyword_list=self._parse_csv_list(
                    self.query_one("#cfg-keyword-list", Input).value,
                ),
                keyword_exclude=self._parse_csv_list(
                    self.query_one("#cfg-keyword-exclude", Input).value,
                ),
                threshold_keyword_scope=self._parse_csv_list(
                    self.query_one("#cfg-threshold-scope", Input).value,
                ),
                similarity_threshold=float(
                    self.query_one("#cfg-similarity-threshold", Input).value,
                ),
            )
            self.model.update_config(config_data)
        except Exception as exc:
            self.app.notify(f"Could not save configuration: {exc}", severity="error")
            return

        self.app.notify("Configuration saved to project JSON files.", severity="information")
        self.dismiss(True)

    @on(Button.Pressed, "#cfg-cancel")
    def cancel(self) -> None:
        self.dismiss(False)
