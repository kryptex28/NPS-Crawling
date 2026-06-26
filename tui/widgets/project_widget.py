

from textual import on
from textual.app import ComposeResult
from textual.containers import Horizontal, ScrollableContainer, Vertical
from textual.widgets import (
    Input, 
    Select, 
    Static, 
    Button, 
    DataTable
)
from models.project_model import ProjectModel
from data_package.project_data import ProjectData

class ProjectWidget(Static):
    def __init__(self) -> None:
        super().__init__()

        self.model = ProjectModel() 

    def compose(self) -> ComposeResult:
        with ScrollableContainer():
            yield Static("Project Name", id="project-name-label")
            yield Input(placeholder="Enter project name", id="project-name-input")
            yield Static("Project Description", id="project-desc-label")
            yield Input(placeholder="Enter project description", id="project-desc-input")

            with Horizontal():
                yield Button("Save Project", id="save-project-btn", variant="success")
                yield Button("Load Project", id="load-project-btn", variant="primary")
                yield Button("Clear Form", id="clear-form-btn", variant="warning")
                yield Button("Show Projects", id="show-projects-btn")


    @on(Button.Pressed, "#save-project-btn")
    def save_project(self):
        project_name: str = self.query_one("#project-name-input", Input).value.strip()
        project_description: str = self.query_one("#project-desc-input", Input).value.strip()

        self.model.save_project(project_data=ProjectData(name=project_name,
                                                         description=project_description,
                                                         id=1))