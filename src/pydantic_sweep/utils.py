import itertools
import re
import typing
from collections.abc import Iterable, Iterator, Sequence
from functools import partial
from typing import Any, TypeAlias, TypeVar

import more_itertools

__all__ = [
    "config_chain",
    "config_combine",
    "config_product",
    "config_roundrobin",
    "config_zip",
    "field",
    "merge_configs",
]


StrictPath: TypeAlias = tuple[str, ...]
Path: TypeAlias = Sequence[str] | str
Config: TypeAlias = dict[str, Any]
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


def _normalize_path(path: Path, /) -> StrictPath:
    """Normalize a path to a tuple of strings."""
    if isinstance(path, str):
        if not re.fullmatch(_STR_PATH_PATTERN, path):
            raise ValueError(
                "If provided as a string, the path must consist only of "
                f"dot-separated keys. For example, 'my.key'. Got {path})"
            )
        return tuple(path.split("."))
    else:
        for p in path:
            if not re.fullmatch(_STR_KEY_PATTERN, p):
                raise ValueError(
                    f"Paths can only contain letters and underscores, got {p}."
                )
        return tuple(path)


def paths_to_dict(items: Iterable[tuple[Path, Any]], /) -> dict[str, Any]:
    """Convert paths and values (items) to a nested dictionary.

    Paths are assumed as single dot-separated strings.
    """
    result: dict[str, Any] = dict()

    for full_path, value in items:
        *path, key = _normalize_path(full_path)
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


def _nested_dict_paths_values(
    d: dict[str, Any], /, path: Path = ()
) -> Iterator[tuple[StrictPath, Any]]:
    """Yield paths and leaf values of a nested dictionary.

    >>> list(_nested_dict_paths_values(dict(a=dict(b=3), c=2)))
    [(('a', 'b'), 3), (('c',), 2)]
    """
    path = _normalize_path(path)
    for subkey, value in d.items():
        cur_path = (*path, subkey)
        if isinstance(value, dict):
            yield from _nested_dict_paths_values(value, path=cur_path)
        else:
            yield cur_path, value


def merge_configs(*dicts: Config) -> Config:
    """Merge multiple Config dictionaries into a single one.

    This function includes error checking for duplicate keys and accidental overwriting
    of subtrees in the nested configuration objects.

    >>> merge_configs(dict(a=dict(b=2)), dict(c=3))
    {'a': {'b': 2}, 'c': 3}
    """
    return paths_to_dict(
        itertools.chain(*(_nested_dict_paths_values(d) for d in dicts))
    )


def field(path: Path, values: Iterable) -> list[Config]:
    """Assign various values to a field in a pydantic Model.

    Parameters
    ----------
    path :
        The path to the key in the model. Can either be a dot-separated string of
        keys (e.g., ``my.key``) or a tuple of keys (e.g., ``('my', 'key')``.
    values :
        The different values that should be assigned to the field.

    Returns
    -------
    A list of partial configuration dictionaries that can be passed to the pydantic
    model.

    Examples
    --------
    >>> import pydantic_sweep as ps

    >>> class Sub(ps.BaseModel):
    ...     x: int = 5
    ...     y: int = 6

    >>> class Model(ps.BaseModel):
    ...     sub: Sub = Sub()
    ...     seed: int = 5

    >>> configs = ps.field("sub.x", [10, 20])
    >>> ps.initialize(Model, configs)
    [Model(sub=Sub(x=10, y=6), seed=5), Model(sub=Sub(x=20, y=6), seed=5)]

    """
    path = _normalize_path(path)
    if isinstance(values, str):
        raise ValueError("values must be iterable, but got a string")

    return [paths_to_dict([(path, value)]) for value in values]


class Combiner(typing.Protocol[T]):
    """A function that yields tuples of items."""

    def __call__(self, *configs: Iterable[T]) -> Iterable[tuple[T, ...]]:
        pass


class Chainer(typing.Protocol[T]):
    """A function that chains iterables together."""

    def __call__(self, *configs: Iterable[T]) -> Iterable[T]:
        pass


def config_combine(
    *configs: Iterable[Config],
    combiner: Combiner | None = None,
    chainer: Chainer | None = None,
) -> list[Config]:
    """Flexible combination of configuration dictionaries.

    In contrast to the more specific functions below, this allows you to flexibly use
    existing functions from ``itertools`` in order to create new combiners. All
    existing combiners build on top of this function.

    The output of this function is a valid input to both itself and other combiner
    functions.

    Parameters
    ----------
    configs :
        The configurations we want to combine.
    combiner :
        A function that takes as input multiple iterables and yields tuples.
        For example: ``itertools.product``.
    chainer :
        A function that takes as input multiple iterables and yields a single new
        iterable. For example: ``itertools.chain``.

    Returns
    -------
    A list of new configuration objects after combining or chaining.
    """
    if combiner is not None:
        if chainer is not None:
            raise ValueError("Can only provide `combiner` or `chainer`, not both")
        return [merge_configs(*combo) for combo in combiner(*configs)]
    elif chainer is not None:
        return list(chainer(*configs))
    else:
        raise ValueError("Must provide one of `single_out` or `multi_out`")


def config_product(*configs: Iterable[Config]) -> list[Config]:
    """A product of existing configuration dictionaries.

    This is the most common way of constructing searches. It constructs the product
    of the inputs.

    >>> config_product(field("a", [1, 2]), field("b", [3, 4]))
    [{'a': 1, 'b': 3}, {'a': 1, 'b': 4}, {'a': 2, 'b': 3}, {'a': 2, 'b': 4}]

    The output of this function is a valid input to both itself and other combiner
    functions.
    """
    return config_combine(*configs, combiner=itertools.product)


def config_zip(*configs: Iterable[Config]) -> list[Config]:
    """Return the zip-combination of configuration dictionaries.

    >>> config_zip(field("a", [1, 2]), field("b", [3, 4]))
    [{'a': 1, 'b': 3}, {'a': 2, 'b': 4}]
    """
    safe_zip = partial(zip, strict=True)
    return config_combine(*configs, combiner=safe_zip)


def config_chain(*configs: Iterable[Config]) -> list[Config]:
    """Chain configuration dictionaries behind each other.

    >>> config_chain(field("a", [1, 2]), field("b", [3, 4]))
    [{'a': 1}, {'a': 2}, {'b': 3}, {'b': 4}]
    """
    return config_combine(*configs, chainer=itertools.chain)


def config_roundrobin(*configs: Iterable[Config]) -> list[Config]:
    """Interleave the configuration dictionaries.

    This is the same behavior as `config_chain`, but instead of chaining them behind
    each other, takes from the different iterables in turn.

    >>> config_roundrobin(field("a", [1, 2, 3]), field("b", [3, 4]))
    [{'a': 1}, {'b': 3}, {'a': 2}, {'b': 4}, {'a': 3}]
    """
    return config_combine(*configs, chainer=more_itertools.roundrobin)
