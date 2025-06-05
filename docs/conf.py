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
author = "Felix Berkenkamp"
release = import_file(MODULE_ROOT / "_version.py").__version__

# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

extensions = [
    "sphinx.ext.napoleon",  # Docstrings
    "sphinx_rtd_theme",  # Theme
    "sphinx.ext.autodoc",  # Source code documentation
    "sphinx.ext.intersphinx",  # Link to external documentation
    "autoapi.extension",  # Automatic API generation
    "sphinx.ext.linkcode",  # Link to Github code
    "myst_nb",  # Executable notebooks
    "sphinx_copybutton",  # Copy code cells
]

nitpicky = True
default_role = "any"
templates_path = ["_templates"]
exclude_patterns = ["_build", "Thumbs.db", ".DS_Store"]

# Add links to other libraries
intersphinx_mapping = {
    "python": ("https://docs.python.org/3", None),
    "more_itertools": ("https://more-itertools.readthedocs.io/en/stable", None),
    "pydantic": ("https://docs.pydantic.dev/latest/", None),
}

nitpick_ignore = [
    ("py:class", "collections.abc.Iterable"),
    ("py:obj", "pydantic.BaseModel"),
    ("py:class", "pydantic.BaseModel"),
    ("py:class", "T"),
    ("py:obj", "T"),
    ("py:class", "Ellipsis"),
    # These are somehow not found
    ("py:class", "pydantic_sweep.types.Config"),
    ("py:class", "pydantic_sweep.types.Path"),
    ("py:class", "pydantic_sweep.types.StrictPath"),
    ("py:class", "pydantic_sweep.types.FieldValue"),
    ("py:class", "pydantic_sweep.types.BaseModelT"),
    ("py:class", "pydantic_sweep.types._FlexibleConfig"),
    ("py:class", "pydantic_sweep.types.FlexibleConfig"),
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


def linkcode_resolve(domain, info):
    """Link to code on Github."""
    # https://www.sphinx-doc.org/en/master/usage/extensions/linkcode.html#module-sphinx.ext.linkcode
    if domain != "py":
        return None
    if not info["module"]:
        return None
    # linkcode is not aware of import in __init__, so need to do some annoying
    # duplication here. Could perhaps be replaced by importing each function and
    # checking `__module__`.
    filename = info["module"].replace(".", "/")
    py_obj_name = info["fullname"]
    if filename.endswith(".types"):
        filename = f"{filename}.py"
    elif py_obj_name == "random_seeds":
        filename = f"{filename}/_utils.py"
    elif py_obj_name == "__version__":
        filename = f"{filename}/_version.py"
    else:
        filename = f"{filename}/_model.py"
    return f"https://github.com/befelix/pydantic_sweep/blob/main/src/{filename}"


# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

html_theme = "sphinx_rtd_theme"
# https://docs.readthedocs.io/en/stable/guides/edit-source-links-sphinx.html
html_context = {
    "display_github": True,
    "github_user": "befelix",
    "github_repo": "pydantic_sweep",
    "github_version": "main",
    "conf_py_path": "/docs/",  # Path in the checkout to the docs root
}
# Do not copy the source code files into the documentation
html_copy_source = False
