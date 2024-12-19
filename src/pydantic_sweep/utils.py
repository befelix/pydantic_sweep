import itertools
import typing
from collections.abc import Iterable, Iterator
from functools import partial
from typing import Any, TypeAlias, TypeVar

import more_itertools

Path: TypeAlias = tuple[str, ...]
Config: TypeAlias = dict[str, Any]
T = TypeVar("T")


def _path_to_str(p: Path, /) -> str:
    return ".".join(p)


def paths_to_dict(items: Iterable[tuple[Path, Any]], /) -> dict[str, Any]:
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
                print(full_path)
                raise ValueError(
                    f"The key {_path_to_str(full_path)} has conflicting values "
                    f"assigned: {node[key]} and {value}."
                )
        else:
            node[key] = value

    return result


def _dict_to_paths(d: dict[str, Any], /, path: Path = ()) -> Iterator[tuple[Path, Any]]:
    for subkey, value in d.items():
        cur_path = (*path, subkey)
        if isinstance(value, dict):
            yield from _dict_to_paths(value, path=cur_path)
        else:
            yield cur_path, value


def merge_configs(*dicts: Config) -> Config:
    """Merge multiple Config dictionaries into a single one.

    This function includes error checking for duplicate keys and accidental overwriting
    of subtrees in the nested configuration objects.
    """
    return paths_to_dict(itertools.chain(*(_dict_to_paths(d) for d in dicts)))


def field(path: str | Path, values: Iterable) -> list[Config]:
    if isinstance(values, str):
        raise ValueError("values must be iterable, but got a string")

    path: tuple[str, ...] = (
        tuple(path.split(".")) if isinstance(path, str) else tuple(path)
    )
    return [paths_to_dict([(path, value)]) for value in values]


class Combiner(typing.Protocol, typing.Generic[T]):
    """A function that yields tuples of items."""

    def __call__(self, *configs: Iterable[T]) -> Iterable[tuple[T, ...]]:
        pass


class Chainer(typing.Protocol, typing.Generic[T]):
    """A function that chains iterables together."""

    def __call__(self, *configs: Iterable[T]) -> Iterable[T]:
        pass


def config_combine(
    *configs: list[Config],
    combiner: Combiner | None = None,
    chainer: Chainer | None = None,
) -> list[Config]:
    if combiner is not None:
        if chainer is not None:
            raise ValueError("Can only provide `combiner` or `chainer`, not both")
        return [merge_configs(*combo) for combo in combiner(*configs)]
    elif chainer is not None:
        return list(chainer(*configs))
    else:
        raise ValueError("Must provide one of `single_out` or `multi_out`")


def config_product(*configs: list[Config]) -> list[Config]:
    return config_combine(*configs, combiner=itertools.product)


def config_zip(*configs: list[Config]) -> list[Config]:
    safe_zip = partial(zip, strict=True)
    return config_combine(*configs, combiner=safe_zip)


def config_chain(*configs: list[Config]) -> list[Config]:
    return config_combine(*configs, chainer=itertools.chain)


def config_roundrobin(*configs: list[Config]) -> list[Config]:
    return config_combine(*configs, chainer=more_itertools.roundrobin)
