# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

import importlib.util
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parents[1]
MODULE_ROOT = PROJECT_ROOT.joinpath("src", "pydantic_sweep")


def import_file(file: Path, /):
    """Import a file directly."""
    assert file.exists()
    spec = importlib.util.spec_from_file_location(file.stem, file)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


sys.path.append(str(PROJECT_ROOT))


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
    "myst_parser",
    "sphinx_rtd_theme",
    "autoapi.extension",
]

templates_path = ["_templates"]
exclude_patterns = ["_build", "Thumbs.db", ".DS_Store"]

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

# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

html_theme = "sphinx_rtd_theme"
html_static_path = ["_static"]
