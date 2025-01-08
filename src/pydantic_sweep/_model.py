import itertools
import types
from collections.abc import Hashable, Iterable
from functools import partial
from typing import Any, Self, TypeVar, overload

import more_itertools
import pydantic

from pydantic_sweep._utils import (
    as_hashable,
    items_skip,
    merge_nested_dicts,
    nested_dict_at,
    nested_dict_from_items,
    nested_dict_get,
    nested_dict_items,
    nested_dict_replace,
    normalize_path,
    notebook_link,
)
from pydantic_sweep.types import Chainer, Combiner, Config, FieldValue, Path

__all__ = [
    "BaseModel",
    "DefaultValue",
    "check_model",
    "check_unique",
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

    @pydantic.model_validator(mode="before")
    @classmethod
    def _safe_union_validator(cls, data: Any) -> Any:
        """Disallow unsafe matches to nested Union models.

        By default, pydantic does not raise an error if multiple pydantic models in a
        union type could match the provided data.
        """
        if isinstance(data, dict):
            fields = cls.model_fields
            for key, value in data.items():
                # Only dicts needs special handling, since static values cannot
                # represent nested models. This also covers the case if value is
                # already a pydantic model.
                if not isinstance(value, dict):
                    continue

                # extra items are handled by extra='forbid' model setting.
                try:
                    field = fields[key]
                except AttributeError:
                    continue

                # Fields that are not Unions are safely resolved by pydantic
                if not isinstance(field.annotation, types.UnionType):
                    continue

                # Discriminators are an alternative way to handle this
                if field.discriminator is not None or any(
                    isinstance(m, pydantic.Discriminator) for m in field.metadata
                ):
                    continue

                # Manually validate each model.
                matches = []
                for annotation in field.annotation.__args__:
                    # Any other type should not need validation, since either they
                    # can't match or, in the case of dictionaries, pydantic models
                    # are preferred under the best-match strategy.
                    if isinstance(annotation, type) and issubclass(
                        annotation, pydantic.BaseModel
                    ):
                        try:
                            res = annotation.model_validate(value)
                        except pydantic.ValidationError:
                            pass
                        else:
                            matches.append((annotation.__name__, res))

                if len(matches) > 1:
                    from pydantic_core import PydanticCustomError

                    raise PydanticCustomError(
                        "unsafe_union_error",
                        "Multiple models of a Union type could match the provided "
                        "data: {conflicts}. To avoid this error, either "
                        "initialize the nested model manually using the `initialize` "
                        "method or use a discriminated union. See {docs} for details.",
                        dict(
                            conflicts=", ".join([name for name, _ in matches]),
                            docs=notebook_link("nested"),
                        ),
                    )
                elif matches:
                    # Avoid re-running the model validation downstream
                    data[key] = matches[0][1]

        return data


class NameMetaClass(type):
    """A metaclass that overwrite cls.__str__ to its name"""

    def __str__(cls) -> str:
        return cls.__name__


class DefaultValue(metaclass=NameMetaClass):
    """Indicator class for a default value in the ``field`` method."""

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
            "Model must have extra=forbid option enabled. Without this, typos in "
            "field names will be silently ignored."
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


def _config_prune_default(config: Config) -> Config:
    """Prune default value placeholders from a config.

    This allows pydantic to handle initialization of them.
    """
    items = nested_dict_items(config)
    items = items_skip(items, target=DefaultValue)
    return nested_dict_from_items(items)


@overload
def initialize(
    model: type[pydantic.BaseModel],
    configs: Iterable[Config],
    *,
    constant: dict[str, Any] | None = None,
    default: dict[str, Any] | None = None,
    to: Path,
    at: Path | None = None,
) -> list[Config]:
    pass


@overload
def initialize(
    model: type[pydantic.BaseModel],
    configs: Iterable[Config],
    *,
    constant: dict[str, Any] | None = None,
    default: dict[str, Any] | None = None,
    to: Path | None = None,
    at: Path,
) -> list[Config]:
    pass


@overload
def initialize(
    model: type[pydantic.BaseModel],
    configs: Iterable[Config],
    *,
    constant: dict[str, Any] | None = None,
    default: dict[str, Any] | None = None,
    to: None = None,
    at: None = None,
) -> list[pydantic.BaseModel]:
    pass


def initialize(
    model: type[pydantic.BaseModel],
    configs: Iterable[Config],
    *,
    constant: dict[str, Any] | None = None,
    default: dict[str, Any] | None = None,
    to: Path | None = None,
    at: Path | None = None,
) -> list[Config] | list[pydantic.BaseModel]:
    """Instantiate the models with the given parameters.

    Parameters
    ----------
    model:
        The pydantic model that we want to finalize. This can be either a model cass
        or an instance of a specific model. In both cases, the configuration is checked
        for safety and the models are instantiated.
    configs:
        The partial config dictionaries that we want to initialize with pydantic.
    constant:
        Constant values that should be initialized for all models. These are safely
        merged with the parameters. Can be either a nested, or a flattened dictionary.
    default:
        Default parameter that are initialized for all models, but may be overwritten by
        other fields without any error checking. Can be either a nested or a flattened
        dictionary.
    to:
        If provided, will first initialize the model and then return a
        configuration dictionary that sets the model as the values at the given path.
        Essentially a shortcut to first passing the models to ``field(to, models)``.
    at:
        If provided, will initialize the model at the given path in the configuration.
    """
    check_model(model)

    if constant is not None:
        if not isinstance(constant, dict):
            raise TypeError(
                f"Expected dictionary for input 'constant', got '{type(constant)}'."
            )

        constant = nested_dict_from_items(
            (normalize_path(key), value) for key, value in constant.items()
        )
        configs = config_product(configs, [constant])

    # Remove placeholders now
    configs = [_config_prune_default(config) for config in configs]

    if default is not None:
        if not isinstance(default, dict):
            raise TypeError(
                f"Expected dictionary for input 'default', got '{type(default)}'."
            )
        # A DefaultValue as a default should not change anything
        default = nested_dict_from_items(
            (normalize_path(key), value)
            for key, value in default.items()
            if value is not DefaultValue
        )
        configs = [
            merge_nested_dicts(default, param, overwrite=True) for param in configs
        ]

    # Initialize a subconfiguration at the path ``at``
    if at is not None:
        if to is not None:
            raise ValueError("Only on of `path` and `at` can be provided, not both.")

        subconfigs = [nested_dict_get(param, at, leaf=False) for param in configs]
        submodels = initialize(model, subconfigs)
        return [
            nested_dict_replace(param, path=at, value=submodel)
            for param, submodel in zip(configs, submodels)
        ]

    # Initialize the provided models
    models = [model(**config) for config in configs]

    if to is not None:
        # Check not needed here: values are all pydantic.BaseModel by design
        return field(to, models, check=False)
    else:
        return models


def field(
    path: Path, /, values: Iterable[FieldValue], *, check: bool = True
) -> list[Config]:
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
    check
        If ``True``, check that values are indeed hashable or pydantic Models.

    Returns
    -------
    list[Config]:
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

    if check:
        # Iterators may get exhausted
        values = list(values)
        for value in values:
            # Note: DefaultValue is hashable
            if not isinstance(value, pydantic.BaseModel | Hashable):
                raise ValueError(
                    f"Value {value} of type {type(value)} is not hashable, which can "
                    f"cause unexpected behaviors. You can disable this check by "
                    f"passing `check=False` as a keyword argument."
                )

    return [nested_dict_at(path, value) for value in values]


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
    list[Config]:
        A list of new configuration objects after combining or chaining.
    """
    if combiner is not None:
        if chainer is not None:
            raise ValueError("Can only provide `combiner` or `chainer`, not both")
        return [merge_nested_dicts(*combo) for combo in combiner(*configs)]
    elif chainer is not None:
        res = list(chainer(*configs))
        if not isinstance(res[0], dict):
            raise ValueError(
                f"Chained items are not dictionaries, but {type(res[0])}. Are you sure "
                f"that you passed a valid chainer function? "
            )
        return res
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


def check_unique(
    *models_: Config | pydantic.BaseModel | Iterable[Config | pydantic.BaseModel],
    raise_exception: bool = True,
) -> bool:
    """Check that models are unique.

    Parameters
    ----------
    *models_
        Iterables of models to check for uniqueness. If multiple are passed, they are
        chained together and jointly checked.

    Raises
    ------
    ValueError
        If models are not unique.
    """
    seen = set()
    for models in models_:
        if isinstance(models, pydantic.BaseModel | dict):
            models = [models]
        for model in models:
            model_hash = hash(as_hashable(model))
            if model_hash in seen:
                if raise_exception:
                    raise ValueError(f"The following model is not unique: {model}.")
                else:
                    return False
            seen.add(model_hash)

    return True
