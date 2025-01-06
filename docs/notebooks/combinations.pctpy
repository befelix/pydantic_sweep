# %% [markdown]
"""
# Combinations

Previously, we instantiated a basic model and assigned parameters to it. To
create more complex configurations, we can combine the outputs of different {any}`field`
calls to create complex configurations. The basic methods for combining them built on
top of the {py:mod}`itertools` Python package, but instead work on lists of nested
dictionaries. There are four basic combination functions that we will get to know,
but for now we will start with the most basic one: {any}`config_product`.
"""

# %%
import pprint

import pydantic_sweep as ps


class Model(ps.BaseModel):
    x: int = 0
    y: int = 0
    z: int = 0


xs = ps.field("x", [1, 2])
ys = ps.field("y", [10, 11])
zs = ps.field("z", [20, 21, 22])

configs = ps.config_product(xs, ys)
pprint.pp(configs, width=45)

# %% [markdown]
"""
This combines the two individual configurations together and creates a product of all
possible inputs. Like all the `ps.config_*` functions, we can provide an arbitrary 
number of input configurations to this function.
"""

# %%
configs = ps.config_product(xs, ys, zs)
pprint.pp(configs, width=45)

# %% [markdown]
"""
More importantly, the output of these functions is yet again a valid input, 
which means that we can nest these call infinitely in order to create complex 
configurations. That is, equivalently to the call above we could have executed
"""

# %%
configs = ps.config_product(ps.config_product(xs, ys), zs)
pprint.pp(configs, width=45)

# %% [markdown]
"""
This becomes interesting once we use other functions beyond the product. The
{any}`config_zip` function works similar to the builtin `zip` function and merges 
the incoming configurations:
"""
# %%
configs = ps.config_zip(xs, ys)
pprint.pp(configs, width=45)

# %% [markdown]
"""
The {any}`config_chain` and {any}`config_roundrobin` functions instead chain the 
input configurations behind each other, the former in the order provided while the
latter operates in a round-robin way taking configurations in turn:
"""
# %%
configs = ps.config_chain(ys, zs)
pprint.pp(configs, width=45)

configs = ps.config_roundrobin(ys, zs)
pprint.pp(configs, width=45)

# %% [markdown]
"""
We are not in a situation to create a complex configuration.
"""

# %%
models = ps.initialize(
    Model,
    ps.config_product(
        ps.config_zip(xs, ys),
        zs,
    ),
)
pprint.pp(models, width=45)

# %% [markdown]
"""
This first zips together the `xs` and `ys` configuration, and then takes a product of
these with all possible `zs` values, resulting in a complex configuration.
"""
# %% [markdown]
"""
## Custom combination functions

A key feature of the `ps.config_*` functions is that they extend Python 
builtins from the {py:mod}`itertools` package to operate on 
nested dictionaries instead and merge them in safe ways. This makes it impossible to 
create conflicting configurations by accident:
- {any}`config_product` is the equivalent of {py:func}`itertools.product`
- {any}`config_zip` is the equivalent of the builtin {py:func}`zip` function
- {any}`config_chain` is the equivalent of {py:func}`itertools.chain`
- {any}'config_roundrobin' is the equivalent of {py:func}`more_itertools.roundrobin`

You can build your own new function, but using the {any}`config_combine` function,
which takes as input existing methods:
"""

# %%
import itertools

configs = ps.config_combine(xs, ys, chainer=itertools.chain)
pprint.pp(configs, width=45)

configs = ps.config_combine(xs, ys, combiner=itertools.product)
pprint.pp(configs, width=45)

# %% [markdown]
"""
## Error checking

While nested combinations are flexible, it is also easy to accidentally overwrite the
same value twice. To avoid this, `pydantic_sweep` includes built-in error checking. 
For example, in the following we accidentally assign values to `x` twice, leading to
an exception.
"""

# %%
try:
    ps.config_product(
        ps.config_zip(xs, ys),
        ps.field("x", [-1, -2]),
    )
except ValueError as e:
    print(e)

# %% [markdown]
"""
The `pydantic_sweep` library tries to check things as much as possible, preferring to
give errors as early as possible. Next, we will discuss some gotchas that occur when
dealing with more complex, nested models.
"""
