from __future__ import annotations

import copy
import itertools
import re
import typing
from collections.abc import Iterable, Iterator
from typing import Any, Literal, TypeVar, overload

from pydantic_sweep._utils import items_skip
from pydantic_sweep.types import Config, FieldValue, FlexibleConfig, Path, StrictPath

__all__ = [
    "items_skip",
    "merge_nested_dicts",
    "nested_dict_at",
    "nested_dict_from_items",
    "nested_dict_get",
    "nested_dict_items",
    "nested_dict_replace",
    "normalize_path",
    "path_to_str",
]


T = TypeVar("T")
GenericUnion = type(T | str)
"""A Generic Union type"""

SpecialGenericAlias = type(typing.List[str])  # noqa: UP006
"""Old-style GenericAlias"""

valid_key_pattern = r"[A-Za-z_][A-Za-z0-9_]*"
# Valid python keys starts with letters and can contain numbers and underscores after
_STR_PATH_PATTERN = re.compile(rf"^{valid_key_pattern}(\.{valid_key_pattern})*$")
_STR_KEY_PATTERN = re.compile(rf"^{valid_key_pattern}$")
# Explanation:
# ^ - Matches the start of the string.
# We first match a valid key, followed by dot-seperated valid keys
# $ - Matches the end of the string.


def path_to_str(p: Path, /) -> str:
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
    match path:
        case str():
            if not re.fullmatch(_STR_PATH_PATTERN, path):
                raise ValueError(
                    "If provided as a string, the path must consist only of "
                    f"dot-separated keys. For example, 'my.key'. Got {path})"
                )
            return tuple(path.split("."))
        case tuple():
            pass
        case Iterable():
            path = tuple(path)
        case _:
            raise ValueError(f"Expected a path, got {path}")

    if check_keys:
        for p in path:
            if not re.fullmatch(_STR_KEY_PATTERN, p):
                raise ValueError(
                    f"Paths can only contain letters and underscores, got {p}."
                )

    return path


@overload
def nested_dict_get(d: Config, /, path: Path, *, leaf: Literal[True]) -> FieldValue: ...


@overload
def nested_dict_get(d: Config, /, path: Path, *, leaf: Literal[False]) -> Config: ...


@overload
def nested_dict_get(
    d: Config, /, path: Path, *, leaf: None = None
) -> Config | FieldValue: ...


def nested_dict_get(
    d: Config, /, path: Path, *, leaf: bool | None = None
) -> Config | FieldValue:
    """Return the value of a nested dict at a certain path.

    Parameters
    ----------
    d
        The config to check
    path
        A path that we want to resolve.
    leaf
        If ``True``, check that we return a leaf node. If ``False``, check that we
        return a non-leaf node.

    Raises
    ------
    KeyError
        If the path does not exist.
    ValueError
        If the result does not match what we specified in ``leaf``.
    """
    path = normalize_path(path)
    node = d

    # Navigate to the sub-path in the nested dictionary
    if path:
        try:
            for i, key in enumerate(path):
                node = node[key]  # type: ignore[assignment]
        except TypeError as e:
            raise KeyError(
                f"Expected a dictionary at {path_to_str(path[:i])}, got {type(node)}."
            ) from e
        except KeyError as e:
            raise KeyError(
                f"The path '{path_to_str(path)}' is not part of the dictionary."
            ) from e

    # No special checks needed
    if leaf is None:
        return node

    if leaf:
        if isinstance(node, dict):
            raise ValueError(
                f"Expected a leaf at path {path_to_str(path)}, but got a dictionary."
            )
    else:
        if not isinstance(node, dict):
            raise ValueError(
                f"Expected a non-leaf node at path {path_to_str(path)}, but got "
                f"{type(node)}."
            )
    return node


def nested_dict_replace(
    d: Config, /, path: Path, value: FieldValue, *, inplace: bool = False
) -> Config:
    """Replace the value of a nested dict at a certain path (out of place).

    Parameters
    ----------
    d :
        The dictionary to replace the value in.
    path :
        The path to the key to replace.
    value :
        The new value to set at the path.
    inplace :
        If ``True``, modify the input dictionary inplace. Otherwise, return a new
        dictionary with the value replaced.
    """
    if not inplace:
        d = copy.deepcopy(d)

    *subpath, key = normalize_path(path)
    sub = nested_dict_get(d, path=subpath, leaf=False)

    if key not in sub:
        raise KeyError(f"The path '{path_to_str(path)}' is not part of the dictionary.")
    else:
        sub[key] = value

    return d


def nested_dict_drop(d: Config, /, path: Path, *, inplace: bool = False) -> Config:
    """Remove a key from a nested dict at a certain path.

    Parameters
    ----------
    d :
        The dictionary to remove the key from.
    path :
        The path to the key to remove.
    inplace :
        If ``True``, modify the input dictionary inplace. Otherwise, return a new
        dictionary with the key removed.
    """
    if not inplace:
        d = copy.deepcopy(d)

    *subpath, key = normalize_path(path)
    sub = nested_dict_get(d, path=subpath, leaf=False)

    if key not in sub:
        raise KeyError(f"The path '{path_to_str(path)}' is not part of the dictionary.")
    else:
        del sub[key]

    return d


def nested_dict_at(path: Path, value: FieldValue) -> Config:
    """Return nested dictionary with the value at path."""
    path = normalize_path(path)
    return nested_dict_from_items([(path, value)])


def nested_dict_from_items(
    items: Iterable[tuple[StrictPath, FieldValue | Config]], /
) -> Config:
    """Convert paths and values (items) to a nested dictionary.

    Paths are assumed as single dot-separated strings.
    """
    result: dict[str, Any] = dict()

    for full_path, value in items:
        *path, key = full_path
        node = result

        for part in path:
            if part not in node:
                node[part] = dict()

            node = node[part]

            if not isinstance(node, dict):
                raise ValueError(
                    f"In the configs, for '{path_to_str(path)}' there are both a "
                    f"value ({node}) and child nodes with values defined. "
                    "This means that these two configs would overwrite each other."
                )

        if key in node:
            if isinstance(node[key], dict):
                raise ValueError(
                    f"In the configs, for '{path_to_str(full_path)}' there are both a"
                    f" value ({value}) and child nodes with values defined. "
                    "This means that these two configs would overwrite each other."
                )
            else:
                raise ValueError(
                    f"The key {path_to_str(full_path)} has conflicting values "
                    f"assigned: {node[key]} and {value}."
                )
        else:
            node[key] = value

    return result


def _nested_dict_items(
    d: FlexibleConfig | Config, /, path: StrictPath
) -> Iterator[tuple[StrictPath, FieldValue]]:
    """See nested_dict_items"""
    for subkey, value in d.items():
        cur_path = (*path, *normalize_path(subkey))
        if isinstance(value, dict):
            yield from _nested_dict_items(value, path=cur_path)
        else:
            yield cur_path, value


def nested_dict_items(
    d: FlexibleConfig | Config, /
) -> Iterator[tuple[StrictPath, FieldValue]]:
    """Yield paths and leaf values of a nested dictionary.

    Note: This function has special handling for Paths, i.e., it will expand
    dot-separated keys and tuples-keys into nested paths.

    >>> list(nested_dict_items(dict(a=dict(b=3), c=2)))
    [(('a', 'b'), 3), (('c',), 2)]
    """
    if not isinstance(d, dict):
        raise TypeError(f"Expected a dictionary, got {d} of type {type(d)}.")
    return _nested_dict_items(d, path=())


def merge_nested_dicts(
    *dicts: FlexibleConfig | Config, overwrite: bool = False
) -> Config:
    """Merge multiple Config dictionaries into a single one.

    This function includes error checking for duplicate keys and accidental overwriting
    of subtrees in the nested configuration objects.

    >>> merge_nested_dicts(dict(a=dict(b=2)), dict(c=3))
    {'a': {'b': 2}, 'c': 3}

    >>> merge_nested_dicts(dict(a=dict(b=2)), dict(a=5), overwrite=True)
    {'a': 5}
    """
    if not overwrite:
        return nested_dict_from_items(
            itertools.chain.from_iterable(nested_dict_items(d) for d in dicts)
        )

    res: Config = dict()
    for d in dicts:
        for path, value in nested_dict_items(d):
            node: dict = res
            *subpath, final = path
            for key in subpath:
                if key not in node or not isinstance(node[key], dict):
                    node[key] = dict()
                node = node[key]
            node[final] = value

    return res


class _NoSkip:
    pass


def _flexible_config_to_nested(
    config: FlexibleConfig | Config, /, skip: Any = _NoSkip
) -> Config:
    """Normalize a flexible config to a nested dictionary."""
    items = nested_dict_items(config)
    if skip is not _NoSkip:
        items = items_skip(items, target=skip)
    return nested_dict_from_items(items)
