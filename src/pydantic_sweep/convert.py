import argparse
import importlib
import os
import runpy
from pathlib import Path
from typing import Any

import pydantic
from typing_extensions import Self

from pydantic_sweep._generation import model_to_python

__all__ = ["load", "model_to_python", "write"]


def _import_module(name: str, /) -> Any:
    """Import a module by name."""
    module_name, class_name = name.rsplit(".", maxsplit=1)
    module = importlib.import_module(module_name)
    return getattr(module, class_name)


def load(source: os.PathLike | str, /, *, model: str) -> pydantic.BaseModel:
    """Load a pydantic model from a file.

    Parameters
    ----------
    source :
        The file that we want to read the model from. Supported extensions are
        ``.json``, ``.yaml`` and ``.py``.
    model :
        The model that we want to load. This is either a path to a module with
        dot-notation (e.g., ``my_module.MyModel``) or, for python files, the
        name of the variable where the model is stored in the file.

    Returns
    -------
    The loaded pydantic model.
    """
    source = Path(source)

    if source.suffix == ".json":
        with source.open("r") as file:
            json_str = file.read()
        cls = _import_module(model)
        return cls.model_validate_json(json_str)
    elif source.suffix == ".yaml":
        import yaml  # type: ignore[import-untyped]

        with source.open("r") as file:
            content = yaml.safe_load(file)

        cls = _import_module(model)
        return cls(**content)
    elif source.suffix == ".py":
        return runpy.run_path(str(source))[model]
    else:
        raise ValueError(f"Unsupported file type: {source.suffix}")


def write(
    target: os.PathLike | str,
    /,
    *,
    model: pydantic.BaseModel,
    yaml_options: dict[str, Any] | None = None,
    exclude_unset: bool = True,
    exclude_defaults: bool = False,
) -> None:
    """Write a model to a file.

    Parameters
    ----------
    target :
        The file to write to. Supported extensions are ``.json``, ``.yaml`` and
        ``.py``.
    model :
        The pydantic model that we want to write to the file.
    yaml_options :
        Optional keyword-arguments passed to ``yaml.dump``.
    exclude_unset :
        Exclude fields that don't have a value set.
    exclude_defaults :
        Exclude fields that have the default value set.
    """
    target = Path(target)
    if target.exists():
        raise FileExistsError(f"File already exists: {target}")
    if target.suffix == ".json":
        dump = model.model_dump_json(
            exclude_unset=exclude_unset, exclude_defaults=exclude_defaults
        )
        with target.open("w") as f:
            f.write(dump)
    elif target.suffix == ".yaml":
        import json

        import yaml

        if yaml_options is None:
            yaml_options = dict()
        # This runs serializers properly (e.g., for Path / Enum objects)
        dump = json.loads(
            model.model_dump_json(
                exclude_unset=exclude_unset, exclude_defaults=exclude_defaults
            )
        )
        with target.open("w") as f:
            yaml.dump(dump, f, **yaml_options)
    elif target.suffix == ".py":
        code = model_to_python(
            model, exclude_unset=exclude_unset, exclude_defaults=exclude_defaults
        )
        with target.open("w") as f:
            f.write(code)
    else:
        raise ValueError(f"Unsupported file type: {target.suffix}")


class Config(pydantic.BaseModel, extra="forbid"):
    """Command line configuratio nobject"""

    source: Path
    target: Path
    model: str
    yaml_default_flow_style: bool
    exclude_defaults: bool = False
    include_unset: bool = False

    @classmethod
    def from_cli(cls) -> Self:
        parser = argparse.ArgumentParser(
            "Convert Pydantic models between different python, json and yaml."
        )
        parser.add_argument("source", type=str, help="The file to convert from.")
        parser.add_argument("target", type=str, help="The file to convert to.")
        parser.add_argument(
            "--model",
            type=str,
            default=None,
            help=(
                "The model: Either the dot-separated import path for the pydantic "
                "Model that we want to load or, for python files, the name of the "
                "variable where the model is stored inside of the file."
            ),
        )
        parser.add_argument(
            "--exclude-defaults",
            action="store_true",
            help="Exclude fields that have default values.",
        )
        parser.add_argument(
            "--include-unset",
            action="store_true",
            help="Also include fields that have no values set.",
        )
        parser.add_argument(
            "--yaml-default-flow-style",
            action="store_true",
            help="Use the default flow style for yaml.",
        )
        return cls(**vars(parser.parse_args()))


if __name__ == "__main__":
    config = Config.from_cli()
    model = load(config.source, model=config.model)
    write(
        config.target,
        model=model,
        exclude_defaults=config.exclude_defaults,
        exclude_unset=not config.include_unset,
        yaml_options={"default_flow_style": config.yaml_default_flow_style},
    )
