from collections.abc import Iterable, Sequence
from typing import Any, TypeVar, overload

import pydantic

from pydantic_sweep.utils import paths_to_dict

__all__ = [
    "BaseModel",
    "check_model",
]

ModelType = TypeVar("ModelType", bound=pydantic.BaseModel)


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
    path: str | Sequence[str],
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
    path: str | Sequence[str] | None = None,
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
        return [paths_to_dict([(path, res)]) for res in result]
