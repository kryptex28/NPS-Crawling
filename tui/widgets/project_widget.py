

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
            
            yield Static("Categories", id="project-categories-label")
            yield Input(placeholder="Enter category", id="project-categories-input")
            yield Select(
                        [("Boolean", "boolean"), ("Float", "float")],
                        id="project-categories-type",
                        value="boolean",
                    )  
            with Horizontal():
                yield Button("Add Category", id="add-category-btn")
                yield Button("Remove Category", id="remove-category-btn")
                yield Button("Refresh Categories", id="refresh-categories-btn")
            yield DataTable(id="project-categories-table", zebra_stripes=True, show_header=True, show_cursor=True)

            with Horizontal():
                yield Button("Save Project", id="save-project-btn", variant="success")
                yield Button("Load Project", id="load-project-btn", variant="primary")
                yield Button("Clear Form", id="clear-form-btn", variant="warning")

    def on_mount(self) -> None:
        table: DataTable = self.query_one("#project-categories-table", DataTable)
        table.add_columns("Category", "Type")

    @on(Button.Pressed, "#add-category-btn")
    def on_add_category(self) -> None:
        category_name: Input = self.query_one("#project-categories-input", Input)
        category_type: Select = self.query_one("#project-categories-type", Select)

        if category_name.value:
            category_type_value = category_type.value if isinstance(category_type.value, str) else "boolean"
            self.model.add_category(category_name.value, category_type_value)
            category_name.value = ""
            self._refresh_categories_table()

    @on(Button.Pressed, "#remove-category-btn")
    def on_remove_category(self) -> None:
        category_name: Input = self.query_one("#project-categories-input", Input)

        if category_name.value:
            self.model.remove_category(category_name.value)
            category_name.value = ""
            self._refresh_categories_table()

    @on(Button.Pressed, "#refresh-categories-btn")
    def on_refresh_categories(self) -> None:
        self._refresh_categories_table()

    @on(Button.Pressed, "#clear-form-btn")
    def on_clear_form(self) -> None:
        self.model.clear_categories()
        self._refresh_categories_table()

    def _refresh_categories_table(self):
        table: DataTable = self.query_one("#project-categories-table", DataTable)
        table.clear()

        for category in self.model.get_categories():
            table.add_row(category["name"], category["type"])