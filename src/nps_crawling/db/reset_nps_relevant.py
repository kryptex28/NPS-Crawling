"""Script to reset the nps_relevant flag for all filings in the database."""

import os
import sys
from sqlalchemy import text

# Fügt den 'src'-Ordner automatisch zum Python-Pfad hinzu, damit Importe funktionieren
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from nps_crawling.db.db_adapter import DbAdapter

def main() -> None:
    print("Verbinde mit der Datenbank...")
    try:
        db = DbAdapter()
    except Exception as e:
        print(f"Fehler bei der Datenbankverbindung: {e}")
        return

    print("Setze nps_relevant für alle Filings auf NULL...")
    try:
        with db.engine.begin() as conn:
            # Setze nps_relevant in der Haupttabelle auf NULL
            stmt_main = text(f"UPDATE {db.table_name} SET nps_relevant = NULL;")
            res_main = conn.execute(stmt_main)
            print(f"  -> Haupttabelle ({db.table_name}): {res_main.rowcount} Zeilen auf nps_relevant = NULL gesetzt.")
            
            # Da nps_relevant auch in der Preprocessing-Versionierungstabelle gespeichert wird, 
            # setzen wir es dort vorsichtshalber ebenfalls zurück.
            stmt_prep = text(f"UPDATE {db.table_name}_preprocessing SET nps_relevant = NULL;")
            res_prep = conn.execute(stmt_prep)
            print(f"  -> Preprocessing-Tabelle ({db.table_name}_preprocessing): {res_prep.rowcount} Zeilen auf nps_relevant = NULL gesetzt.")
            
        print("Fertig!")
            
    except Exception as e:
        print(f"Ein Fehler ist beim Ausführen der Updates aufgetreten: {e}")

if __name__ == "__main__":
    main()
