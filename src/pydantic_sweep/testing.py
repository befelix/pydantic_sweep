import pytest

from pydantic_sweep import BaseModel
from pydantic_sweep.cli import CLI


class CLITests:
    @pytest.fixture
    def implementation(self) -> tuple[type[CLI], dict]:
        """This fixture must be overridden in the subclass."""
        raise NotImplementedError("Override this fixture to return your ABC instance")

    def test_cli_roundtrip(
        self, monkeypatch: pytest.MonkeyPatch, implementation: tuple[type[CLI], dict]
    ) -> None:
        """Test that the CLI can roundtrip a model."""

        class Model(BaseModel):
            x: int
            y: float
            z: str

        my_model = Model(x=42, y=3.14, z="test")

        cli, kwargs = implementation
        args = cli.cli_args(my_model, **kwargs)
        monkeypatch.setattr("sys.argv", ["program_name", *args])
        loaded_model = cli.from_cli(Model)
        assert my_model == loaded_model
