
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
        table = self.query_one("#project-table", DataTable)

        table.add_columns("Project Name", "Project Description")

        project_data: list[ProjectData] = self.model.get_projects()

        for data in project_data:
            table.add_row(data.name, 
                          data.description)

    @on(Button.Pressed, "#close-project-btn")
    def close_project_view(self):
        self.dismiss(True)
