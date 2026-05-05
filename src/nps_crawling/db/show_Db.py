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
            
            # Get all keywords to process in python for clean aggregation
            all_keywords_rows = conn.execute(text(f"SELECT keywords FROM {db.table_name}")).fetchall()

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

        print("=" * 50)
        print(f"Statistiken zur Datenbank-Tabelle '{db.table_name}':")
        print(f"  - Gesamte Filings: {total_count}")
        print(f"  - nps_relevant = True:  {true_count}")
        print(f"  - nps_relevant = False: {false_count}")
        print(f"  - nps_relevant = Null:  {null_count}")
        print("-" * 50)
        print(f"  - Verschiedene Keywords (Gesamt): {len(keyword_counter)}")
        
        print("\nFilings pro Keyword:")
        for kw, cnt in keyword_counter.most_common():
            print(f"    * '{kw}': {cnt}")
            
        print("\nFilings pro Keyword-Kombination:")
        for combo, cnt in combination_counter.most_common():
            print(f"    * {combo}: {cnt}")
            
        print("=" * 50 + "\n")
    except Exception as e:
        print(f"Fehler beim Abrufen der Statistiken: {e}")


if __name__ == "__main__":
    main()
