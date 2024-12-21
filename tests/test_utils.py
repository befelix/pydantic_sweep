import pytest

from pydantic_sweep.utils import (
    merge_configs,
    nested_dict_at,
    nested_dict_from_items,
    normalize_path,
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


def test_merge_dicts():
    res = dict(a=dict(a=5, b=dict(c=6, y=9)), c=7)
    d1 = dict(a=dict(a=5, b=dict(c=6)))
    d2 = dict(c=7, a=dict(b=dict(y=9)))
    assert merge_configs(d1, d2) == res

    # This is already tested as part of TestUnflattenItems
    with pytest.raises(ValueError):
        merge_configs(dict(a=1), dict(a=2))
    with pytest.raises(ValueError):
        merge_configs(dict(a=dict(a=5)), dict(a=6))
    with pytest.raises(ValueError):
        merge_configs(dict(a=6), dict(a=dict(a=5)))
