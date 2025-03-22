import runpy
import tempfile
from pathlib import Path

import pydantic
import pytest

from pydantic_sweep import BaseModel
from pydantic_sweep._generation import model_to_python


class Model(BaseModel):
    x: int = 0
    y: str = ""
    z: list = pydantic.Field(default_factory=list)
    a: set = pydantic.Field(default_factory=set)
    b: float = 0.0
    c: dict = pydantic.Field(default_factory=dict)
    d: tuple = ()


class NestedModel(BaseModel):
    sub: Model = Model()
    hidden_sub: list[Model] = pydantic.Field(default_factory=list)


class TestModelToPython:
    def _eval(self, s: str, /):
        """Write code to file, execute with runpy, and return model."""
        with tempfile.TemporaryDirectory() as tmpdir:
            model_file = Path(tmpdir) / "model.py"
            with open(model_file, "w") as f:
                f.write(s)
            res = runpy.run_path(model_file)
        return res["model"]

    def _test_generation(self, model: pydantic.BaseModel, /, **kwargs):
        code = model_to_python(model, **kwargs)
        model_reconstructed = self._eval(code)
        assert model_reconstructed == model
        return code

    def test_local(self):
        class Model(BaseModel):
            x: int

        with pytest.raises(ValueError):
            model_to_python(Model(x=1))

    @pytest.mark.parametrize(
        "model",
        [
            Model(x=1),
            Model(y="test"),
            Model(x=1, y="test"),
            Model(z=[1]),
            Model(a={1}),
            Model(b=1.0),
            Model(c=dict(a=1)),
            Model(d=(1,)),
        ],
    )
    def test_basic(self, model: Model):
        self._test_generation(model)

    def test_nested(self):
        self._test_generation(NestedModel())
        self._test_generation(NestedModel(sub=Model(x=5)))

    def test_nested_hidden(self):
        self._test_generation(NestedModel(hidden_sub=[Model(x=1)]))
        self._test_generation(
            NestedModel(hidden_sub=[Model(x=1, c=dict(a=5), a={1, "a"})])
        )
