import os

# Wichtig: PYTHONPATH auf src/ setzen, falls nötig
from nps_crawling.db.db_adapter import DbAdapter


def main():
    try:
        db = DbAdapter()
    except Exception as e:
        print(f"Fehler bei DB Verbindung: {e}")
        return
    # Hol die letzten 50 Einträge
    filings1 = db.get_all_filings(limit=220)

    print(f"Gefundene Einträge: {len(filings1)}\n")
    for f in filings1:
        print(f"--- ID: {f['id']} ---")
        print(f"Form: {f['form']} | Datum: {f['file_date']}")
        print(f"Rohdaten-Pfad: {f['path_to_raw']}")
        print(f"Keyword Array: {f['keywords']}")
        print("-" * 40)
    print(f"Gefundene Einträge für diese Ansicht: {len(filings1)}\n")

    # Hol die letzten 5 Einträge
    filings = db.get_all_filings(limit=5)

    for f in filings:
        print(f"\n==================================================")
        print(f"       ALLE DATEN FÜR ID: {f.get('id')}")
        print(f"==================================================")

        # Gehe durch alle Spalten des Dictionaries und zeige *alles* an
        for col_name, col_value in f.items():
            print(f"{col_name:<30}: {col_value}")

    print(f"\nFertig. Das waren die Daten für {len(filings)} Einträge.")


if __name__ == "__main__":
    main()
