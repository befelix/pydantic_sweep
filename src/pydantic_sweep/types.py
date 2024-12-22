from __future__ import annotations

from collections.abc import Hashable, Iterable
from typing import TypeAlias, TypeVar, Union

import pydantic

__all__ = [
    "Config",
    "ModelType",
    "Path",
    "StrictPath",
]

StrictPath: TypeAlias = tuple[str, ...]
"""A tuple-path of keys for a pydantic model."""

Path: TypeAlias = Iterable[str] | str
"""Anything that can be converted to a tuple-path (str or iterable of str)."""

Config: TypeAlias = dict[str, Union[Hashable, "Config"]]
"""A nested config dictionary for configurations.

Fields should be hashable (and therefore immutable). That makes them safer to use in 
a configuration, unlike mutable types that may be modified inplace.
"""

ModelType = TypeVar("ModelType", bound=pydantic.BaseModel)
"""TypeVar for a Pydantic Model."""
