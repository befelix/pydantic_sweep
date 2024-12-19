import pydantic
import pytest

from pydantic_sweep.model import (
    BaseModel,
    check_model,
    config_chain,
    config_product,
    config_roundrobin,
    config_zip,
    field,
    initialize,
)


def test_BaseModel():
    class Model(BaseModel):
        x: int

    assert Model(x=5).x == 5

    # Wrong type for x
    with pytest.raises(ValueError):
        Model(x=None)

    # Assign wrong type for x to instantiated model
    model = Model(x=5)
    with pytest.raises(ValueError):
        model.x = None

    # Extra field
    with pytest.raises(ValueError):
        Model(x=5, y=6)


def test_assert_config():
    class A(pydantic.BaseModel):
        x: int

    class Model(BaseModel):
        x: int
        a: A

    with pytest.raises(ValueError):
        check_model(Model)
    with pytest.raises(ValueError):
        check_model(Model(x=5, a=dict(x=6)))

    class B(BaseModel):
        x: int

    class Model2(BaseModel):
        x: int
        a: B

    check_model(Model2)
    check_model(Model2(x=5, a=dict(x=6)))


class TestFinalize:
    def test_basic(self):
        class Model(BaseModel):
            x: int

        assert initialize(Model, [{"x": 5}]) == [Model(x=5)]
        assert initialize(Model(x=6), [{"x": 5}]) == [Model(x=5)]

    def test_partial(self):
        """Test partial instantiation of model."""

        class Model(BaseModel):
            x: int
            y: int

        m = Model(x=5, y=6)
        m1, m2 = initialize(m, [{"x": 10}, {"x": 11}])
        assert m1 == Model(x=10, y=6)
        assert m2 == Model(x=11, y=6)

        # Post-hoc setting of parameters
        m1.y = 10
        assert m2.y == 6
        assert m.y == 6

    def test_copy(self):
        """Make sure we do not share state between models."""

        class Sub(BaseModel):
            x: int = 5

        class Model(BaseModel):
            x: int
            sub: Sub = Sub()

        m1, m2 = initialize(Model, [{"x": 5}, {"x": 6}])
        assert m1.sub is not m2.sub
        m1.sub.x = 10
        assert m2.sub.x == 5

        m1, m2 = initialize(Model(x=10), [{"x": 5}, {"x": 6}])
        assert m1.sub is not m2.sub
        m1.sub.x = 10
        assert m2.sub.x == 5


def test_config_product():
    res = config_product(field("a", [1, 2]), field("b", [3, 4]))
    expected = [dict(a=1, b=3), dict(a=1, b=4), dict(a=2, b=3), dict(a=2, b=4)]
    assert res == expected

    with pytest.raises(ValueError):
        config_product(field("a", [1]), field("a", [2]))


def test_config_zip():
    res = config_zip(field("a", [1, 2]), field("b", [3, 4]))
    assert res == [dict(a=1, b=3), dict(a=2, b=4)]

    # Different lengths
    with pytest.raises(ValueError):
        config_zip(field("a", [1, 2]), field("b", [3]))

    # Same value
    with pytest.raises(ValueError):
        config_zip(field("a", [1, 2]), field("a", [3, 4]))


def test_config_chain():
    res = config_chain(field("a", [1, 2]), field("b", [3, 4]))
    assert res == [dict(a=1), dict(a=2), dict(b=3), dict(b=4)]

    # Same keys should not cause conflicts here
    res = config_chain(field("a", [1]), field("b", [2]))
    assert res == [dict(a=1), dict(b=2)]


def test_config_roundrobin():
    res = config_roundrobin(field("a", [1, 2]), field("b", [3, 4]))
    assert res == [dict(a=1), dict(b=3), dict(a=2), dict(b=4)]

    # Same keys should not cause conflicts here
    res = config_chain(field("a", [1]), field("b", [2]))
    assert res == [dict(a=1), dict(b=2)]
