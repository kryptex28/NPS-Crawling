import os

import pandas as pd

from nps_crawling.db.db_adapter import DbAdapter


def export_to_excel(filepath: str = "nps_filings_export.xlsx", only_relevant: bool = True) -> None:
    """
    Exports the entire database table to an Excel (.xlsx) file using pandas.
    If only_relevant is True, only rows where nps_relevant is True are exported.
    Requires 'openpyxl' to write the file.
    """
    try:
        db = DbAdapter()
    except Exception as e:
        print(f"Error connecting to database: {e}")
        return

    print(f"Exporting data from '{db.table_name}' to '{filepath}'...")

    try:
        # Construct query to fetch all data
        if only_relevant:
            query = f"SELECT * FROM {db.table_name} WHERE nps_relevant = True"
        else:
            query = f"SELECT * FROM {db.table_name}"

        # Read the data into a pandas DataFrame using the SQLAlchemy engine
        df = pd.read_sql(query, db.engine)

        # Excel does not support timezone-aware datetimes.
        # Convert any timezone-aware datetime columns to timezone-naive.
        for col in df.select_dtypes(include=['datetimetz']).columns:
            df[col] = df[col].dt.tz_localize(None)

        # Write DataFrame to an Excel file
        # 'index=False' prevents pandas from writing row indices to the excel file
        df.to_excel(filepath, index=False, engine='openpyxl')

        print(f"Successfully exported {len(df)} rows to {os.path.abspath(filepath)}")

    except ImportError as e:
        print(f"\nImportError: {e}")
        print("Es fehlt ein Modul, um Excel-Dateien zu schreiben.")
        print("Bitte installiere 'openpyxl' mit folgendem Befehl:")
        print("pip install openpyxl")
    except Exception as e:
        print(f"\nEin Fehler ist aufgetreten: {e}")


if __name__ == "__main__":
    export_to_excel("nps_filings_export.xlsx")
