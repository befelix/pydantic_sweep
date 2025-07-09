# Changelog

This page summarizes historic changes in the library. Please also see the
[release page](https://github.com/befelix/pydantic_sweep/releases)

## 0.3

### 0.3.6

- Fix `model_replace` for Union types

### 0.3.5

- Type hints have improved to avoid false positives on the user side.

### 0.3.4
- `check_model` does not output `unhashable` warnings.
- Added `pydantic_sweep.convert` to convert between json, yaml and Python code
  dumps of pydantic Models. This is also an entrypoint that can be executed as
  `python -m pydantic_sweep.convert source target --model 'path.to.Model'`
- `initialize` now accepts any mixture of `str`, tuple, and dot-separated keys for
  `default` and `constant` values.
- Added a `model_replace` method to create a copy of a pydantic model while
  overwriting certain values.

### 0.3.3
- `check_model` now warns on non-hashable type hints (can be configured)
- `check_model` now explicitly forbids the `arbitrary_types_allowed` pydantic setting.

### 0.3.2

- Fix for Python 3.10
- Add `example` folder
- License documentation and examples under 0BSD

### 0.3.1

- `initialize` accepts nested dictionaries for `default`/`constant` arguments.

### 0.3.0

- `field` now checks that values are hashable by default. This can be disabled by 
  setting `check=False`.
- Added `as_hashable` utility to easily compare different configs and pydantic Models.
- Added `check_unique` utility to check whether models are unique.

## 0.2

### 0.2.1
- `BaseModel` gained a custom model_validator that guards against ambiguous model
  selection from union types in nested models.
- Relaxed version requirements of `pydantic` and `more-itertools`

### 0.2.0

- `DefaultValue` is checked against conflicting settings the same way as normal values
- Passing `DefaultValue` to the `default`/`constant` argument of `initialize` works as
  expected.

## 0.1

- Initial release
