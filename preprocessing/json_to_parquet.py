import json
from json import JSONDecoder, JSONDecodeError
from pathlib import Path
import ast

import pandas as pd


def _parse_json_stream(text: str) -> list:
    """
    Parse a stream of one or multiple JSON values from a string.

    Reads consecutive JSON objects from the beginning of the string.
    If no valid JSON value can be parsed, an empty list is returned.
    """
    decoder = JSONDecoder()
    idx = 0
    length = len(text)
    records = []

    while idx < length:
        # Skip whitespace between JSON values
        while idx < length and text[idx].isspace():
            idx += 1
        if idx >= length:
            break

        try:
            obj, end = decoder.raw_decode(text, idx)
        except JSONDecodeError:
            # Stop parsing at the first invalid chunk
            break

        records.append(obj)
        idx = end

    return records


def _parse_linewise(text: str) -> list:
    """
    Try to parse each non-empty line either as JSON or as a Python literal.
    Collect all successfully parsed objects.
    """
    records = []

    for line_no, line in enumerate(text.splitlines(), start=1):
        line = line.strip()
        if not line:
            continue

        # First try: JSON per line
        try:
            obj = json.loads(line)
            records.append(obj)
            continue
        except JSONDecodeError:
            pass

        # Second try: Python literal per line (e.g. "{'a': 1, 'b': 2}")
        try:
            obj = ast.literal_eval(line)
            if isinstance(obj, (dict, list, tuple)):
                records.append(obj)
                continue
        except (SyntaxError, ValueError):
            # ignore this line
            continue

    return records


def _normalize_records(records: list, source_name: str) -> pd.DataFrame:
    """
    Normalize the list of records into a flat DataFrame.
    """
    if not records:
        raise ValueError("No parsable records found in file.")

    # If the stream returned a single list, treat it as the record list
    if len(records) == 1 and isinstance(records[0], list):
        records = records[0]

    df = pd.json_normalize(records)
    df["__source_file"] = source_name
    return df


def load_json_to_df(path: Path) -> pd.DataFrame:
    """
    Load a file that contains JSON-like data and return a pandas DataFrame.

    Supported formats:
    1) A single JSON document:
       - A list of objects: [ {...}, {...}, ... ]
       - A dict that contains a list as one of its values.

    2) A stream of JSON values (concatenated objects).

    3) JSON Lines: one JSON object per line.

    4) Python literals (written via str(obj)), either:
       - Entire file is one big literal (list/dict)
       - One literal per line.
    """
    text = path.read_text(encoding="utf-8").strip()

    # 1) Try: single JSON document
    try:
        data = json.loads(text)
        if isinstance(data, list):
            records = data
            return _normalize_records(records, path.name)
        elif isinstance(data, dict):
            # Try to find the first list value and treat it as the record list
            list_values = [v for v in data.values() if isinstance(v, list)]
            if list_values:
                records = list_values[0]
                return _normalize_records(records, path.name)
            # if dict without list, treat the dict itself as one record
            records = [data]
            return _normalize_records(records, path.name)
    except JSONDecodeError:
        pass

    # 2) Try: JSON stream
    records = _parse_json_stream(text)
    if records:
        return _normalize_records(records, path.name)

    # 3) Try: Python literal for the whole file
    try:
        obj = ast.literal_eval(text)
        if isinstance(obj, (list, dict, tuple)):
            if isinstance(obj, dict):
                records = [obj]
            else:
                records = list(obj)
            return _normalize_records(records, path.name)
    except (SyntaxError, ValueError):
        pass

    # 4) Try: line-wise parsing (JSON or Python literal per line)
    records = _parse_linewise(text)
    if records:
        return _normalize_records(records, path.name)

    # If we reach this, nothing worked
    raise ValueError(f"Could not parse file '{path}' as JSON-like data.")


def json_input_to_parquet(input_path: Path, output_file: Path) -> None:
    """
    Convert one or multiple JSON-like files to a single Parquet file.

    If input_path is:
    - a file: convert this single file
    - a directory: read all *.json files in that directory
    """
    if input_path.is_file():
        json_files = [input_path]
    elif input_path.is_dir():
        json_files = sorted(input_path.glob("*.json"))
    else:
        raise FileNotFoundError(f"Input path does not exist: {input_path}")

    if not json_files:
        raise FileNotFoundError(f"No JSON files found at: {input_path}")

    dfs = []

    for json_file in json_files:
        print(f"Loading {json_file}")
        df = load_json_to_df(json_file)
        dfs.append(df)

    full_df = pd.concat(dfs, ignore_index=True)

    output_file.parent.mkdir(parents=True, exist_ok=True)

    print(f"Writing Parquet to {output_file}")
    full_df.to_parquet(output_file, index=False)
