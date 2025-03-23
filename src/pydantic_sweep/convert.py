import argparse
import importlib
import os
import runpy
from pathlib import Path
from typing import Any

import pydantic

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
        import json

        with source.open("r") as file:
            content = json.load(file)
        return _import_module(model)(**content)
    elif source.suffix == ".yaml":
        import yaml  # type: ignore[import-untyped]

        with source.open("r") as file:
            content = yaml.safe_load(file)
        return _import_module(model)(**content)
    elif source.suffix == ".py":
        return runpy.run_path(str(source))[model]
    else:
        raise ValueError(f"Unsupported file type: {source.suffix}")


def write(target: os.PathLike | str, /, *, model: pydantic.BaseModel) -> None:
    """Write a model to a file.

    Parameters
    ----------
    target :
        The file to write to. Supported extensions are ``.json``, ``.yaml`` and
        ``.py``.
    model :
        The pydantic model that we want to write to the file.
    """
    target = Path(target)
    if target.exists():
        raise FileExistsError(f"File already exists: {target}")
    if target.suffix == ".json":
        dump = model.model_dump_json()
        with target.open("w") as f:
            f.write(dump)
    elif target.suffix == ".yaml":
        import json

        import yaml

        # This runs serializers properly (e.g., for Path / Enum objects)
        dump = json.loads(model.model_dump_json())
        with target.open("w") as f:
            yaml.dump(dump, f)
    elif target.suffix == ".py":
        code = model_to_python(model)
        with target.open("w") as f:
            f.write(code)
    else:
        raise ValueError(f"Unsupported file type: {target.suffix}")


class Config(pydantic.BaseModel, extra="forbid"):
    """Command line configuratio nobject"""

    source: Path
    target: Path
    model: str


def parse() -> Config:
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

    args = parser.parse_args()
    return Config(source=args.source, target=args.target, model=args.model)


if __name__ == "__main__":
    config = parse()
    model = load(config.source, model=config.model)
    write(config.target, model=model)
