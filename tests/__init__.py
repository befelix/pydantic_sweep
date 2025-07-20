from importlib.metadata import version

import pydantic_sweep as ps


def test_version():
    assert isinstance(ps.__version__, str)
    _, _, _ = ps.__version__.split(".")
    assert ps.__version__ == version("pydantic-sweep")
