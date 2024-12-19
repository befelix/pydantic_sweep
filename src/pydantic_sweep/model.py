import itertools
import typing
from collections.abc import Iterable
from functools import partial
from typing import Any, TypeVar, overload

import more_itertools
import pydantic

from pydantic_sweep.types import Config, ModelType, Path
from pydantic_sweep.utils import merge_configs, normalize_path, pathvalues_to_dict

__all__ = [
    "BaseModel",
    "check_model",
    "initialize",
]

T = TypeVar("T")


class BaseModel(pydantic.BaseModel, extra="forbid", validate_assignment=True):
    """Base model with validation enabled by default."""

    pass


def _check_model_config(model, /):
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
        elif issubclass(model, pydantic.BaseModel):
            name = model.__name__
        else:
            # Just a leaf node
            continue

        if name in checked:
            continue
        _check_model_config(model)
        checked.add(name)

        for field in model.model_fields.values():
            to_check.append(field.annotation)  # noqa: PERF401


@overload
def initialize(
    model: ModelType | type[ModelType],
    parameters: Iterable[dict[str, Any]],
    path: Path,
) -> list[dict[str, Any]]:
    pass


@overload
def initialize(
    model: ModelType | type[ModelType],
    parameters: Iterable[dict[str, Any]],
    path: None = None,
) -> list[ModelType]:
    pass


def initialize(
    model: ModelType | type[ModelType],
    parameters: Iterable[dict[str, Any]],
    path: Path | None = None,
) -> list[dict[str, Any]] | list[ModelType]:
    """Instantiate the models with the given parameters.

    Parameters
    ----------
    model:
        The pydantic model that we want to finalize. This can be either a model cass
        or an instance of a specific model. In both cases, the configuration is checked
        for safety and the models are instantiated.
    parameters:
        The partial parameter dictionaries that we want to initialize with pydantic.
    path:
        If provided, will return a new configuration with model values at the present
        path. This is useful for initializing nexted models.
    """
    check_model(model)

    if isinstance(model, pydantic.BaseModel):
        result: list[ModelType] = [
            model.model_validate(model.model_copy(update=parameter).model_dump())  # type: ignore[misc]
            for parameter in parameters
        ]
    else:
        result = [model(**parameter) for parameter in parameters]

    # TODO: Test!
    if path is None:
        return result
    else:
        path = tuple(path.split(".")) if isinstance(path, str) else tuple(path)
        return [pathvalues_to_dict([(path, res)]) for res in result]


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
    path = normalize_path(path)
    if isinstance(values, str):
        raise ValueError("values must be iterable, but got a string")

    return [pathvalues_to_dict([(path, value)]) for value in values]


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
