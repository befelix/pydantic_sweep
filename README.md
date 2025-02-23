# pydantic-sweep

`pydantic_sweep` is a library to programmatically, safely and flexibly define 
complex parameter sweeps over `pydantic` models in Python. 

![PyPI - Version](https://img.shields.io/pypi/v/pydantic-sweep)
![Static Badge](https://img.shields.io/badge/python-3.10%20%7C%203.11%20%7C%203.12%20%7C%203.13-blue)
![GitHub branch check runs](https://img.shields.io/github/check-runs/befelix/pydantic_sweep/main)
![GitHub License](https://img.shields.io/github/license/befelix/pydantic_sweep)

**Highlights**:
- Specify parameter sweeps in Python
- Flexibility: specify complex parameter combinations by chaining simple functional operations
- Safety checks for parameter combinations (get meaningful errors early)
- `pydantic` field validation

For example, the following code will instantiate models with `(x=5, sub=Sub1(s=1)` and 
`(x=6, sub=Sub1(s=2)` and try each of those with seed values of `seed=43` and 
`seed=44`, leading to four different configurations:

```python
import pydantic_sweep as ps

class Sub1(ps.BaseModel):
    s: int = 5

class Sub2(ps.BaseModel):
    y: str = "hi"

class Model(ps.BaseModel):
    seed: int = 42
    x: int = 5
    sub: Sub1 | Sub2

# We want to test across two seeds
configs = ps.config_product(
    ps.field("seed", [43, 44]),
    # And two specific Sub1 and `x` combinations
    ps.config_zip(
        ps.field("x", [ps.DefaultValue, 6]),
        ps.field("sub.s", [1, 2]),
    )
)
# This includes safety checks that Sub1 / Sub2 are uniquely specified
models = ps.initialize(Model, configs)

# The code above is equivalent to
models_manual = [
    Model(seed=43, sub=Sub1(s=1)),
    Model(seed=43, x=6, sub=Sub1(s=2)), 
    Model(seed=44, sub=Sub1(s=1)),
    Model(seed=44, x=6, sub=Sub1(s=2)), 
]
assert models == models_manual

# We can also check that we didn't accidentally duplicate a setting
ps.check_unique(models)
```

While in this toy example, manually specifying the combinations may still be viable, 
the library allows infinitely combining different configs and sub-models, making it 
a powerful tool for large-scale experiment definition.
To learn mode about the capabilities of the library please visit the
[documentation page](https://pydantic-sweep.readthedocs.io).

## Installation

You can install the library by checking out the repo and running

```bash
pip install 'pydantic-sweep'
```

## License

The main code-base is licensed under MPL-2.0 a weak copy-left license that allows 
commercial use. See the 
[license file](https://github.com/befelix/pydantic_sweep/blob/main/docs/LICENSE) for 
the exact clauses and
[this FAQ](https://www.mozilla.org/en-US/MPL/2.0/FAQ/) for a high-level description.

An exception from this are the documentation in the `docs` and `example` folders  as
well as this `README` file, which are licensed under the
[0BSD](https://github.com/befelix/pydantic_sweep/blob/main/docs/LICENSE): a highly 
permissive license that does not require attribution. That way, you are free to copy & 
paste example code into your use-case. See 
[here](https://choosealicense.com/licenses/0bsd/) for a high-level description.
