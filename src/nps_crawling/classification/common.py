from enum import Enum
import json
from pathlib import Path
import re
from typing import Callable, TypeVar


def classification_config_basename(name: str, *, max_length: int = 200) -> str:
    """Turn a category or model label into a single path segment / filename stem (no extension).

    Removes characters that are invalid or awkward on common filesystems.
    """
    s = str(name).replace("\\", "_").replace("/", "_")
    for ch in ':*?"<>|':
        s = s.replace(ch, "_")
    s = re.sub(r"\s+", " ", s).strip()
    if not s:
        s = "unnamed"
    return s[:max_length]


def stable_serialize(obj):
    if isinstance(obj, dict):
        return {k: stable_serialize(v) for k, v in sorted(obj.items())}
    if isinstance(obj, (list, tuple)):
        return [stable_serialize(v) for v in obj]
    if isinstance(obj, set):
        return sorted(stable_serialize(v) for v in obj)
    if isinstance(obj, Enum):
        return obj.value
    if isinstance(obj, Path):
        return str(obj)
    if hasattr(obj, "to_dict") and callable(obj.to_dict):
        return stable_serialize(obj.to_dict())
    if hasattr(obj, "__dict__"):
        return stable_serialize({k: v for k, v in vars(obj).items() if not k.startswith("_")})
    return obj


T = TypeVar("T")


def load_json_file(path: str | Path) -> dict:
    """Load a JSON object from ``path``."""
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def config_path_ref(path: str | Path, *, base: Path | None = None) -> str:
    """Serialize a config path as a repo-relative string (forward slashes)."""
    resolved = Path(path).resolve()
    if base is None:
        from nps_crawling.config import Config

        base = Config.ROOT_DIR
    try:
        ref = resolved.relative_to(base.resolve())
    except ValueError:
        ref = resolved
    return ref.as_posix()


def resolve_config_path(ref: str | Path) -> Path:
    """Resolve a config path reference to an existing file."""
    path = Path(ref)
    if path.is_file():
        return path.resolve()

    from nps_crawling.config import Config

    for candidate in (
        Config.ROOT_DIR / path,
        Config.CLASSIFICATION_CONFIG_DIR / path,
        path,
    ):
        if candidate.is_file():
            return candidate.resolve()

    raise FileNotFoundError(f"Config JSON not found: {ref}")


def resolve_config_entry(
    value: str | Path | dict | T,
    *,
    from_dict: Callable[[dict], T],
    from_json: Callable[[str | Path], T],
) -> T:
    """Load a config entry from an object, inline dict, or JSON path reference."""
    if isinstance(value, (str, Path)):
        return from_json(value)
    if isinstance(value, dict):
        return from_dict(value)
    return value


def make_hashable(obj):
    """Convert unhashable types to hashable equivalents."""
    if isinstance(obj, dict):
        return tuple(sorted((k, make_hashable(v)) for k, v in obj.items()))
    elif isinstance(obj, list):
        return tuple(make_hashable(item) for item in obj)
    elif isinstance(obj, set):
        return frozenset(make_hashable(item) for item in obj)
    elif hasattr(obj, "to_dict") and callable(obj.to_dict):
        return make_hashable(obj.to_dict())
    elif hasattr(obj, "__dict__"):
        return make_hashable({k: v for k, v in vars(obj).items() if not k.startswith("_")})
    else:
        return obj
