import pytest

from pydantic_sweep.cli import FileCLI, ModelDumpCLI
from pydantic_sweep.testing import CLITests


class TestModelDumpCLI(CLITests):
    @pytest.fixture
    def implementation(self):
        return ModelDumpCLI, {}


class TestFileCLI(CLITests):
    @pytest.fixture
    def implementation(self, tmp_path):
        config = tmp_path / "config.json"
        return FileCLI, {"path": config}
