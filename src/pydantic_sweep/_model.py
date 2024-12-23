import itertools
import types
import typing
from collections.abc import Iterable
from functools import partial
from typing import Any, Self, TypeVar, overload

import more_itertools
import pydantic

from pydantic_sweep._utils import (
    merge_nested_dicts,
    nested_dict_at,
    nested_dict_get,
    nested_dict_replace,
    normalize_path,
)
from pydantic_sweep.types import Config, ModelType, Path

__all__ = [
    "BaseModel",
    "DefaultValue",
    "check_model",
    "config_chain",
    "config_combine",
    "config_product",
    "config_roundrobin",
    "config_zip",
    "field",
    "initialize",
]

T = TypeVar("T")


class BaseModel(pydantic.BaseModel, extra="forbid", validate_assignment=True):
    """Base model with validation enabled by default."""

    pass


class DefaultValue:
    """Indicator class for a default value in the `field` method."""

    def __new__(cls, *args: Any, **kwargs: Any) -> Self:
        raise TypeError("This is a sentinel value and not meant to be instantiated.")

    def __init_subclass__(cls, **kwargs: Any) -> None:
        raise TypeError("This is a sentinel value and not meant to be subclassed.")


def _check_model_config(
    model: pydantic.BaseModel | type[pydantic.BaseModel], /
) -> None:
    config = model.model_config
    if "extra" not in config or config["extra"] != "forbid":
        raise ValueError(
            "Model must have extra=forbid option enabled. Without "
            "this typose in parameters will be silently ignored."
        )

    if "validate_assignment" not in config or not config["validate_assignment"]:
        raise ValueError(
            "Model must have validate_assignment=True option enabled. "
            "Without this the type of arguments will not be verified."
        )


def check_model(model: pydantic.BaseModel | type[pydantic.BaseModel], /) -> None:
    """Best-effort check that the model has the correct configuration.

    This recurses into the models, but there's probably a way to achieve a
    false positive if one tries.
    """
    to_check: list[Any] = [model]
    checked = set()

    while to_check:
        model = to_check.pop()

        if isinstance(model, pydantic.BaseModel):
            name = model.__class__.__name__
        # Subclass can raise error for inputs that are not type
        # https://github.com/python/cpython/issues/101162
        elif isinstance(model, type) and issubclass(model, pydantic.BaseModel):
            name = model.__name__
        else:
            # Just a leaf node
            continue

        if name in checked:
            continue

        _check_model_config(model)
        checked.add(name)

        for field in model.model_fields.values():
            annotation = field.annotation
            if isinstance(annotation, types.UnionType):
                to_check.extend(annotation.__args__)
            else:
                to_check.append(annotation)


@overload
def initialize(
    model: ModelType | type[ModelType],
    parameters: Iterable[Config],
    *,
    to: Path,
    at: Path | None = None,
) -> list[Config]:
    pass


@overload
def initialize(
    model: ModelType | type[ModelType],
    parameters: Iterable[Config],
    *,
    to: Path | None = None,
    at: Path,
) -> list[Config]:
    pass


@overload
def initialize(
    model: ModelType | type[ModelType],
    parameters: Iterable[Config],
    *,
    to: None = None,
    at: None = None,
) -> list[ModelType]:
    pass


def initialize(
    model: ModelType | type[ModelType],
    parameters: Iterable[Config],
    *,
    to: Path | None = None,
    at: Path | None = None,
) -> list[Config] | list[ModelType]:
    """Instantiate the models with the given parameters.

    Parameters
    ----------
    model:
        The pydantic model that we want to finalize. This can be either a model cass
        or an instance of a specific model. In both cases, the configuration is checked
        for safety and the models are instantiated.
    parameters:
        The partial parameter dictionaries that we want to initialize with pydantic.
    to:
        If provided, will first initialize the model and then return a
        configuration dictionary that sets the model as the values at the given path.
        Essentially a shortcut to first passing the models to ``field(to, models)``.
    at:
        If provided, will initialize the model at the given path in the configuration.
    """
    check_model(model)

    # Initialize a subconfiguration at the path ``at``
    if at is not None:
        if to is not None:
            raise ValueError("Only on of `path` and `at` can be provided, not both.")

        subconfigs = [nested_dict_get(param, at) for param in parameters]
        submodels = initialize(model, subconfigs)
        return [
            nested_dict_replace(param, path=at, value=submodel)
            for param, submodel in zip(parameters, submodels)
        ]

    # Initialize the provided models
    if isinstance(model, pydantic.BaseModel):
        models: list[ModelType] = [
            model.model_validate(model.model_copy(update=parameter).model_dump())  # type: ignore[misc]
            for parameter in parameters
        ]
    else:
        models = [model(**parameter) for parameter in parameters]

    if to is not None:
        return field(to, models)
    else:
        return models


def field(path: Path, /, values: Iterable) -> list[Config]:
    """Assign various values to a field in a pydantic Model.

    Parameters
    ----------
    path :
        The path to the key in the model. Can either be a dot-separated string of
        keys (e.g., ``my.key``) or a tuple of keys (e.g., ``('my', 'key')``.
    values :
        The different values that should be assigned to the field. Note that the
        `DefaultValue` class has a special meaning, since it will be effectively
        ignored, allowing it to be kept to the default model.

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
    path = normalize_path(path, check_keys=True)
    if isinstance(values, str):
        raise ValueError("values must be iterable, but got a string")

    return [
        nested_dict_at(path, value) if value is not DefaultValue else dict()
        for value in values
    ]


class Combiner(typing.Protocol[T]):
    """A function that yields tuples of items."""

    def __call__(self, *configs: Iterable[T]) -> Iterable[tuple[T, ...]]: ...


class Chainer(typing.Protocol[T]):
    """A function that chains iterables together."""

    def __call__(self, *configs: Iterable[T]) -> Iterable[T]: ...


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
        return [merge_nested_dicts(*combo) for combo in combiner(*configs)]
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
