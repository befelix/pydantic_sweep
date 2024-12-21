import itertools
import re
from collections.abc import Iterable, Iterator
from typing import Any, TypeVar

from pydantic_sweep.types import Config, Path, StrictPath

__all__ = [
    "dict_to_pathvalues",
    "merge_configs",
    "nested_dict_from_items",
    "normalize_path",
]


T = TypeVar("T")

valid_key_pattern = r"[A-Za-z_][A-Za-z0-9_]*"
# Valid python keys starts with letters and can contain numbers and underscores after
_STR_PATH_PATTERN = re.compile(rf"^{valid_key_pattern}(\.{valid_key_pattern})*$")
_STR_KEY_PATTERN = re.compile(rf"^{valid_key_pattern}$")
# Explanation:
# ^ - Matches the start of the string.
# We first match a valid key, followed by dot-seperated valid keys
# $ - Matches the end of the string.


def _path_to_str(p: Path, /) -> str:
    return p if isinstance(p, str) else ".".join(p)


def normalize_path(path: Path, /, *, check_keys: bool = False) -> StrictPath:
    """Normalize a path to a tuple of strings.

    Parameters
    ----------
    path :
        The path to be normalized.
    check_keys :
        If ``True``, also check each individual key in a tuple path.
    """
    if isinstance(path, str):
        if not re.fullmatch(_STR_PATH_PATTERN, path):
            raise ValueError(
                "If provided as a string, the path must consist only of "
                f"dot-separated keys. For example, 'my.key'. Got {path})"
            )
        return tuple(path.split("."))
    else:
        if check_keys:
            for p in path:
                if not re.fullmatch(_STR_KEY_PATTERN, p):
                    raise ValueError(
                        f"Paths can only contain letters and underscores, got {p}."
                    )
        return tuple(path)


def nested_dict_at(path: Path, value) -> dict[str, Any]:
    """Return nested dictionary with the value at path."""
    return nested_dict_from_items([(path, value)])


def nested_dict_from_items(items: Iterable[tuple[Path, Any]], /) -> dict[str, Any]:
    """Convert paths and values (items) to a nested dictionary.

    Paths are assumed as single dot-separated strings.
    """
    result: dict[str, Any] = dict()

    for full_path, value in items:
        *path, key = normalize_path(full_path)
        node = result

        for part in path:
            if part not in node:
                node[part] = dict()

            node = node[part]

            if not isinstance(node, dict):
                raise ValueError(
                    f"In the configs, for '{_path_to_str(path)}' there are both a "
                    f"value ({node}) and child nodes with values defined. "
                    "This means that these two configs would overwrite each other."
                )

        if key in node:
            if isinstance(node[key], dict):
                raise ValueError(
                    f"In the configs, for '{_path_to_str(full_path)}' there are both a"
                    f" value ({value}) and child nodes with values defined. "
                    "This means that these two configs would overwrite each other."
                )
            else:
                raise ValueError(
                    f"The key {_path_to_str(full_path)} has conflicting values "
                    f"assigned: {node[key]} and {value}."
                )
        else:
            node[key] = value

    return result


def dict_to_pathvalues(
    d: dict[str, Any], /, path: Path = ()
) -> Iterator[tuple[StrictPath, Any]]:
    """Yield paths and leaf values of a nested dictionary.

    >>> list(dict_to_pathvalues(dict(a=dict(b=3), c=2)))
    [(('a', 'b'), 3), (('c',), 2)]
    """
    path = normalize_path(path)
    for subkey, value in d.items():
        cur_path = (*path, subkey)
        if isinstance(value, dict):
            yield from dict_to_pathvalues(value, path=cur_path)
        else:
            yield cur_path, value


def merge_configs(*dicts: Config) -> Config:
    """Merge multiple Config dictionaries into a single one.

    This function includes error checking for duplicate keys and accidental overwriting
    of subtrees in the nested configuration objects.

    >>> merge_configs(dict(a=dict(b=2)), dict(c=3))
    {'a': {'b': 2}, 'c': 3}
    """
    return nested_dict_from_items(
        itertools.chain(*(dict_to_pathvalues(d) for d in dicts))
    )
