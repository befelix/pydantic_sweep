# %% [markdown]
"""
# Introduction

`pydantic_sweep` is built to construct parameter sweeps over
{py:class}`pydantic.BaseModel` classes. If you're not familiar with how `pydantic`
works, please first familiarize yourself with the
[pydantic documentation](https://docs.pydantic.dev/latest/)
"""

# %% [markdown]
"""
The starting point for any parameter sweep is a (nested) 
{py:class}`pydantic.BaseModel`. Since we want to use these models for configuring
experiments, we need some custom configuration to make them safe. For now, this means we
use the {any}`pydantic_sweep.BaseModel` class instead. Please jump to the {doc}`models` 
section for details or if you want to use your own models.
"""

# %%
import pprint

import pydantic_sweep as ps


class Sub(ps.BaseModel):
    x: int


class Model(ps.BaseModel):
    sub: Sub
    y: int = 6


# %% [markdown]
"""
While you could manually instantiate these models with your desired configuration, 
this library provides an automatic way to generate configuration. The basic 
entry-point is the {any}`field` function, which constructs (nested) 
dictionaries of sub-configurations using "." to identify nested fields. For example, 
to assign the values `(1, 2, 3)` to the field `sub.x`, we can run:
"""

# %%
configs = ps.field("sub.x", [1, 2, 3])
pprint.pp(configs, width=45)

# %% [markdown]
"""
While we could instantiate the models with these configurations manually, we will use
the {any}`initialize` function, which will make for more compact 
code as we move to more complicated configuration setups later.
"""

# %%
models = ps.initialize(Model, configs)
pprint.pp(models, width=45)

# %% [markdown]
"""
Note that the models took the default values for `y`, while we only provided the 
partial configurations for `x`.

## Fixed and Default values

Sometimes we want to set the same values for all the models. For this, we can use the
`constant` field:
"""

# %%
models = ps.initialize(Model, configs, constant=dict(y=0))
pprint.pp(models, width=45)

# %% [markdown]
"""
The parameter `y=0` is safely merged with the other configurations. If we only want 
to change the default values of the model, we need to use the `default` argument 
instead. We will also use the {any}`DefaultValue` placeholder to define a placeholder
that does not modify values.
"""

# %%
models = ps.initialize(
    Model,
    ps.field("y", [10, ps.DefaultValue]),
    constant=dict(sub=dict(x=0)),
    default=dict(y=0),
)
pprint.pp(models, width=45)

# %% [markdown]
"""
Note that while the original `Model` defines `y=6`, here the default value is `0` as 
defined above. For convenience, it is also possible to provide dot-seperated 
flattened dictionaries of the form `{"sub.x": 0}` for the `constant` and `default` 
arguments.

So far, we have encountered the two most important methods in this library: {any}`field`
and {any}`initialize`. While these functions have a lot more features, so far we 
haven't accomplished anything that couldn't be easily done by a list-comprehension. 
In the next section, we will start to combine these configs in more interesting ways.
"""
