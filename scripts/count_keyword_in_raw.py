import os
import json
import argparse
from pathlib import Path

from collections import Counter

def count_all_keywords_in_files(directory: Path) -> None:
    if not directory.exists():
        print(f"Das Verzeichnis {directory} existiert nicht.")
        return

    print(f"Zähle alle Keywords im Ordner {directory} ...")
    
    total_files = 0
    keyword_total_counter = Counter()
    keyword_alone_counter = Counter()

    for root, _, files in os.walk(directory):
        for file in files:
            if file.endswith('.json'):
                total_files += 1
                filepath = os.path.join(root, file)
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        # Parse die JSON-Datei
                        data = json.load(f)
                        
                        # Die Dateien sind normalerweise Listen von Dicts
                        if not isinstance(data, list):
                            data = [data]
                            
                        file_keywords = set()
                        for entry in data:
                            meta = entry.get("metadata", {})
                            meta_keyword = meta.get("keyword", "")
                            
                            # Fallback, falls keyword unter filing liegt
                            if not meta_keyword:
                                meta_keyword = meta.get("filing", {}).get("keyword", "")
                                
                            if meta_keyword and isinstance(meta_keyword, str):
                                clean_kw = meta_keyword.strip()
                                file_keywords.add(clean_kw)
                                
                        # Nach Durchlauf der Einträge in einer Datei auswerten:
                        for kw in file_keywords:
                            keyword_total_counter[kw] += 1
                            if len(file_keywords) == 1:
                                keyword_alone_counter[kw] += 1
                                    
                except Exception as e:
                    print(f"Fehler beim Lesen/Parsen von {filepath}: {e}")

    print("=" * 50)
    print("Ergebnisse der Keyword-Zählung in den rohen Dateien:")
    print(f"Gescannte JSON-Dateien insgesamt: {total_files}")
    print("-" * 50)
    
    for kw, total_cnt in keyword_total_counter.most_common():
        alone_cnt = keyword_alone_counter[kw]
        print(f"    * '{kw}': {total_cnt}x insgesamt (davon {alone_cnt}x als einziges Keyword in der Datei)")
        
    print("=" * 50)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Zählt alle vorkommenden Keywords in den rohen JSON-Dateien.")
    args = parser.parse_args()
    
    # Automatischer absoluter Pfad zu ../data/json_raw/files vom aktuellen Skript aus
    script_dir = Path(__file__).resolve().parent
    raw_files_dir = script_dir.parent / "data" / "json_raw" / "files"
    
    count_all_keywords_in_files(raw_files_dir)
