import os
import json
import argparse
from pathlib import Path

def count_keyword_in_files(keyword: str, directory: Path) -> None:
    if not directory.exists():
        print(f"Das Verzeichnis {directory} existiert nicht.")
        return

    print(f"Suche nach '{keyword}' im Ordner {directory} ...")
    
    total_occurrences = 0
    files_with_keyword = 0
    total_files = 0

    # Suchbegriff in Kleinbuchstaben für eine case-insensitive Suche
    search_term = keyword.lower()

    for root, _, files in os.walk(directory):
        for file in files:
            if file.endswith('.json'):
                total_files += 1
                filepath = os.path.join(root, file)
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        # Parse die JSON-Datei
                        data = json.load(f)
                        found_in_file = False
                        
                        # Die Dateien sind normalerweise Listen von Dicts
                        if not isinstance(data, list):
                            data = [data]
                            
                        for entry in data:
                            meta = entry.get("metadata", {})
                            meta_keyword = meta.get("keyword", "")
                            
                            # Fallback, falls keyword unter filing liegt
                            if not meta_keyword:
                                meta_keyword = meta.get("filing", {}).get("keyword", "")
                                
                            if meta_keyword and isinstance(meta_keyword, str):
                                if search_term in meta_keyword.lower():
                                    total_occurrences += 1
                                    found_in_file = True
                                    
                        if found_in_file:
                            files_with_keyword += 1
                except Exception as e:
                    print(f"Fehler beim Lesen/Parsen von {filepath}: {e}")

    print("=" * 50)
    print(f"Ergebnisse für das Keyword: '{keyword}'")
    print(f"Gescannte JSON-Dateien: {total_files}")
    print(f"Dateien, die das Keyword enthalten: {files_with_keyword}")
    print(f"Gesamte Vorkommen (Treffer) insgesamt: {total_occurrences}")
    print("=" * 50)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Zählt, wie oft ein Keyword in den rohen JSON-Dateien vorkommt.")
    parser.add_argument("--keyword", type=str, default="net promotor", help="Das Keyword, nach dem gesucht werden soll.")
    
    args = parser.parse_args()
    
    # Automatischer absoluter Pfad zu ../data/json_raw/files vom aktuellen Skript aus
    script_dir = Path(__file__).resolve().parent
    raw_files_dir = script_dir.parent / "data" / "json_raw" / "files"
    
    count_keyword_in_files(args.keyword, raw_files_dir)
