from __future__ import annotations

from collections.abc import Hashable, Iterable
from typing import Protocol, TypeAlias, TypeVar, Union

import pydantic

__all__ = [
    "Chainer",
    "Combiner",
    "Config",
    "FieldValue",
    "FlexibleConfig",
    "Path",
    "StrictPath",
]


StrictPath: TypeAlias = tuple[str, ...]
"""A tuple-path of keys for a pydantic model."""

Path: TypeAlias = Union[str, Iterable[str], "StrictPath"]
"""Anything that can be converted to a tuple-path (str or iterable of str)."""

FieldValue: TypeAlias = Hashable | pydantic.BaseModel
"""The possible values that should be assigned to a field.

Fields should be hashable (and therefore immutable) values. That makes them safer to 
use in a configuration, since unlike mutable types they can not be modified inplace.
"""

Config: TypeAlias = dict[str, Union["FieldValue", "Config"]]
"""A nested config dictionary for configurations."""

FlexibleConfig: TypeAlias = dict["Path", Union["FieldValue", "FlexibleConfig"]]
"""A flexible config that allows any Path."""

T = TypeVar("T")


class Combiner(Protocol[T]):
    """A function that yields tuples of items."""

    def __call__(self, *configs: Iterable[T]) -> Iterable[tuple[T, ...]]: ...


class Chainer(Protocol[T]):
    """A function that chains iterables together."""

    def __call__(self, *configs: Iterable[T]) -> Iterable[T]: ...


BaseModelT = TypeVar("BaseModelT", bound=pydantic.BaseModel)
"""TypeVar for a pydantic BaseModel."""
