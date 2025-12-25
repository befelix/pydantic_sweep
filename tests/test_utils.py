import collections.abc
import dataclasses
import typing
from typing import Annotated, Any, TypeVar

import pydantic
import pytest
import typing_extensions

from pydantic_sweep._utils import (
    RaiseWarnIgnore,
    as_hashable,
    iter_subtypes,
    raise_warn_ignore,
    random_seeds,
)


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
