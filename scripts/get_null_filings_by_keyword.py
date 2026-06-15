import os
import sys
from collections import defaultdict

# Fügt den 'src'-Ordner automatisch zum Python-Pfad hinzu, egal von wo das Skript gestartet wird
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

from nps_crawling.db.db_adapter import DbAdapter
from sqlalchemy import text

def main() -> None:
    """
    Connects to the database and retrieves up to 5 filings with project_relevant=NULL 
    per keyword, printing their path_to_raw.
    """
    try:
        db = DbAdapter()
    except Exception as e:
        print(f"Fehler bei DB Verbindung: {e}")
        return
        
    keyword_filings = defaultdict(list)
    
    try:
        with db.engine.connect() as conn:
            # Hole alle Filings, wo project_relevant NULL ist und keywords existieren
            stmt = text(f"SELECT path_to_raw, keywords FROM {db.table_name} WHERE project_relevant IS NULL AND keywords IS NOT NULL")
            rows = conn.execute(stmt).fetchall()
            
            for row in rows:
                path_to_raw = row[0]
                keywords = row[1]
                
                if not keywords:
                    continue
                    
                # Gehe durch alle Keywords dieses Filings
                for kw in keywords:
                    clean_kw = kw.strip()
                    # Füge den Pfad hinzu, falls wir noch keine 5 für dieses Keyword haben
                    if len(keyword_filings[clean_kw]) < 5:
                        keyword_filings[clean_kw].append(path_to_raw)
                        
        # Ausgabe der Ergebnisse
        print("=" * 60)
        print("Filings mit project_relevant = NULL (Maximal 5 pro Keyword)")
        print("=" * 60)
        
        if not keyword_filings:
            print("Keine entsprechenden Filings gefunden.")
            
        for kw, paths in sorted(keyword_filings.items()):
            print(f"\nKeyword: '{kw}'")
            print("-" * 40)
            for p in paths:
                print(f"  - {p}")
            
    except Exception as e:
        print(f"Fehler beim Abrufen der Daten: {e}")

if __name__ == "__main__":
    main()
