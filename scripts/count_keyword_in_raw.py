import os
import argparse
from pathlib import Path

from nps_crawling.config import Config

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
                        # Den gesamten Text der Datei als Kleinbuchstaben einlesen
                        content = f.read().lower()
                        count = content.count(search_term)
                        if count > 0:
                            total_occurrences += count
                            files_with_keyword += 1
                except Exception as e:
                    print(f"Fehler beim Lesen von {filepath}: {e}")

    print("=" * 50)
    print(f"Ergebnisse für das Keyword: '{keyword}'")
    print(f"Gescannte JSON-Dateien: {total_files}")
    print(f"Dateien, die das Keyword enthalten: {files_with_keyword}")
    print(f"Gesamte Vorkommen (Treffer) insgesamt: {total_occurrences}")
    print("=" * 50)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Zählt, wie oft ein Keyword in den rohen JSON-Dateien vorkommt.")
    parser.add_argument("--keyword", type=str, default="net promoter", help="Das Keyword, nach dem gesucht werden soll.")
    
    args = parser.parse_args()
    
    raw_files_dir = Config.RAW_JSON_PATH_CRAWLER / "files"
    count_keyword_in_files(args.keyword, raw_files_dir)
