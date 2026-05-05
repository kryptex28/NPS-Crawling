import csv
import os

from sqlalchemy import text

from nps_crawling.db.db_adapter import DbAdapter


def export_to_csv(filepath: str = "nps_filings_export.csv", all: bool = True, keyword: str = "net promotor") -> None:
    """
    Exports the database table to a CSV file.
    If all is True, all rows where nps_relevant is True are exported.
    If all is False, only rows containing the specified keyword are exported.
    """
    try:
        db = DbAdapter()
    except Exception as e:
        print(f"Error connecting to database: {e}")
        return

    print(f"Exporting data from '{db.table_name}' to '{filepath}'...")

    if all:
        stmt = text(f"SELECT * FROM {db.table_name} WHERE nps_relevant = True")
        params = {}
    else:
        stmt = text(f"SELECT * FROM {db.table_name} WHERE :keyword = ANY(keywords)")
        params = {"keyword": keyword}

    try:
        with db.engine.connect() as conn:
            result = conn.execute(stmt, params)

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
    # all=True exportiert alle nps_relevant=True
    # all=False exportiert nur Filings mit dem spezifizierten Keyword in der keywords Spalte
    export_to_csv("nps_filings_export.csv", all=True, keyword="net promotor")
