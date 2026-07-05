from textual.app import ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Static
from textual import on
from data_package.query_data import QueryData

class QueryConfigScreen(ModalScreen):
    CSS_PATH = "query_config_screen.tcss"

    def __init__(self, query: QueryData) -> None:
        """Initialize the QueryConfigScreen."""
        super().__init__()
        self.query_data = query

    def compose(self) -> ComposeResult:
        """Compose the query configuration display layout."""
        with Container():
            yield Static("Query Configuration Details", classes="modal-title")
            
            with Vertical(id="config-details-container"):
                yield Static(f"[bold]ID:[/bold] {self.query_data.id}")
                yield Static(f"[bold]Query Base URL:[/bold] {self.query_data.query_base or 'default'}")
                yield Static(f"[bold]Keyword / Phrase:[/bold] {self.query_data.keyword or 'None'}")
                yield Static(f"[bold]Company / Entity Title:[/bold] {self.query_data.entity_title or 'None'}")
                yield Static(f"[bold]Ticker:[/bold] {self.query_data.entity or 'None'}")
                yield Static(f"[bold]CIK:[/bold] {self.query_data.cik or 'None'}")
                yield Static(f"[bold]Filing Category:[/bold] {self.query_data.filing_category or 'None'}")
                yield Static(f"[bold]Filing Types:[/bold] {', '.join(self.query_data.filing_types) if self.query_data.filing_types else 'None'}")
                yield Static(f"[bold]Date Range:[/bold] {self.query_data.date_range or 'None'}")
                yield Static(f"[bold]Filed From:[/bold] {self.query_data.from_date or 'None'}")
                yield Static(f"[bold]Filed To:[/bold] {self.query_data.to_date or 'None'}")
                yield Static(f"[bold]Filing Limit:[/bold] {self.query_data.limit if self.query_data.limit is not None else '-1'}")

            with Horizontal(classes="modal-footer"):
                yield Button("Close", variant="primary", id="close-config-btn")

    @on(Button.Pressed, "#close-config-btn")
    def close(self) -> None:
        """Close the query config details screen."""
        self.dismiss()
