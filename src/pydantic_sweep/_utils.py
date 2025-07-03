from __future__ import annotations

import copy
import enum
import itertools
import operator
import random
import re
import types
import typing
import warnings
from collections.abc import Callable, Hashable, Iterable, Iterator, Mapping, Sequence
from typing import Any, Literal, TypeVar, overload

import pydantic
from typing_extensions import Self

from pydantic_sweep.types import Config, FieldValue, FlexibleConfig, Path, StrictPath

__all__ = [
    "as_hashable",
    "items_skip",
    "merge_nested_dicts",
    "model_diff",
    "nested_dict_at",
    "nested_dict_from_items",
    "nested_dict_get",
    "nested_dict_items",
    "nested_dict_replace",
    "normalize_path",
    "notebook_link",
    "path_to_str",
    "raise_warn_ignore",
    "random_seeds",
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
                    f"Expected a leaf at path {path_to_str(path)}, but got a "
                    f"dictionary."
                )
        else:
            if not isinstance(d, dict):
                raise ValueError(
                    f"Expected a non-leaf node at path {path_to_str(path)}, but got "
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
                f"Expected a dictionary at {path_to_str(subpath[: i + 1])}, got {sub}."
            )
        node = sub

    if final not in node:
        raise KeyError(f"The path '{path_to_str(path)}' is not part of the dictionary.")
    else:
        node[final] = value

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
    d: FlexibleConfig, /, path: StrictPath
) -> Iterator[tuple[StrictPath, FieldValue]]:
    """See nested_dict_items"""
    if not isinstance(d, dict):
        raise ValueError(f"Expected a dictionary, got {d} of type {type(d)}.")
    for subkey, value in d.items():
        cur_path = (*path, *normalize_path(subkey))
        if isinstance(value, dict):
            yield from _nested_dict_items(value, path=cur_path)
        else:
            yield cur_path, value


def nested_dict_items(d: FlexibleConfig, /) -> Iterator[tuple[StrictPath, FieldValue]]:
    """Yield paths and leaf values of a nested dictionary.

    Note: This function has special handling for Paths, i.e., it will expand
    dot-separated keys and tuples-keys into nested paths.

    >>> list(nested_dict_items(dict(a=dict(b=3), c=2)))
    [(('a', 'b'), 3), (('c',), 2)]
    """
    return _nested_dict_items(d, path=())


def merge_nested_dicts(*dicts: FlexibleConfig, overwrite: bool = False) -> Config:
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
            node: dict = res
            *subpath, final = path
            for p in subpath:
                if p not in node or not isinstance(node[p], dict):
                    node[p] = dict()
                node = node[p]
            node[final] = value

    return res


class _NoSkip:
    pass


def _flexible_config_to_nested(
    config: FlexibleConfig, /, skip: Any = _NoSkip
) -> Config:
    """Normalize a flexible config to a nested dictionary."""
    items = nested_dict_items(config)
    if skip is not _NoSkip:
        items = items_skip(items, target=skip)
    return nested_dict_from_items(items)


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
            if t.__bound__ is not None:
                yield from iter_subtypes(t.__bound__)
            elif t.__constraints__:
                for constraint in t.__constraints__:
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
