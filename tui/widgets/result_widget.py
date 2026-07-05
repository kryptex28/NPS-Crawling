from __future__ import annotations

from textual import on
from textual.app import ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.widgets import Button, Checkbox, Static

from models.result_model import ResultModel


class ResultWidget(Container):

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.model = ResultModel()
        self._last_export_path: str | None = None

    def compose(self) -> ComposeResult:
        with Horizontal():
            with Vertical():
                yield Static("Result", classes="panel-title")
                with Horizontal(classes="form-row", id="result-controls"):
                    yield Checkbox("Export only relevant data", value=False, id="cb-only-relevant")
                    yield Button("Export Results", id="btn-export-results", variant="primary")
                    yield Button("Open Export", id="btn-open-export", variant="default")

    @on(Button.Pressed, "#btn-export-results")
    def export_results(self) -> None:
        try:
            only_relevant = self.query_one("#cb-only-relevant", Checkbox).value
            filepath = self.model.export(only_relevant=only_relevant)
            self._last_export_path = filepath
            self.notify(f"CSV exported successfully to:\n{filepath}", title="Export Complete")
        except Exception as e:
            self.notify(f"Error exporting results: {e}", title="Export Failed", severity="error")

    @on(Button.Pressed, "#btn-open-export")
    def open_export(self) -> None:
        try:
            path_to_open = self._last_export_path
            if not path_to_open:
                from nps_crawling.config import Config
                path_to_open = str(Config.ROOT_DIR / "output")
            self.model.open(path_to_open)
            self.notify(f"Opening export path:\n{path_to_open}", title="Opening File")
        except Exception as e:
            self.notify(f"Error opening export: {e}", title="Open Failed", severity="error")
