from __future__ import annotations

from collections.abc import Collection, Mapping
from typing import Any, cast

import pydantic

__all__ = ["model_to_python"]


def model_to_python(
    model: pydantic.BaseModel,
    *,
    exclude_defaults: bool = True,
    include: Collection[str] | Mapping[str, Any] | None = None,
) -> str:
    """Generate python code for a pydantic model.

    This function generates python code that instantiates a given model. This is,
    for example, useful to switch json/yaml configuration files to Python-native ones.

    Parameters
    ----------
    model :
        The model that we want to convert to Python code
    exclude_defaults :
        Whether to exclude default arguments.
    include :
        Additional fields to include.

    Returns
    -------
    The corresponding python code including imports.
    """
    model_classes: set[type[object]] = set()
    lines: list[str] = []
    include = cast(None | dict | set[str], include)  # pydantic is too strict here
    dump = model.model_dump(exclude_defaults=exclude_defaults, include=include)

    _add_python_code(
        model=model,
        field_name="model",
        dump=dump,
        indent=0,
        lines=lines,
        model_classes=model_classes,
    )

    import_lines = _generate_imports(model_classes)
    return "\n".join([*sorted(import_lines), "", "", *lines])


def _generate_imports(classes: Collection[type[object]], /) -> list[str]:
    if len(set(cls.__name__ for cls in classes)) != len(classes):
        from collections import Counter

        counts = Counter(cls.__name__ for cls in classes)
        duplicates = [name for name, count in counts.items() if count > 1]
        raise ValueError(
            "The following models share the same name, but exist at different code "
            f"paths. This is currently not supported: {', '.join(duplicates)}."
        )

    return [f"from {cls.__module__} import {cls.__name__}" for cls in classes]


def _add_python_code(
    model: pydantic.BaseModel,
    *,
    field_name: str,
    dump: dict,
    indent: int,
    lines: list,
    model_classes: set,
) -> None:
    cls = type(model)
    if cls.__qualname__ != cls.__name__:
        raise ValueError("Cannot generate code for local modules.")
    model_classes.add(cls)

    model_whitespace = "    " * indent
    field_whitespace = "    " * (indent + 1)

    if indent == 0:
        lines.append(f"{field_name} = {cls.__name__}(")
    else:
        lines.append(f"{model_whitespace}{field_name}={cls.__name__}(")

    for key, dump_value in dump.items():
        field_value = getattr(model, key)
        if isinstance(field_value, pydantic.BaseModel):
            _add_python_code(
                model=field_value,
                field_name=key,
                dump=dump_value,
                lines=lines,
                model_classes=model_classes,
                indent=indent + 1,
            )
        else:
            lines.append(f"{field_whitespace}{key}={dump_value!r},")
    lines.append(f"{model_whitespace})")
