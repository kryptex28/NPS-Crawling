"""Runner script to convert JSON to Parquet for NPS filings."""

from pathlib import Path

from nps_crawling.preprocessing.json_to_parquet import json_input_to_parquet


def main() -> None:
    """Simple runner script to convert the current JSON file to Parquet.

    Paths are resolved relative to this file's directory.
    """
    base_dir = Path(__file__).resolve().parent

    # Input JSON file (adjust if needed)
    input_path = base_dir / "test_data" / "nps_filings.json"

    # Output Parquet file
    output_file = base_dir / "test_data" / "nps_filings.parquet"

    print("Starting JSON to Parquet conversion...")
    print(f"Base dir: {base_dir}")
    print(f"Input   : {input_path}")
    print(f"Output  : {output_file}")

    json_input_to_parquet(input_path, output_file)

    print("Conversion finished.")


if __name__ == "__main__":
    main()
