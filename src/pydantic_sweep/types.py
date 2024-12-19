from collections.abc import Sequence
from typing import Any, TypeAlias, TypeVar

import pydantic

__all__ = [
    "Config",
    "ModelType",
    "Path",
    "StrictPath",
]

StrictPath: TypeAlias = tuple[str, ...]
Path: TypeAlias = Sequence[str] | str
Config: TypeAlias = dict[str, Any]
ModelType = TypeVar("ModelType", bound=pydantic.BaseModel)
