from pathlib import Path

import pandas as pd


def main() -> None:
    """
    Inspect the structure of the Parquet file.
    """
    base_dir = Path(__file__).resolve().parent
    path = base_dir / "test_data" / "nps_filings.parquet"

    df = pd.read_parquet(path)

    print("Shape:", df.shape)
    print("\nDtypes:")
    print(df.dtypes)

    print("\nColumns:")
    for col in df.columns:
        print(f"- {col}")

    print("\nFirst 5 rows:")
    print(df.head(5))


if __name__ == "__main__":
    main()
