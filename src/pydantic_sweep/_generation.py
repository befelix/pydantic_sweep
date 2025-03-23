from __future__ import annotations

import contextlib
from collections.abc import Collection, Generator, Mapping
from enum import Enum
from pathlib import Path
from typing import Any, cast

import pydantic

__all__ = ["model_to_python"]


def model_to_python(
    model: pydantic.BaseModel,
    *,
    name: str = "model",
    exclude_unset: bool = True,
    exclude_defaults: bool = False,
    include: Collection[str] | Mapping[str, Any] | None = None,
) -> str:
    """Generate python code for a pydantic model.

    This function generates python code that instantiates a given model. This is,
    for example, useful to switch json/yaml configuration files to Python-native ones.

    Parameters
    ----------
    model :
        The model that we want to convert to Python code
    name :
        The name of the variable to which we assign the instantiated model.
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
    dump = model.model_dump(
        exclude_defaults=exclude_defaults,
        exclude_unset=exclude_unset,
        include=include,
    )

    _add_python_code(
        model=model,
        field_prefix=f"{name} = ",
        dump=dump,
        indent=0,
        lines=lines,
        model_classes=model_classes,
    )

    import_lines = _generate_imports(model_classes)
    return "\n".join([*sorted(import_lines), "", "", *lines])


def _generate_imports(classes: Collection[type[object]], /) -> list[str]:
    """Generate import statements for the given classes."""
    if len(set(cls.__name__ for cls in classes)) != len(classes):
        from collections import Counter

        counts = Counter(cls.__name__ for cls in classes)
        duplicates = [name for name, count in counts.items() if count > 1]
        raise ValueError(
            "The following models share the same name, but exist at different code "
            f"paths. This is currently not supported: {', '.join(duplicates)}."
        )

    return [f"from {cls.__module__} import {cls.__name__}" for cls in classes]


def _add_import(obj: Any, model_classes: set) -> None | str:
    cls = type(obj)
    if cls.__qualname__ != cls.__name__:
        raise ValueError("Cannot generate code for local modules.")
    if cls.__module__ == "builtins":
        return None
    else:
        model_classes.add(cls)
        return cls.__name__


@contextlib.contextmanager
def _wrapped(
    whitespace: str, prefix: str, open: str, close: str, lines: list[str]
) -> Generator[None, None, None]:
    lines.append(f"{whitespace}{prefix}{open}")
    yield
    # Final line comma not needed (works better with auto-formatting)
    lines[-1] = lines[-1].removesuffix(",")
    if whitespace:
        close += ","
    lines.append(f"{whitespace}{close}")


def _add_python_code(
    model: Any,
    *,
    field_prefix: str,
    dump: Any,
    indent: int,
    lines: list,
    model_classes: set,
) -> None:
    whitespace = "    " * indent

    if isinstance(model, pydantic.BaseModel):
        type_name = _add_import(model, model_classes)
        assert type_name is not None
        assert isinstance(dump, dict)
        open, close = f"{type_name}(", ")"
        with _wrapped(whitespace, field_prefix, open, close, lines):
            for key, dump_value in dump.items():
                _add_python_code(
                    model=getattr(model, key),
                    field_prefix=f"{key}=",
                    dump=dump_value,
                    lines=lines,
                    model_classes=model_classes,
                    indent=indent + 1,
                )
    elif isinstance(model, list | tuple | set):
        type_name = _add_import(model, model_classes=model_classes)

        if isinstance(model, list):
            open, close = "[", "]"
        elif isinstance(model, tuple):
            open, close = "[", "]"
        elif isinstance(model, set):
            open, close = "{", "}"
        else:
            raise ValueError(f"Unsupported collection type: {type(model)}")

        if type_name is not None:
            open = f"{type_name}{open}"
            close = f"{close})"

        with _wrapped(whitespace, field_prefix, open, close, lines):
            for model_item, dump_item in zip(model, dump, strict=True):
                _add_python_code(
                    model=model_item,
                    field_prefix="",
                    dump=dump_item,
                    lines=lines,
                    model_classes=model_classes,
                    indent=indent + 1,
                )
    elif isinstance(model, dict):
        type_name = _add_import(model, model_classes=model_classes)
        if type_name is None:
            open, close = "{", "}"
        else:
            open = f"{type_name}({{"
            close = "})"

        with _wrapped(whitespace, field_prefix, open, close, lines):
            for key, dump_value in dump.items():
                _add_python_code(
                    model=model[key],
                    field_prefix=f"{key!r}: ",
                    dump=dump_value,
                    lines=lines,
                    model_classes=model_classes,
                    indent=indent + 1,
                )
    elif isinstance(dump, Enum):
        enum_cls = _add_import(dump, model_classes=model_classes)
        dump = f"{enum_cls}.{dump.name}"
        lines.append(f"{whitespace}{field_prefix}{dump},")
    else:
        if isinstance(dump, Path):
            dump = str(dump)
        lines.append(f"{whitespace}{field_prefix}{dump!r},")
