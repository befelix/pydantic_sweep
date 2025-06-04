import collections.abc
import copy
import dataclasses
import typing
from typing import Annotated, Any, TypeVar

import pydantic
import pytest
import typing_extensions

from pydantic_sweep._utils import (
    RaiseWarnIgnore,
    _flexible_config_to_nested,
    as_hashable,
    iter_subtypes,
    merge_nested_dicts,
    model_diff,
    nested_dict_at,
    nested_dict_from_items,
    nested_dict_get,
    nested_dict_replace,
    normalize_path,
    raise_warn_ignore,
    random_seeds,
)


def test_normalize_path():
    path = ("a", "A_", "b0", "__C")
    assert normalize_path(path) == path
    assert normalize_path("a.A_.b0.__C") == path

    with pytest.raises(ValueError):
        normalize_path("a,b")
    with pytest.raises(ValueError):
        normalize_path(".")
    with pytest.raises(ValueError):
        normalize_path("a.b.")
    with pytest.raises(ValueError):
        normalize_path("a..b")
    with pytest.raises(ValueError):
        normalize_path(".a.b")

    with pytest.raises(ValueError):
        normalize_path(("a", "2"), check_keys=True)
    with pytest.raises(ValueError):
        normalize_path(("a.b",), check_keys=True)
    with pytest.raises(ValueError):
        normalize_path(("0a.b",), check_keys=True)


class TestNormalizeFlexibleConfig:
    def test_basic(self):
        assert _flexible_config_to_nested(dict(a=1, b=2)) == dict(a=1, b=2)
        assert _flexible_config_to_nested({"a.b": 1}) == dict(a=dict(b=1))
        assert _flexible_config_to_nested({("a", "b"): 1}) == dict(a=dict(b=1))
        assert _flexible_config_to_nested(dict(a={"b.c": 1})) == dict(
            a=dict(b=dict(c=1))
        )

    def test_nested(self):
        assert _flexible_config_to_nested({"a.b.c": 1, "a.b.d": 2}) == dict(
            a=dict(b=dict(c=1, d=2))
        )
        assert _flexible_config_to_nested({"a.b.c": 1, "a.b.d.e": 2}) == dict(
            a=dict(b=dict(c=1, d=dict(e=2)))
        )

    def test_conflicts(self):
        with pytest.raises(ValueError):
            _flexible_config_to_nested({"a.b": 1, "a": 2})
        with pytest.raises(ValueError):
            _flexible_config_to_nested({"a": dict(b=1), "a.b": 2})
        with pytest.raises(ValueError):
            _flexible_config_to_nested({"a.b.c": 1, "a.b.c.d": 2})

    def test_skip(self):
        assert _flexible_config_to_nested({"a.c": None, "a.b": 2}, skip=None) == dict(
            a=dict(b=2)
        )


class TestNestedDictFromItems:
    def test_functionality(self):
        d = {("a", "a"): 5, ("a", "b", "c"): 6, "c": 7}
        res = dict(a=dict(a=5, b=dict(c=6)), c=7)
        assert nested_dict_from_items(d.items()) == res

    def test_duplicate_key(self):
        with pytest.raises(ValueError):
            nested_dict_from_items([("a", 1), ("a", 1)])
        with pytest.raises(ValueError):
            nested_dict_from_items([("a.a", 1), ("a.a", 1)])

    def test_parent_overwrite(self):
        with pytest.raises(ValueError):
            nested_dict_from_items([("a.a", 5), ("a", 6)])
        with pytest.raises(ValueError):
            nested_dict_from_items([("a.a.a", 5), ("a", 6)])
        with pytest.raises(ValueError):
            nested_dict_from_items([("a.a.a", 5), ("a.a", 6)])

    def test_child_overwrite(self):
        with pytest.raises(ValueError):
            nested_dict_from_items([("a", 6), ("a.a", 5)])
        with pytest.raises(ValueError):
            nested_dict_from_items([("a", 6), ("a.a", 5)])
        with pytest.raises(ValueError):
            nested_dict_from_items([("a.a", 6), ("a.a.a", 5)])


def test_nested_dict_at():
    res = nested_dict_at("a.b.c", 5)
    assert res == dict(a=dict(b=dict(c=5)))


def test_nested_dict_replace():
    d = dict(a=5, b=dict(c=6, d=7))
    d_orig = copy.deepcopy(d)
    expected = dict(a=5, b=dict(c=0, d=7))

    res = nested_dict_replace(d, "b.c", value=0)
    assert res == expected
    assert d == d_orig, "In-place modification"


class TestNestedDictGet:
    def test_basic(self):
        d = dict(a=dict(b=dict(c=5)))

        assert nested_dict_get(d, "a") is d["a"]
        assert nested_dict_get(d, "a.b") is d["a"]["b"]
        assert nested_dict_get(d, "a.b.c") == 5

        with pytest.raises(KeyError):
            nested_dict_get(d, "c")

    def test_leaf(self):
        d = dict(a=dict(b=2))
        nested_dict_get(d, "a", leaf=False)
        nested_dict_get(d, "a.b", leaf=True)

        with pytest.raises(ValueError):
            nested_dict_get(d, "a", leaf=True)
        with pytest.raises(ValueError):
            nested_dict_get(d, "a.b", leaf=False)


def test_merge_dicts():
    res = dict(a=dict(a=5, b=dict(c=6, y=9)), c=7)
    d1 = dict(a=dict(a=5, b=dict(c=6)))
    d2 = dict(c=7, a=dict(b=dict(y=9)))
    assert merge_nested_dicts(d1, d2) == res

    # This is already tested as part of TestUnflattenItems
    with pytest.raises(ValueError):
        merge_nested_dicts(dict(a=1), dict(a=2))
    with pytest.raises(ValueError):
        merge_nested_dicts(dict(a=dict(a=5)), dict(a=6))
    with pytest.raises(ValueError):
        merge_nested_dicts(dict(a=6), dict(a=dict(a=5)))

    assert merge_nested_dicts(dict(a=1), dict(b=2), overwrite=True) == dict(a=1, b=2)
    assert merge_nested_dicts(dict(a=1), dict(a=2), overwrite=True) == dict(a=2)
    assert merge_nested_dicts(dict(a=dict(b=2)), dict(a=3), overwrite=True) == dict(a=3)


class TestAsHashable:
    def test_builtins(self):
        hash(as_hashable(None)) == hash(None)
        hash(as_hashable((1, 2))) == hash((1, 2))

    def test_dict(self):
        hash(as_hashable(dict(a=dict(b=2))))
        assert as_hashable(dict(a=1, b=2)) == as_hashable(dict(b=2, a=1))

        res1 = as_hashable(dict(a=1, b=dict(c=2)))
        res2 = as_hashable(dict(b=dict(c=2), a=1))
        assert res1 == res2

        assert as_hashable(dict(a=1)) != as_hashable(dict(a=2))
        assert as_hashable(dict(a=dict(b=1))) != as_hashable(dict(b=dict(a=1)))
        assert as_hashable([1, 2]) != as_hashable((1, 2))

    def test_pydantic(self):
        class Sub(pydantic.BaseModel):
            x: int

        class Model(pydantic.BaseModel):
            a: int
            sub: Sub

        hash(as_hashable(dict(a=1, b=dict(c=2))))
        hash(as_hashable(dict(a=1, b=Model(a=1, sub=Sub(x=1)))))

        class Model(pydantic.BaseModel):
            a: int
            b: int

        assert as_hashable(Model(a=1, b=2)) == as_hashable(Model(b=2, a=1))

        class Model1(pydantic.BaseModel):
            x: int

        class Model2(pydantic.BaseModel):
            x: int

        assert as_hashable(Model1(x=1)) != as_hashable(Model2(x=1))
        assert as_hashable(Model1(x=1)) != as_hashable(dict(x=1))

    def test_set(self):
        hash(as_hashable(set([1, 2])))
        assert as_hashable({1, 2}) == as_hashable({1, 2})
        assert as_hashable({1, 2}) != as_hashable((1, 2))

    def test_exception(self):
        @dataclasses.dataclass
        class Test:
            x: int

        t = Test(x=5)

        with pytest.raises(TypeError):
            as_hashable(t)


def test_random_seeds():
    assert set(random_seeds(10, upper=10)) == set(range(10))
    with pytest.raises(ValueError):
        random_seeds(-1)
    with pytest.raises(ValueError):
        random_seeds(1, upper=0)


def test_raise_warn_ignore():
    class CustomException(Exception):
        pass

    class CustomWarning(UserWarning):
        pass

    raise_warn_ignore("blub", action="ignore")
    with pytest.raises(CustomException, match="blub1"):
        raise_warn_ignore("blub1", action="raise", exception=CustomException)
    with pytest.warns(CustomWarning, match="blub2"):
        raise_warn_ignore("blub2", action="warn", warning=CustomWarning)

    with pytest.raises(ValueError, match="raise, warn, ignore"):
        raise_warn_ignore("blub", action="OWEH")

    raise_warn_ignore("blub", action=RaiseWarnIgnore.IGNORE)


def subtypes(x) -> set:
    return set(iter_subtypes(x))


class TestIterSubtypes:
    def test_basic(self):
        assert subtypes(float) == {float}
        assert subtypes(int) == {int}
        assert subtypes(None) == {None}

        class Test(list):
            """Custom type"""

        assert subtypes(Test) == {Test}
        assert subtypes(collections.abc.Sequence[str]) == {
            collections.abc.Sequence,
            str,
        }

    def test_old(self):
        assert subtypes(typing.Dict) == {dict}  # noqa: UP006
        assert subtypes(typing.List) == {list}  # noqa: UP006
        assert subtypes(typing.List[typing.Dict]) == {list, dict}  # noqa: UP006
        assert subtypes(typing.Sequence[str]) == {collections.abc.Sequence, str}  # noqa: UP006, RUF100

    def test_final(self):
        assert subtypes(typing.Final[str]) == {str}
        assert subtypes(typing_extensions.Final[str]) == {str}

    def test_generic(self):
        T = TypeVar("T", bound=str | int)
        assert subtypes(T) == {str, int}
        T = TypeVar("T", str, int)
        assert subtypes(T) == {str, int}
        assert subtypes(T | float) == {str, int, float}
        T = TypeVar("T")
        assert subtypes(T) == {Any}

    def test_alias(self):
        assert subtypes(list[str]) == {list, str}
        assert subtypes(list[str | float]) == {list, str, float}
        assert subtypes(list[str | float]) == {list, str, float}
        assert subtypes(set[tuple[str] | tuple[float, ...]]) == {set, tuple, str, float}

    def test_generic_alias(self):
        T = TypeVar("T")
        assert subtypes(list[T]) == {list, typing.Any}
        T = TypeVar("T", str, float)
        assert subtypes(list[T]) == {list, str, float}

    def test_annotated(self):
        assert subtypes(Annotated[int, "blub"]) == {int}
        assert subtypes(Annotated[int | Annotated[float, "s"], "blub"]) == {int, float}

    def test_literal(self):
        assert subtypes(typing.Literal["test", 1]) == {str, int}
        assert subtypes(typing_extensions.Literal["test", 1]) == {str, int}


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
