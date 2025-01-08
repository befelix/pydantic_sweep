# Changelog

This page summarizes historic changes in the library. Please also see the
[release page](https://github.com/befelix/pydantic_sweep/releases)

## 0.3

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
