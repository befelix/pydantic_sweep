from __future__ import annotations

import itertools
import operator
from collections.abc import Callable, Iterator, Mapping, Sequence
from typing import Any

import pydantic

from pydantic_sweep._nested_dict import nested_dict_from_items
from pydantic_sweep.types import StrictPath

__all__ = [
    "model_diff",
]


class MissingMeta(type):
    def __repr__(cls) -> str:
        return "Missing"


class Missing(metaclass=MissingMeta):
    """A Missing value"""

    pass


def _model_diff_iter(
    m1: Any, m2: Any, *, path: StrictPath = (), compare: Callable[[Any, Any], bool]
) -> Iterator[tuple[StrictPath, tuple]]:
    """Iterator implementation for model_diff."""
    # Different types are treated differently by design. One could in principle
    # compare tuples and dicts, but given that the core usecase is pydantic models
    # these will get normalized to the same type in any case.
    cls = type(m1)
    if cls is not type(m2):
        yield path, (m1, m2)
        return

    match m1:
        case pydantic.BaseModel():
            # Thanks to previous check, we know they have the same keys
            for name in cls.model_fields:
                value1 = getattr(m1, name)
                value2 = getattr(m2, name)
                yield from _model_diff_iter(
                    value1, value2, path=(*path, name), compare=compare
                )

        case Mapping():
            keys = m1.keys() | m2.keys()
            for key in keys:
                if key not in m1:
                    yield (*path, f"[{key}]"), (Missing, m2[key])
                elif key not in m2:
                    yield (*path, f"[{key}]"), (m1[key], Missing)
                else:
                    yield from _model_diff_iter(
                        m1[key], m2[key], path=(*path, f"[{key}]"), compare=compare
                    )

        case Sequence() if not isinstance(m1, str):
            for i, (v1, v2) in enumerate(
                itertools.zip_longest(m1, m2, fillvalue=Missing)
            ):
                yield from _model_diff_iter(
                    v1, v2, path=(*path, f"[{i}]"), compare=compare
                )

        case _:
            # A leaf node that we cannot expand directly --> call standard comparator
            if not compare(m1, m2):
                yield path, (m1, m2)


def model_diff(
    m1: Any,
    m2: Any,
    /,
    *,
    compare: Callable[[Any, Any], bool] = operator.eq,
) -> dict[str, Any]:
    """Return a nested dictionary of model diffs.

    That is, given two models this function iterates over all nested sub-model fields
    and returns a nested dictionaries with leaf values that are tuples of the
    corresponding value of the left model, and the value of the right model.

    Parameters
    ----------
    m1 :
        The first model, or nested structure.
    m2 :
        The second model, or nested structure
    compare :
        Function to compare two elements, returns ``True`` if they are equal.

    Examples
    --------
    >>> class Sub(pydantic.BaseModel):
    ...     x: int = 0

    >>> class Model(pydantic.BaseModel):
    ...     s: Sub = Sub()
    ...     y: int = 2

    >>> model_diff(Model(s=Sub(x=1)), Model(s=Sub(x=2)))
    {'s': {'x': (1, 2)}}

    >>> model_diff(Model(), Model())
    {}
    """
    return nested_dict_from_items(_model_diff_iter(m1, m2, compare=compare))
