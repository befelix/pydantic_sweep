import pytest

from pydantic_sweep.utils import (
    _normalize_path,
    config_product,
    config_zip,
    field,
    merge_configs,
    paths_to_dict,
)


def test_normalize_path():
    path = ("a", "A_", "b0", "__C")
    assert _normalize_path(path) == path
    assert _normalize_path("a.A_.b0.__C") == path

    with pytest.raises(ValueError):
        _normalize_path("a,b")
    with pytest.raises(ValueError):
        _normalize_path(".")
    with pytest.raises(ValueError):
        _normalize_path("a.b.")
    with pytest.raises(ValueError):
        _normalize_path("a..b")
    with pytest.raises(ValueError):
        _normalize_path(".a.b")

    with pytest.raises(ValueError):
        _normalize_path(("a", "2"))
    with pytest.raises(ValueError):
        _normalize_path(("a.b",))
    with pytest.raises(ValueError):
        _normalize_path(("0a.b",))


class TestPathsToDict:
    def test_functionality(self):
        d = {("a", "a"): 5, ("a", "b", "c"): 6, "c": 7}
        res = dict(a=dict(a=5, b=dict(c=6)), c=7)
        assert paths_to_dict(d.items()) == res

    def test_duplicate_key(self):
        with pytest.raises(ValueError):
            paths_to_dict([("a", 1), ("a", 1)])
        with pytest.raises(ValueError):
            paths_to_dict([("a.a", 1), ("a.a", 1)])

    def test_parent_overwrite(self):
        with pytest.raises(ValueError):
            paths_to_dict([("a.a", 5), ("a", 6)])
        with pytest.raises(ValueError):
            paths_to_dict([("a.a.a", 5), ("a", 6)])
        with pytest.raises(ValueError):
            paths_to_dict([("a.a.a", 5), ("a.a", 6)])

    def test_child_overwrite(self):
        with pytest.raises(ValueError):
            paths_to_dict([("a", 6), ("a.a", 5)])
        with pytest.raises(ValueError):
            paths_to_dict([("a", 6), ("a.a", 5)])
        with pytest.raises(ValueError):
            paths_to_dict([("a.a", 6), ("a.a.a", 5)])


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
