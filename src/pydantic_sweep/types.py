from __future__ import annotations

from collections.abc import Hashable, Iterable
from typing import Protocol, TypeAlias, TypeVar, Union

__all__ = [
    "Chainer",
    "Combiner",
    "Config",
    "Path",
    "StrictPath",
]

T = TypeVar("T")

StrictPath: TypeAlias = tuple[str, ...]
"""A tuple-path of keys for a pydantic model."""

Path: TypeAlias = Iterable[str] | str
"""Anything that can be converted to a tuple-path (str or iterable of str)."""

Config: TypeAlias = dict[str, Union[Hashable, "Config"]]
"""A nested config dictionary for configurations.

Fields should be hashable (and therefore immutable). That makes them safer to use in 
a configuration, unlike mutable types that may be modified inplace.
"""


class Combiner(Protocol[T]):
    """A function that yields tuples of items."""

    def __call__(self, *configs: Iterable[T]) -> Iterable[tuple[T, ...]]: ...


class Chainer(Protocol[T]):
    """A function that chains iterables together."""

    def __call__(self, *configs: Iterable[T]) -> Iterable[T]: ...
