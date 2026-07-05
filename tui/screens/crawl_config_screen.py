from __future__ import annotations
from textual.app import ComposeResult
from textual.containers import Container, Horizontal, ScrollableContainer
from textual.screen import ModalScreen
from textual.widgets import Button, Static, Label, Input
from textual import on

from models.crawl_model import CrawlModel


class CrawlConfigScreen(ModalScreen):
    CSS_PATH = "crawl_config_screen.tcss"

    def __init__(self) -> None:
        super().__init__()
        self.model = CrawlModel()
        self.config_path = self.model.get_config_path()
        self.config_data = self.model.get_config()

    def compose(self) -> ComposeResult:
        with Container():
            yield Static(f"Configure Crawl ({self.config_path.name})", classes="modal-title")
            
            with ScrollableContainer(id="crawl-config-form"):
                # Query Path
                with Horizontal(classes="form-row"):
                    yield Label("Query Path:")
                    yield Input(self.config_data.get("query_path", ""), id="crawl-query-path")

                # SEC Query Limit Count
                with Horizontal(classes="form-row"):
                    yield Label("SEC Query Limit Count:")
                    yield Input(str(self.config_data.get("sec_query_limit_count", 10000)), id="crawl-limit-count")

                # Download Delay
                with Horizontal(classes="form-row"):
                    yield Label("Download Delay:")
                    yield Input(str(self.config_data.get("download_delay", 0.2)), id="crawl-download-delay")

            with Horizontal(classes="modal-footer"):
                yield Button("Save", variant="success", id="save-config-btn")
                yield Button("Cancel", variant="error", id="cancel-config-btn")

    @on(Button.Pressed, "#cancel-config-btn")
    def cancel(self) -> None:
        self.dismiss()

    @on(Button.Pressed, "#save-config-btn")
    def save(self) -> None:
        try:
            updates = {
                "query_path": self.query_one("#crawl-query-path", Input).value.strip(),
                "sec_query_limit_count": int(self.query_one("#crawl-limit-count", Input).value),
                "download_delay": float(self.query_one("#crawl-download-delay", Input).value),
            }

            self.model.save_config(updates)
            self.app.notify("Crawl configuration saved successfully.", severity="information")
            self.dismiss(True)
        except ValueError:
            self.app.notify("Invalid number value: please verify numeric fields.", severity="error")
        except Exception as e:
            self.app.notify(f"Error saving configuration: {e}", severity="error")
