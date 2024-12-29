# pydantic-sweep

`pydantic_sweep` is a library to programmatically, safely and flexibly define 
complex parameter sweeps over `pydantic` models in Python. 

![PyPI - Version](https://img.shields.io/pypi/v/pydantic-sweep)
![Static Badge](https://img.shields.io/badge/python-3.10%20%7C%203.11%20%7C%203.12%20%7C%203.13-blue)
![GitHub branch check runs](https://img.shields.io/github/check-runs/befelix/pydantic_sweep/main)
![GitHub License](https://img.shields.io/github/license/befelix/pydantic_sweep)

**Highlights**:
- Specify parameter sweeps in Python
- Flexibility: specify complex parameter combinations by chaining simple operations
- Safety checks for parameter combinations (get meaningful errors early)
- `pydantic` field validation

For example, the following code will instantiate models with `(x=5, y=1)` and 
(`x=6, y=2)` and try each of those with seed values of `seed=43` and `seed=44`, 
leading to four different configurations:

```python
import pydantic_sweep as ps

class Model(ps.BaseModel):
    seed: int = 42
    x: int = 5
    y: int

models = ps.initialize(
    Model, 
    ps.config_product(
        ps.field("seed", [43, 44]),
        ps.config_zip(
            ps.field("x", [ps.DefaultValue, 6]),
            ps.field("y", [1, 2]),
        )
    )
)

# The code above is equivalent to
models = [
    Model(seed=43, x=5, y=1), 
    Model(seed=43, x=6, y=2), 
    Model(seed=44, x=5, y=1), 
    Model(seed=44, x=6, y=2),
]
```

To learn mode about the full capabilities of the library visit the
[documentation page](https://berkenkamp.me/pydantic_sweep/).

## Installation

You can install the library by checking out the repo and running

```bash
pip install 'pydantic_sweep'
```
