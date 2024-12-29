"""Larger integration tests for the overall workflow."""

import pydantic_sweep as ps
from pydantic_sweep import field


def test_basic_class():
    """Basic workflow using a BaseModel."""

    class Model(ps.BaseModel):
        x: int = 6
        y: int = 5
        z: str = "a"

    configs = ps.initialize(
        Model,
        ps.config_product(
            ps.field("z", [ps.DefaultValue, "b"]),
            ps.config_zip(
                ps.field("x", [1, 2]),
                ps.field("y", [3, 4]),
            ),
        ),
    )
    expected = [
        Model(x=1, y=3),
        Model(x=2, y=4),
        Model(x=1, y=3, z="b"),
        Model(x=2, y=4, z="b"),
    ]
    assert configs == expected


def test_basic_instance():
    """Basic workflow using an instance of a model."""

    class Model(ps.BaseModel):
        x: int = 6
        y: int = 5
        z: str = "a"

    configs = ps.initialize(
        Model,
        ps.config_product(
            ps.field("z", [ps.DefaultValue, "b"]),
            ps.config_zip(
                ps.field("x", [1, 2]),
                ps.field("y", [3, 4]),
            ),
        ),
        default=dict(z="new"),
    )
    expected = [
        Model(x=1, y=3, z="new"),
        Model(x=2, y=4, z="new"),
        Model(x=1, y=3, z="b"),
        Model(x=2, y=4, z="b"),
    ]
    assert configs == expected


def test_nested():
    """Test nested model configuration."""

    class Sub1(ps.BaseModel):
        x: int = 5
        z: int = 7

    class Sub2(ps.BaseModel):
        y: int = 6
        z: int = 9

    class Model(ps.BaseModel):
        s: Sub2 | Sub1

    models = ps.initialize(
        Model,
        ps.config_chain(
            ps.initialize(Sub1, field("x", [1, 2]), to="s"),
            ps.initialize(Sub2, field("y", [3]), to="s"),
        ),
    )
    assert models == [Model(s=Sub1(x=1)), Model(s=Sub1(x=2)), Model(s=Sub2(y=3))]
