from __future__ import annotations


from textual import on
from textual.app import ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.widgets import (
    Button,
    DataTable,
    Static,
)


from models.database_model import DatabaseModel

class DatabaseWidget(Container):

    def __init__(self):
        """Initialize the DatabaseWidget."""
        super().__init__()
        self.model = DatabaseModel()

    def compose(self) -> ComposeResult:
        """Compose the database viewer layout with a data table."""
        with Horizontal():
            with Vertical():
                yield Static("Database", classes="panel-title")
                with Horizontal():
                    yield Button("Show Database", id="btn-show-database")
                    yield Button("Clear Database", id="btn-clear-database")
                yield DataTable(id="db-table")

    @on(Button.Pressed, "#btn-show-database")
    async def load(self) -> None:
        """Fetch filings from the database and populate the data table."""
        table = self.query_one("#db-table", DataTable)

        # create a Thread to fetch all database entries to avoid TUI freeze
        worker = self.run_worker(
            lambda: self.model.get_all_filings(),
            thread=True,
        )

        rows = await worker.wait()
        table.clear()
        if not rows:
            return
        
        columns = list(rows[0].keys())

        table.add_columns(*columns)

        for row in rows:
            table.add_row(*(str(row.get(col, "")) for col in columns))

    @on(Button.Pressed, "#btn-clear-database")
    def on_database_clear(self):
        """Clear all rows in the database data table."""
        database = self.query_one("#db-table", DataTable)
        database.clear()