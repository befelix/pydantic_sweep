# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

import importlib.util
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parents[1]
MODULE_ROOT = PROJECT_ROOT.joinpath("src", "pydantic_sweep")

sys.path.append(str(PROJECT_ROOT))


def import_file(file: Path, /):
    """Import a file directly."""
    assert file.exists()
    spec = importlib.util.spec_from_file_location(file.stem, file)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information

project = "pydantic_sweep"
copyright = "2024, Felix Berkenkamp"
author = "Felix Berkenkamp"
release = import_file(MODULE_ROOT / "_version.py").__version__

# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

extensions = [
    "sphinx.ext.napoleon",
    "sphinx_rtd_theme",
    "sphinx.ext.autodoc",
    "sphinx.ext.intersphinx",
    "autoapi.extension",
    "myst_nb",
]

nitpicky = True
default_role = "any"
templates_path = ["_templates"]
exclude_patterns = ["_build", "Thumbs.db", ".DS_Store"]

# intersphinx_mapping = {
#     "python": ("https://docs.python.org/3", None),
#     "collections": ("https://docs.python.org/3/library/collections", None),
# }

nitpick_ignore = [
    ("py:class", "collections.abc.Iterable"),
    ("py:obj", "pydantic.BaseModel"),
    ("py:class", "pydantic.BaseModel"),
    ("py:class", "T"),
    ("py:obj", "T"),
    ("py:class", "Ellipsis"),
    # These are somehow not found
    ("py:class", "pydantic_sweep.types.ModelType"),
    ("py:class", "pydantic_sweep.types.Config"),
    ("py:class", "pydantic_sweep.types.Path"),
    ("py:class", "pydantic_sweep.types.StrictPath"),
]
napoleon_use_rtype = False

autoapi_dirs = ["../src/pydantic_sweep"]
autoapi_options = [
    "members",
    "undoc-members",
    # "private-members",
    "show-inheritance",
    "show-module-summary",
    "special-members",
    "imported-members",
]
autoapi_root = "autoapi"
autoapi_keep_files = False
keep_warnings = True
autodoc_typehints = "signature"

# Notebook formatting
source_suffix = {
    ".rst": "restructuredtext",
    ".ipynb": "myst-nb",
    ".myst": "myst-nb",
}
# Note: Multi-suffixes like .pct.py will be supported in myst-nb>1.1.2
nb_custom_formats = {
    ".pctpy": ["jupytext.reads", {"fmt": "py:percent"}],
}
nb_execution_in_temp = True
nb_execution_allow_errors = False

# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

html_theme = "sphinx_rtd_theme"
