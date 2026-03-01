import os
from sqlalchemy import create_engine, text
from nps_filings import NpsFilingsDB

def main():
    engine = create_engine(f"postgresql+psycopg2://{os.environ['POSTGRES_ENGINE']}")

    db = NpsFilingsDB(engine)

    test_id = "test-filing-1"

    # optional: sauberer Start (löscht nur den einen Testdatensatz)
    with engine.begin() as conn:
        conn.execute(text("DELETE FROM nps_filings WHERE id = :id"), {"id": test_id})

    # 1) UPSERT: neuen Datensatz anlegen
    db.upsert_filing(
        id=test_id,
        ciks=["0000320193"],
        form="10-K",
        keywords=["risk"],
        meta={"source": "unit-test"},
    )

    # 2) Keyword hinzufügen (nur wenn nicht vorhanden)
    added1 = db.add_keyword(test_id, "nps")
    added2 = db.add_keyword(test_id, "nps")  # sollte False sein

    # 3) update einzelner Felder
    db.update_fields(test_id, path_cleaned="/tmp/cleaned.json", has_nps=True)

    # 4) checks
    print("has_nps:", db.has_nps(test_id))                 # True
    print("cleaned_exists:", db.cleaned_exists(test_id))   # True
    print("blacklisted:", db.is_blacklisted(test_id))      # False
    print("added1:", added1)                               # True
    print("added2:", added2)                               # False

    # 5) direkt nachschauen, was in der DB steht
    with engine.connect() as conn:
        row = conn.execute(
            text("""
            SELECT id, ciks, form, keywords, has_nps, path_cleaned, meta
            FROM nps_filings
            WHERE id = :id
            """),
            {"id": test_id},
        ).mappings().one()
        print("row:", dict(row))

    # 6) cleanup (optional)
    # db.delete_filing(test_id)

if __name__ == "__main__":
    main()