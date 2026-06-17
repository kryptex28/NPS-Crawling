from enum import Enum
from pathlib import Path


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