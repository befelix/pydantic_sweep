import pydantic
import pytest

from pydantic_sweep._model_diff import model_diff


class TestModelDiff:
    def test_none(self):
        assert not model_diff(None, None)

    def test_basic(self):
        class Sub(pydantic.BaseModel):
            x: int = 0
            y: int = 0

        class Model(pydantic.BaseModel):
            sub: Sub = Sub()
            z: str = "hi"

        assert not model_diff(Model(), Model())
        assert model_diff(Sub(), Sub(x=1)) == dict(x=(0, 1))
        assert model_diff(Sub(), Sub(x=1, y=2)) == dict(x=(0, 1), y=(0, 2))
        assert model_diff(Model(), Model(sub=Sub(x=1))) == dict(sub=dict(x=(0, 1)))

    def test_different_models(self):
        class M(pydantic.BaseModel):
            x: int = 0

        class Y(pydantic.BaseModel):
            x: int = 0

        with pytest.raises(ValueError):
            model_diff(M(), Y())

    def test_unhashable(self):
        class Model(pydantic.BaseModel):
            x: list | tuple

        # unhashable
        assert not model_diff(Model(x=[1]), Model(x=[1]))
        assert model_diff(Model(x=(1,)), Model(x=[1])) == dict(x=((1,), [1]))

    def test_different_submodules(self):
        class S1(pydantic.BaseModel):
            x: int = 0

        class S2(pydantic.BaseModel):
            x: int = 0

        class Model(pydantic.BaseModel):
            sub: S1 | S2

        assert model_diff(Model(sub=S1()), Model(sub=S2())) == dict(sub=(S1(), S2()))

    def test_list(self):
        x1 = [0, 1, 2]
        x2 = [0, 99, 2]
        assert model_diff(x1, x2) == {"[1]": (1, 99)}

    def test_dict(self):
        d1 = dict(a="a", b="b", c="c")
        d2 = dict(c="c", b="b", a=0)
        assert model_diff(d1, d2) == {"[a]": ("a", 0)}
