

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
