import csv
import os

from sqlalchemy import text

from nps_crawling.db.db_adapter import DbAdapter


def export_to_csv(filepath: str = "nps_filings_export.csv", only_relevant: bool = True) -> None:
    """
    Exports the entire database table to a CSV file.
    If only_relevant is True, only rows where nps_relevant is True are exported.
    """
    try:
        db = DbAdapter()
    except Exception as e:
        print(f"Error connecting to database: {e}")
        return

    print(f"Exporting data from '{db.table_name}' to '{filepath}'...")

    # Select all records from the table
    if only_relevant:
        stmt = text(f"SELECT * FROM {db.table_name} WHERE nps_relevant = True")
    else:
        stmt = text(f"SELECT * FROM {db.table_name}")

    try:
        with db.engine.connect() as conn:
            result = conn.execute(stmt)

            # Extract column names
            columns = result.keys()

            # Open the CSV file and write the data
            with open(filepath, mode="w", newline="", encoding="utf-8") as file:
                writer = csv.writer(file)

                # Write the header row
                writer.writerow(columns)

                # Fetch all rows and write them
                rows = result.fetchall()
                writer.writerows(rows)

        print(f"Successfully exported {len(rows)} rows to {os.path.abspath(filepath)}")
    except Exception as e:
        print(f"An error occurred during export: {e}")


if __name__ == "__main__":
    export_to_csv("nps_filings_export.csv")
