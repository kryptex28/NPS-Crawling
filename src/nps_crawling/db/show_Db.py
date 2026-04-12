import os

# Wichtig: PYTHONPATH auf src/ setzen, falls nötig
from nps_crawling.db.db_adapter import DbAdapter


def main() -> None:
    """
    Connects to the database and prints out a summary of the stored NPS filings.
    First, it prints a compressed list of items, then a full detailed view of the latest few.
    """
    try:
        db = DbAdapter()
    except Exception as e:
        print(f"Fehler bei DB Verbindung: {e}")
        return
    try:
        from sqlalchemy import text
        with db.engine.connect() as conn:
            total_count = conn.execute(text(f"SELECT COUNT(*) FROM {db.table_name}")).scalar()
            true_count = conn.execute(text(f"SELECT COUNT(*) FROM {db.table_name} WHERE nps_relevant = TRUE")).scalar()
            false_count = conn.execute(text(f"SELECT COUNT(*) FROM {db.table_name} WHERE nps_relevant = FALSE")).scalar()
            null_count = conn.execute(text(f"SELECT COUNT(*) FROM {db.table_name} WHERE nps_relevant IS NULL")).scalar()
            
        print("=" * 50)
        print(f"Statistiken zur Datenbank-Tabelle '{db.table_name}':")
        print(f"  - Gesamte Filings: {total_count}")
        print(f"  - nps_relevant = True:  {true_count}")
        print(f"  - nps_relevant = False: {false_count}")
        print(f"  - nps_relevant = Null:  {null_count}")
        print("=" * 50 + "\n")
    except Exception as e:
        print(f"Fehler beim Abrufen der Statistiken: {e}")


if __name__ == "__main__":
    main()
