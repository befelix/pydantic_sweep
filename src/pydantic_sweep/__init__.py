from importlib.metadata import version

from . import cli, types
from ._model import (
    BaseModel,
    DefaultValue,
    check_model,
    check_unique,
    config_chain,
    config_combine,
    config_product,
    config_roundrobin,
    config_zip,
    field,
    initialize,
    model_replace,
)
from ._model_diff import model_diff
from ._utils import as_hashable, random_seeds

__version__ = version("pydantic-sweep")
del version

__all__ = [
    "BaseModel",
    "DefaultValue",
    "__version__",
    "as_hashable",
    "check_model",
    "check_unique",
    "cli",
    "config_chain",
    "config_combine",
    "config_product",
    "config_roundrobin",
    "config_zip",
    "field",
    "initialize",
    "model_diff",
    "model_replace",
    "random_seeds",
    "types",
]
