
from textual.app import ComposeResult
from textual.containers import Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Static

from textual.widgets import DataTable, Static


class ProjectScreen(ModalScreen):
    def __init__(self) -> None:
        super().__init__()

    def compose(self) -> ComposeResult:
        with Vertical():
            yield Static("Project View", id="project-title")
            yield Static("Recent Projects", id="project-recent")
            yield DataTable(id="project-table", zebra_stripes=True, show_header=False, show_cursor=True)
            yield Button("Open Project", id="open-project-btn")
            yield Button("Delete Project", id="delete-project-btn")
            yield Button("Refresh", id="refresh-project-btn")
