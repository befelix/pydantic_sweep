import copy

import pytest

from pydantic_sweep._nested_dict import (
    _flexible_config_to_nested,
    merge_nested_dicts,
    nested_dict_at,
    nested_dict_drop,
    nested_dict_from_items,
    nested_dict_get,
    nested_dict_replace,
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


class TestNestedDictReplace:
    def test_inplace(self):
        d = dict(a=5, b=dict(c=6, d=7))
        d_orig = copy.deepcopy(d)
        expected = dict(a=5, b=dict(c=0, d=7))

        nested_dict_replace(d, "b.c", value=0, inplace=True)
        assert d == expected
        assert d_orig != d

    def test_out_of_place(self):
        d = dict(a=5, b=dict(c=6, d=7))
        d_orig = copy.deepcopy(d)
        expected = dict(a=5, b=dict(c=0, d=7))

        res = nested_dict_replace(d, "b.c", value=0)
        assert res == expected
        assert d == d_orig, "In-place modification"

    def test_empty_path(self):
        d = dict(a=5, b=dict(c=6, d=7))
        with pytest.raises(ValueError):
            nested_dict_replace(d, (), value=0)

    def test_missing(self):
        # Replacing non-existing key
        d = dict(a=5, b=dict(a=5))
        with pytest.raises(KeyError):
            nested_dict_replace(d, "b.c", value=0)


class TestNestedDictDrop:
    def test_inplace(self):
        d = dict(a=5, b=dict(c=6, d=7))
        d_orig = copy.deepcopy(d)

        nested_dict_drop(d, "b.c", inplace=True)
        expected = dict(a=5, b=dict(d=7))
        assert d == expected
        assert d_orig != d

    def test_out_of_place(self):
        d = dict(a=5, b=dict(c=6, d=7))
        d_orig = copy.deepcopy(d)

        res = nested_dict_drop(d, "b.c", inplace=False)
        expected = dict(a=5, b=dict(d=7))
        assert res == expected
        assert d == d_orig, "In-place modification"

    def test_empty_path(self):
        d = dict(a=5, b=dict(c=6, d=7))
        with pytest.raises(ValueError):
            nested_dict_drop(d, (), inplace=True)

    def test_missing(self):
        # Dropping non-existing key
        d = dict(a=5, b=dict(a=5))
        with pytest.raises(KeyError):
            nested_dict_drop(d, "b.c", inplace=True)


class TestNestedDictGet:
    def test_basic(self):
        d = dict(a=dict(b=dict(c=5)))

        assert nested_dict_get(d, "a") is d["a"]
        assert nested_dict_get(d, "a.b") is d["a"]["b"]
        assert nested_dict_get(d, "a.b.c") == 5

        with pytest.raises(KeyError):
            nested_dict_get(d, "c")

    def test_empty_path(self):
        d = dict(a=1)
        assert nested_dict_get(d, ()) is d

    def test_non_dict(self):
        d = dict(a=5)
        with pytest.raises(KeyError):
            nested_dict_get(d, "a.b")

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
