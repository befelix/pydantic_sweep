from __future__ import annotations

import enum
import random
import types
import typing
import warnings
from collections.abc import Hashable, Iterable, Iterator
from typing import Any, Literal, TypeVar

import pydantic
from typing_extensions import Self

__all__ = [
    "as_hashable",
    "items_skip",
    "notebook_link",
    "raise_warn_ignore",
    "random_seeds",
]


T = TypeVar("T")
GenericUnion = type(T | str)
"""A Generic Union type"""

SpecialGenericAlias = type(typing.List[str])  # noqa: UP006
"""Old-style GenericAlias"""


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
                (key, as_hashable(getattr(item, key)))
                for key in item.__class__.model_fields
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


class RaiseWarnIgnore(enum.Enum):
    """Actions for `raise_warn_ignore`."""

    RAISE = "raise"
    WARN = "warn"
    IGNORE = "ignore"

    @classmethod
    def cast(cls, name: str | Self, /) -> Self:
        try:
            return cls(name)
        except ValueError:
            options = ", ".join([action.value for action in cls])
            raise ValueError(f"{name} is not a valid action. Options are: {options}")


def raise_warn_ignore(
    message: str,
    *,
    action: Literal["raise", "warn", "ignore"] | RaiseWarnIgnore,
    exception: type[Exception] = ValueError,
    warning: type[Warning] = UserWarning,
) -> None:
    """Raise/warn/ignore depending on action input."""
    action = RaiseWarnIgnore.cast(action)
    if action is RaiseWarnIgnore.WARN:
        warnings.warn(message, category=warning)
    elif action is RaiseWarnIgnore.RAISE:
        raise exception(message)


def iter_subtypes(t: type, /) -> Iterator[type]:
    """Iterate over all possible subtypes of the input type.

    >>> list(iter_subtypes(str | int))
    [<class 'str'>, <class 'int'>]

    >>> T = TypeVar("T", bound=str)
    >>> list(iter_subtypes(T | float | int))
    [<class 'str'>, <class 'float'>, <class 'int'>]
    """
    origin = typing.get_origin(t)

    match (origin, t):
        case (typing.Annotated, _):
            sub = typing.get_args(t)[0]
            yield from iter_subtypes(sub)
        case (typing.Union | types.UnionType, _):
            for arg in typing.get_args(t):
                yield from iter_subtypes(arg)
        case (typing.Final, _):
            yield from iter_subtypes(*typing.get_args(t))
        case (typing.Literal, _):
            for arg in typing.get_args(t):
                yield type(arg)
        case (_, types.GenericAlias() | SpecialGenericAlias()):  # type: ignore
            # Generic alias: list[str], special: typing.List[str]
            if origin is not None:
                yield from iter_subtypes(origin)
            for arg in typing.get_args(t):
                if arg is not Ellipsis:
                    yield from iter_subtypes(arg)
        case (_, typing.TypeVar()):
            if t.__bound__ is not None:  # type: ignore[unresolved-attribute]
                yield from iter_subtypes(t.__bound__)  # type: ignore[unresolved-attribute]
            elif t.__constraints__:  # type: ignore[unresolved-attribute]
                for constraint in t.__constraints__:  # type: ignore[unresolved-attribute]
                    yield from iter_subtypes(constraint)
            else:
                # Unconstrained typevar can take any value.
                yield typing.Any
        case _:
            if origin is None:
                yield t
            else:
                # Resolves special types like typing.List
                yield origin
