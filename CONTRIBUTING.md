# Contributing

The project uses [uv](https://docs.astral.sh/uv/) for its basic setup, 
[ruff](https://docs.astral.sh/ruff) for code-formatting, and
[mypy](https://mypy.readthedocs.io/) for type checks and
[sphinx](https://www.sphinx-doc.org/) for the documentation.

The [CI checks on the main branch](https://github.com/befelix/pydantic_sweep/blob/main/.github/workflows/test.yml)
are the single source of truth for code correctness.

To get a full development setup, you can checkout the repo and run
```bash
uv sync --all-groups
```

You can build the documentation with
```bash
uv run --group doc sphinx-build \
  --jobs 2 \
  --fail-on-warning \
  -b html \
  docs \
  docs/_build/html
```
