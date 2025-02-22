from typing import Annotated

import pydantic
import pytest
from pydantic import Discriminator, Tag

from pydantic_sweep._model import (
    BaseModel,
    DefaultValue,
    check_model,
    check_unique,
    config_chain,
    config_product,
    config_roundrobin,
    config_zip,
    field,
    initialize,
)


class TestBaseModel:
    def test_config(self):
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

    def test_validation(self):
        class Sub1(BaseModel):
            x: pydantic.StrictInt | pydantic.StrictFloat
            y: int = 5

        class Sub2(BaseModel):
            x: pydantic.StrictInt

        class Model(BaseModel):
            sub: Annotated[Sub1 | Sub2, "Select them automatically"]

        with pytest.raises(pydantic.ValidationError):
            Model(sub=dict(x=1))

        # These should work, since they uniquely identify Sub1
        assert Model(sub=dict(x=1, y=2)) == Model(sub=Sub1(x=1, y=2))
        assert Model(sub=dict(x=1.0)) == Model(sub=Sub1(x=1.0))

    def test_validation_discriminator(self):
        class Sub1(BaseModel):
            x: int

        class Sub2(BaseModel):
            x: int

        class DiscModel(BaseModel):
            sub: Annotated[
                Annotated[Sub1, Tag("sub1")] | Annotated[Sub2, Tag("sub2")],
                Discriminator(lambda *args: "sub2"),
            ]

        assert DiscModel(sub=dict(x=1)) == DiscModel(sub=Sub2(x=1))

    def test_validation_dict(self):
        # This is strongly discouraged, but the validator should still works
        class Model(BaseModel):
            d: dict[str, int] | int

        Model(d=dict(x=1))

        # This is unsafe and shouldn't
        class Sub(BaseModel):
            x: int

        # Best match should prefer the pydantic Basemodel
        class Model(BaseModel):
            d: dict[str, float] | Sub

        assert Model(d=dict(x=1.0)) == Model(d=Sub(x=1.0))


class TestCheckModel:
    def test_nested_fail(self):
        class A(pydantic.BaseModel):
            x: int

        class Model(BaseModel):
            x: int
            a: A

        with pytest.raises(ValueError):
            check_model(Model)
        with pytest.raises(ValueError):
            check_model(Model(x=5, a=dict(x=6)))

    def test_nested_pass(self):
        class B(BaseModel):
            x: int

        class Model2(BaseModel):
            x: int
            a: B

        check_model(Model2)
        check_model(Model2(x=5, a=dict(x=6)))

    def test_union_types(self):
        class A(BaseModel):
            x: int

        class B(BaseModel):
            x: int

        class Nested(BaseModel):
            s: A | B

        check_model(Nested)

        class Nested(BaseModel):
            s: A | pydantic.BaseModel

        with pytest.raises(ValueError):
            check_model(Nested)

    def test_arbitrary(self):
        class A(pydantic.BaseModel, extra="forbid"):
            x: int = 5

        check_model(A)
        check_model(A())

        A.model_config["arbitrary_types_allowed"] = True

        with pytest.raises(ValueError):
            check_model(A)
        with pytest.raises(ValueError):
            check_model(A())

    def test_non_hashable(self):
        """Note: mutable types are not hashable."""
        class A(BaseModel):
            x: set

        class B(BaseModel):
            a: A

        check_model(A, unhashable="ignore")
        check_model(B, unhashable="ignore")
        with pytest.warns(UserWarning, match="`a.x`"):
            check_model(B)
        with pytest.raises(ValueError, match="`a.x`"):
            check_model(B, unhashable="raise")

        class A(BaseModel):
            y: list

        with pytest.warns(UserWarning, match="`y`"):
            check_model(A, unhashable="warn")


class TestField:
    def test_invalid_path(self):
        with pytest.raises(ValueError):
            field("a-b", [1])

    def test_basic(self):
        assert field("a", []) == []
        assert field("a", [1, 2]) == [dict(a=1), dict(a=2)]
        assert field("a.b", [1]) == [dict(a=dict(b=1))]
        assert field(("a", "b"), [1]) == [dict(a=dict(b=1))]

    def test_default_value(self):
        class Model(BaseModel):
            x: int = 5

        res = initialize(Model, field("x", [1, DefaultValue, 2]))
        assert res[0].x == 1
        assert res[1].x == 5
        assert res[2].x == 2

        with pytest.raises(TypeError):
            DefaultValue()
        with pytest.raises(TypeError):

            class Test(DefaultValue):
                pass

        assert str(DefaultValue) == "DefaultValue"

    def test_check(self):
        with pytest.raises(ValueError):
            field("a", [dict(a=1)])

        res = field("a", [dict(a=1)], check=False)
        assert res == [dict(a=dict(a=1))]

    def test_iterator_values(self):
        res = field("a", iter(range(2)), check=True)
        assert res == [dict(a=0), dict(a=1)]


class TestInitialize:
    def test_basic(self):
        class Model(BaseModel):
            x: int

        assert initialize(Model, [{"x": 5}]) == [Model(x=5)]

    def test_partial(self):
        """Test partial instantiation of model."""

        class Model(BaseModel):
            x: int
            y: int = 6

        m = Model(x=100)
        m1, m2 = initialize(Model, [{"x": 10}, {"x": 11}])
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

        m1, m2 = initialize(Model, [{"x": 5}, {"x": 6}], default=dict(x=10))
        assert m1.sub is not m2.sub
        m1.sub.x = 10
        assert m2.sub.x == 5

    def test_default(self):
        class Sub(BaseModel):
            x: int

        class Model(BaseModel):
            sub: Sub
            y: int = 0

        res = initialize(Model, field("sub.x", [1]), default=dict(y=10))
        assert res == [Model(sub=Sub(x=1), y=10)]

        # Default as default value should not have any effect
        res = initialize(Model, field("sub.x", [1]), default=dict(y=DefaultValue))
        assert res == [Model(sub=Sub(x=1), y=0)]

        res = initialize(
            Model,
            field("sub.x", [DefaultValue]),
            constant=dict(y=10),
            default={"sub.x": 99},
        )
        assert res == [Model(sub=Sub(x=99), y=10)]

        res = initialize(
            Model,
            field("sub.x", [DefaultValue]),
            constant=dict(y=10),
            default=dict(sub=dict(x=99)),
        )
        assert res == [Model(sub=Sub(x=99), y=10)]

    def test_constant(self):
        class Sub(BaseModel):
            x: int

        class Model(BaseModel):
            sub: Sub
            y: int = 0

        res = initialize(Model, field("sub.x", [1]), constant=dict(y=10))
        assert res == [Model(sub=Sub(x=1), y=10)]

        res = initialize(Model, field("sub.x", [1]), constant=dict(y=DefaultValue))
        assert res == [Model(sub=Sub(x=1), y=0)]

        res = initialize(Model, field("sub.x", [1, 2]), constant=dict(y=10))
        assert res == [Model(sub=Sub(x=1), y=10), Model(sub=Sub(x=2), y=10)]

        res = initialize(Model, [dict()], constant={"sub.x": 0})
        assert res == [Model(sub=Sub(x=0))]

        # Provide nested diction config for constant
        res = initialize(Model, [dict()], constant=dict(sub=dict(x=0)))
        assert res == [Model(sub=Sub(x=0))]

        with pytest.raises(TypeError):
            initialize(Model, [], constant=[5])

        with pytest.raises(ValueError):
            initialize(Model, field("sub.x", [1]), constant={"sub.x": 2})

        # Also DefaultValue should conflict here
        with pytest.raises(ValueError):
            initialize(Model, field("sub.x", [1]), constant={"sub.x": DefaultValue})

    def test_to(self):
        class Sub(BaseModel):
            x: int = 5

        values = field("x", [0, 1])
        assert initialize(Sub, values, to="a.b") == field(
            "a.b", initialize(Sub, values)
        )

        sub = initialize(Sub, field("x", [0]), to="s")
        assert sub == field("s", [Sub(x=0)])

        class Model(BaseModel):
            s: Sub

        model = initialize(Model, sub)
        assert model == [Model(s=Sub(x=0))]

    def test_at(self):
        class Sub(BaseModel):
            x: int

        class Model(BaseModel):
            sub: Sub

        values = field("sub.x", [0])
        partial = initialize(Sub, values, at="sub")
        assert partial == [dict(sub=Sub(x=0))]

    def test_conflicing_args(self):
        class Sub(BaseModel):
            x: int

        initialize(Sub, [dict(x=1)])
        with pytest.raises(ValueError):
            initialize(Sub, [dict(x=1)], at="sub", to="sub")


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


def test_default_override():
    """Make sure default values cannot be overwritten."""
    with pytest.raises(ValueError):
        config_product(
            field("a", [DefaultValue]),
            field("a", [DefaultValue]),
        )

    with pytest.raises(ValueError):
        config_product(
            field("a", [1.0]),
            field("a", [DefaultValue]),
        )


def test_check_unique():
    xs = field("a", [1, 2])
    assert check_unique(xs, raise_exception=False)
    assert not check_unique(xs, xs, raise_exception=False)
    assert not check_unique([*xs, *xs], raise_exception=False)

    class Sub(BaseModel):
        x: int = 0

    class Model(BaseModel):
        sub: Sub = Sub()
        y: int = 0

    assert check_unique(
        [Model(), Model(sub=Sub(x=1)), Model(y=1)], raise_exception=False
    )
    assert not check_unique(
        [Model(y=1), Model(sub=Sub(x=1)), Model(y=1)], raise_exception=False
    )

    with pytest.raises(ValueError):
        check_unique([Model(y=0), Model(y=0)])
    check_unique([Model(y=0)])

    class Sub2(Sub):
        pass

    # These should be marked as unique, since they are different model classes
    check_unique([Model(sub=Sub()), Model(sub=Sub2())])

    # Check individual models
    check_unique(Model(y=0))
    check_unique(Model(y=0), Model(y=1))
    with pytest.raises(ValueError):
        check_unique(Model(), Model())
