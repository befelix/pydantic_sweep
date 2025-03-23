import enum
import runpy
import sys
import tempfile
from pathlib import Path

import pydantic
import pytest

from pydantic_sweep import BaseModel, convert
from pydantic_sweep._generation import model_to_python


class MyEnum(enum.Enum):
    a = "a"
    b = "b"


class Model(BaseModel):
    x: int = 0
    y: str = ""
    z: list = pydantic.Field(default_factory=list)
    a: set = pydantic.Field(default_factory=set)
    b: float = 0.0
    c: dict = pydantic.Field(default_factory=dict)
    d: tuple = ()
    e: Path = Path("")
    f: MyEnum = MyEnum.a


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
            res = runpy.run_path(str(model_file))
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
            Model(e=Path("/home")),
            Model(f=MyEnum.b),
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


@pytest.mark.parametrize("ext", ["json", "yaml", "py"])
def test_conversion(tmp_path, ext):
    submodel = Model(
        x=1,
        y="test",
        z=[1],
        a={1},
        b=1.0,
        c=dict(a=1),
        d=(1,),
        e=Path("/test"),
        f=MyEnum.b,
    )
    model = NestedModel(sub=submodel, hidden_sub=[submodel])
    if ext == "py":
        model_str = "model"
    else:
        model_str = f"{type(model).__module__}.{type(model).__name__}"

    file = tmp_path / f"model.{ext}"
    convert.write(file, model=model)
    assert convert.load(file, model=model_str) == model


def test_conversion_entrypoint(tmp_path, monkeypatch):
    """Ring-conversion between JSON, YAML, and Python files."""
    model = Model(
        x=1,
        y="test",
        z=[1],
        a={1},
        b=1.0,
        c=dict(a=1),
        d=(1,),
        e=Path("/test"),
        f=MyEnum.b,
    )
    model_str = f"{Model.__module__}.{Model.__name__}"
    json_file = tmp_path / "model.json"
    yaml_file = tmp_path / "model.yaml"
    py_file = tmp_path / "model.py"

    convert.write(tmp_path / json_file, model=model)

    modules = dict(sys.modules)
    modules.pop("pydantic_sweep.convert", None)
    monkeypatch.setattr(sys, "modules", modules)

    monkeypatch.setattr(
        "sys.argv", ["", str(json_file), str(yaml_file), "--model", model_str]
    )
    runpy.run_module(
        "pydantic_sweep.convert",
        run_name="__main__",
    )

    monkeypatch.setattr(
        "sys.argv", ["", str(yaml_file), str(py_file), "--model", model_str]
    )
    runpy.run_module(
        "pydantic_sweep.convert",
        run_name="__main__",
    )

    json_file.unlink()
    monkeypatch.setattr(
        "sys.argv", ["", str(py_file), str(json_file), "--model", "model"]
    )
    runpy.run_module(
        "pydantic_sweep.convert",
        run_name="__main__",
    )

    reconstructed_model = convert.load(json_file, model=model_str)
    assert reconstructed_model == model
