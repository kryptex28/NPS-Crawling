
from textual.app import ComposeResult
from textual.containers import Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Static
from textual import on

from textual.widgets import DataTable, Static

from models.project_model import ProjectModel
from data_package.project_data import ProjectData

class ProjectScreen(ModalScreen):
    DEFAULT_CSS = """
    ProjectScreen {
        align: center middle;
    }

    ProjectScreen > Vertical {
        width: 75%;
        max-height: 90%;
        background: $surface;
        border: thick $primary;
        padding: 0 1;
    }

    ProjectScreen #project-title {
        background: $primary;
        color: $text;
        text-align: center;
        padding: 0 1;
        height: 3;
        content-align: center middle;
    }

    ProjectScreen #project-recent {
        color: $accent;
        text-style: bold;
        margin-top: 1;
        margin-bottom: 1;
    }

    ProjectScreen #project-table {
        height: 1fr;
        margin-bottom: 1;
    }

    ProjectScreen Button {
        margin-top: 1;
        width: 100%;
    }

    ProjectScreen #open-project-btn {
        background: $primary;
        color: $text;
    }

    ProjectScreen #delete-project-btn {
        background: $error;
        color: $text;
    }

    ProjectScreen #refresh-project-btn {
        background: $surface-lighten-1;
    }
    """


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
