import abc
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

import pydantic

from pydantic_sweep.types import BaseModelT

__all__ = [
    "CLI",
    "FileCLI",
    "ModelDumpCLI",
]


class CLI(metaclass=abc.ABCMeta):
    @classmethod
    def execute_script(
        cls, script: os.PathLike | str, model: pydantic.BaseModel, **kwargs: Any
    ) -> subprocess.CompletedProcess:
        """Call the CLI interface to load the model."""
        import subprocess

        cli_args = cls.cli_args(model)
        return subprocess.run(
            [sys.executable, str(script), *cli_args], check=True, **kwargs
        )

    @staticmethod
    @abc.abstractmethod
    def cli_args(model: pydantic.BaseModel, /) -> list[str]:
        """Convert the model to a list of CLI arguments."""
        pass

    @staticmethod
    @abc.abstractmethod
    def from_cli(model_cls: type[BaseModelT], /) -> BaseModelT:
        """Load the model from a list of CLI arguments."""
        pass


class ModelDumpCLI(CLI):
    """A CLI Interface that passes a compressed model dump as on the CLI."""

    @staticmethod
    def cli_args(model: pydantic.BaseModel, /) -> list[str]:
        """Dump the model to a list of CLI arguments."""
        import base64
        import gzip

        dump = model.model_dump_json()
        dump_comp = gzip.compress(dump.encode("utf-8"))
        encoded = base64.b64encode(dump_comp).decode("utf-8")
        return [encoded]

    @staticmethod
    def from_cli(model_cls: type[BaseModelT], /) -> BaseModelT:
        """Load the model from a list of CLI arguments."""
        import argparse
        import base64
        import gzip

        parser = argparse.ArgumentParser()
        parser.add_argument("dump", help="Base64-encoded compressed model dump.")
        args = parser.parse_args()

        encoded = args.dump.encode("utf-8")
        dump_comp = base64.b64decode(encoded)
        dump = gzip.decompress(dump_comp).decode("utf-8")
        return model_cls.model_validate_json(dump)


class FileCLI(CLI):
    """A CLI Interface that loads the model from a configuration file."""

    @staticmethod
    def cli_args(model: pydantic.BaseModel, /, *, path: str | os.PathLike) -> list[str]:  # type: ignore[override]
        """Dump the model to a temporary configuration file and return its path."""
        with open(path, "w", encoding="utf-8") as f:
            f.write(model.model_dump_json())
        return [str(path)]

    @staticmethod
    def from_cli(model_cls: type[BaseModelT], /) -> BaseModelT:
        """Load the model from a configuration file specified on the CLI."""
        import argparse

        parser = argparse.ArgumentParser()
        parser.add_argument("file", help="Path to the configuration file.", type=Path)
        args = parser.parse_args()

        file_path = args.file
        if not file_path.is_file():
            raise FileNotFoundError(f"Configuration file not found: {file_path}")

        json_str = file_path.read_text(encoding="utf-8")
        return model_cls.model_validate_json(json_str)
