import subprocess
import sys

from nps_crawling.db.db_adapter import DbAdapter

class ResultModel():

    def __init__(self) -> None:
        """Initialize the ResultModel instance."""
        pass

    def open(self, path: str = ""):
        """Open the export output file with the default system application."""
        if not path:
            return

        if sys.platform == "win32":
            subprocess.Popen(["start", path], shell=True)
        elif sys.platform == "darwin":
            subprocess.Popen(["open", path])
        else:
            subprocess.Popen(["xdg-open", path])

    def export(self, only_relevant: bool = False) -> str:
        """Export database results to an Excel or CSV file."""
        db_adapter = DbAdapter()
        return db_adapter.export_csv(only_relevant=only_relevant)