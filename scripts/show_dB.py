import os
import sys

# Fügt den 'src'-Ordner automatisch zum Python-Pfad hinzu, egal von wo das Skript gestartet wird
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

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
            true_count = conn.execute(text(f"SELECT COUNT(*) FROM {db.table_name} WHERE project_relevant = TRUE")).scalar()
            false_count = conn.execute(text(f"SELECT COUNT(*) FROM {db.table_name} WHERE project_relevant = FALSE")).scalar()
            null_count = conn.execute(text(f"SELECT COUNT(*) FROM {db.table_name} WHERE project_relevant IS NULL")).scalar()
            
            # Get all keywords to process in python for clean aggregation
            all_keywords_rows = conn.execute(text(f"SELECT keywords FROM {db.table_name}")).fetchall()
            null_keywords_rows = conn.execute(text(f"SELECT keywords FROM {db.table_name} WHERE project_relevant IS NULL")).fetchall()

        from collections import Counter
        keyword_counter = Counter()
        combination_counter = Counter()

        for row in all_keywords_rows:
            kws = row[0]
            if not kws:
                combination_counter["[Keine Keywords]"] += 1
                continue
                
            # Clean keywords (keep original quotes, just strip spaces)
            clean_kws = []
            for k in kws:
                clean_k = k.strip()
                clean_kws.append(clean_k)
                keyword_counter[clean_k] += 1
                
            # Sort the array so ['A', 'B'] is the same combination as ['B', 'A']
            clean_kws.sort()
            kws_str = "[" + ", ".join([f"'{k}'" for k in clean_kws]) + "]"
            combination_counter[kws_str] += 1

        null_combination_counter = Counter()
        for row in null_keywords_rows:
            kws = row[0]
            if not kws:
                null_combination_counter["[Keine Keywords]"] += 1
                continue
                
            clean_kws = [k.strip() for k in kws]
            clean_kws.sort()
            kws_str = "[" + ", ".join([f"'{k}'" for k in clean_kws]) + "]"
            null_combination_counter[kws_str] += 1

        print("=" * 50)
        print(f"Statistiken zur Datenbank-Tabelle '{db.table_name}':")
        print(f"  - Gesamte Filings: {total_count}")
        print(f"  - project_relevant = True:  {true_count}")
        print(f"  - project_relevant = False: {false_count}")
        print(f"  - project_relevant = Null:  {null_count}")
        print("-" * 50)
        print(f"  - Verschiedene Keywords (Gesamt): {len(keyword_counter)}")
        
        print("\nFilings pro Keyword:")
        for kw, cnt in keyword_counter.most_common():
            print(f"    * '{kw}': {cnt}")
            
        print("\nFilings pro Keyword-Kombination (Gesamt):")
        for combo, cnt in combination_counter.most_common():
            print(f"    * {combo}: {cnt}")
            
        if null_count > 0:
            print("\nFilings mit project_relevant = NULL pro Keyword-Kombination:")
            for combo, cnt in null_combination_counter.most_common():
                print(f"    * {combo}: {cnt}")
            
        print("=" * 50 + "\n")
    except Exception as e:
        print(f"Fehler beim Abrufen der Statistiken: {e}")


if __name__ == "__main__":
    main()
