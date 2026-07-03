
from textual.app import ComposeResult
from textual.containers import Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Static
from textual import on

from textual.widgets import DataTable, Static

from models.project_model import ProjectModel
from data_package.project_data import ProjectData

class ProjectScreen(ModalScreen):
    CSS_PATH = "project_screen.tcss"


    def __init__(self) -> None:
        super().__init__()
        self.model = ProjectModel()
        
    def compose(self) -> ComposeResult:
        with Vertical():
            yield Static("Project View", id="project-title")
            yield Static("Recent Projects", id="project-recent")
            yield DataTable(id="project-table", zebra_stripes=True, show_header=True, show_cursor=True)
            yield Button("Open Project", id="open-project-btn")
            yield Button("Delete Project", id="delete-project-btn")
            yield Button("Refresh", id="refresh-project-btn")
            yield Button("Close", id="close-project-btn")

    def on_mount(self) -> None:
        self._refresh_table()

    def _refresh_table(self) -> None:
        table = self.query_one("#project-table", DataTable)
        table.clear(columns=True)
        table.add_columns("Project Name", "Project Description")
        for data in self.model.get_projects():
            table.add_row(data.name, data.description)

    @on(Button.Pressed, "#open-project-btn")
    def open_project(self) -> None:
        table = self.query_one("#project-table", DataTable)
        if table.cursor_row is None:
            self.app.notify("Select a project first.", severity="warning")
            return
        row = table.get_row_at(table.cursor_row)
        self.model.load_project(
            ProjectData(name=str(row[0]), description=str(row[1]), id=1),
        )
        self.app.notify(f"Loaded project '{row[0]}'.", severity="information")
        self.dismiss(True)

    @on(Button.Pressed, "#refresh-project-btn")
    def refresh_projects(self) -> None:
        self._refresh_table()

    @on(Button.Pressed, "#close-project-btn")
    def close_project_view(self):
        self.dismiss(True)
