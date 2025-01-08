import copy
import itertools
import random
import re
from collections.abc import Hashable, Iterable, Iterator
from typing import Any, Literal, TypeVar, overload

import pydantic

from pydantic_sweep.types import Config, FieldValue, Path, StrictPath

__all__ = [
    "as_hashable",
    "items_skip",
    "merge_nested_dicts",
    "nested_dict_at",
    "nested_dict_from_items",
    "nested_dict_get",
    "nested_dict_items",
    "nested_dict_replace",
    "normalize_path",
    "notebook_link",
    "random_seeds",
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


@overload
def nested_dict_get(d: Config, /, path: Path, *, leaf: Literal[True]) -> FieldValue: ...


@overload
def nested_dict_get(d: Config, /, path: Path, *, leaf: Literal[False]) -> Config: ...


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
    AttributeError
        If the path does not exist.
    ValueError
        If the result does not match what we specified in ``leaf``.
    """
    path = normalize_path(path)
    for p in path:
        d = d[p]  # type: ignore[assignment]
    if leaf is not None:
        if leaf:
            if isinstance(d, dict):
                raise ValueError(
                    f"Expected a leaf at path {_path_to_str(path)}, but got a "
                    f"dictionary."
                )
        else:
            if not isinstance(d, dict):
                raise ValueError(
                    f"Expected a non-leaf node at path {_path_to_str(path)}, but got "
                    f"{type(d)}."
                )
    return d


def nested_dict_replace(
    d: Config, /, path: Path, value: FieldValue, *, inplace: bool = False
) -> Config:
    """Replace the value of a nested dict at a certain path (out of place)."""
    if not inplace:
        d = copy.deepcopy(d)

    *subpath, final = normalize_path(path)

    node = d
    for i, key in enumerate(subpath):
        sub = node[key]
        if not isinstance(sub, dict):
            raise ValueError(
                f"Expected a dictionary at {_path_to_str(subpath[:i+1])}, got {sub}."
            )
        node = sub

    if final not in node:
        raise KeyError(
            f"The path '{_path_to_str(path)}' is not part of the dictionary."
        )
    else:
        node[final] = value

    return d


def nested_dict_at(path: Path, value: FieldValue) -> Config:
    """Return nested dictionary with the value at path."""
    path = normalize_path(path)
    return nested_dict_from_items([(path, value)])


def nested_dict_from_items(items: Iterable[tuple[StrictPath, FieldValue]], /) -> Config:
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


def _nested_dict_items(
    d: Config, /, path: StrictPath = ()
) -> Iterator[tuple[StrictPath, FieldValue]]:
    """See nested_dict_items"""
    path = normalize_path(path)
    if not isinstance(d, dict):
        raise ValueError(f"Expected a dictionary, got {d} of type {type(d)}.")
    for subkey, value in d.items():
        cur_path = (*path, subkey)
        if isinstance(value, dict):
            yield from _nested_dict_items(value, path=cur_path)
        else:
            yield cur_path, value


def nested_dict_items(d: Config, /) -> Iterator[tuple[StrictPath, FieldValue]]:
    """Yield paths and leaf values of a nested dictionary.

    >>> list(nested_dict_items(dict(a=dict(b=3), c=2)))
    [(('a', 'b'), 3), (('c',), 2)]
    """
    return _nested_dict_items(d)


def merge_nested_dicts(*dicts: Config, overwrite: bool = False) -> Config:
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
            itertools.chain(*(nested_dict_items(d) for d in dicts))
        )

    res: Config = dict()
    for d in dicts:
        for path, value in nested_dict_items(d):
            node = res
            *subpath, final = path
            for p in subpath:
                if p not in node or not isinstance(node[p], dict):
                    node[p] = dict()
                node = node[p]  # type: ignore[assignment]
            node[final] = value

    return res


K = TypeVar("K")
V = TypeVar("V")


def items_skip(items: Iterable[tuple[K, V]], target: Any) -> Iterator[tuple[K, V]]:
    """Yield items skipping certain targets."""
    for key, value in items:
        if value is not target:
            yield key, value


def as_hashable(item: Any, /) -> Hashable:
    """Convert input into a unique, hashable representation.

    In addition to the builtin hashable types, this also works for dictionaries and
    pydantic Models (recursively). Sets and lists are also supported, but not dealt
    with recursively.

    Parameters
    ----------
    item
        The item that we want to convert to something hashable.

    Returns
    -------
    Hashable
        A hashable representation of the item.
    """
    match item:
        case Hashable():
            return item
        case pydantic.BaseModel():
            # Cannot use model_dump here, since that would map different models with
            # the same attribute to the same keys. Don't need frozenset, since key
            # order is deterministic
            model_dump = tuple(
                (key, as_hashable(getattr(item, key))) for key in item.model_fields
            )
            return f"pydantic:{item.__class__}:{model_dump}"
        case dict():
            return frozenset((key, as_hashable(value)) for key, value in item.items())
        case set():
            return frozenset(item)
        case list():
            return ("__list_type", tuple(item))
        case _:
            raise TypeError(f"Unhashable object of type {type(item)}")


def random_seeds(num: int, *, upper: int = 1000) -> list[int]:
    """Generate unique random values within a certain range.

    This is useful in scenarios where we don't want to hard-code a random seed,
    but also need reproducibility by setting a seed. Sampling the random seed is a
    good compromise there.

    Parameters
    ----------
    num :
        The number of random seeds to generate.
    upper:
        A non-inclusive upper bound on the maximum seed to generate.

    Returns
    -------
    list[int]:
        A list of integer seeds.
    """
    if upper <= 0:
        raise ValueError("Upper bound must be positive.")

    return random.sample(range(upper), num)


def notebook_link(
    name: Literal["combinations", "example", "intro", "models", "nested"],
    *,
    version: Literal["stable", "latest"] = "stable",
) -> str:
    return f"https://pydantic-sweep.readthedocs.io/{version}/notebooks/{name}.html"
