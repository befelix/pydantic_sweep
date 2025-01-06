# %% [markdown]
"""
# Nested models

So far, we have only considered basic nested models. Configuration gets more interesting
when there are Union types for sub-models in pydantic. While one could use the previous
methods, by default `pydantic`'s initialization behavior will match partial
configurations to the ["best" Model type that matches](
https://docs.pydantic.dev/latest/concepts/unions/). This
explicitly allows ambiguity, when multiple could match. Instead, `BaseModel` includes a
 custom `model_validator` that disallows these kind of unsafe unions:
"""

# %%
import pprint

import pydantic

import pydantic_sweep as ps


class Method1(ps.BaseModel):
    x: int = 0
    y: int = 0


class Method2(ps.BaseModel):
    x: int = 0
    z: int = 0


class Environment(ps.BaseModel):
    method: Method1 | Method2
    seed: int | None = None


xs = ps.field("method.x", [1, 2])

try:
    ps.initialize(Environment, xs)
except pydantic.ValidationError as e:
    print(e)

# %% [markdown]
"""
Here the `method.x` value can match either `Method1` or `Method2`. As suggested by 
the error, to avoid this behavior either we need to make it explicit which model we 
want to use. `pydantic` offers a way to do this through [discriminated unions](
https://docs.pydantic.dev/latest/concepts/unions/#discriminated-unions). 
Alternatively, we can directly initialize the sub-models individually. The 
{any}`initialize` method provides two ways to do this via the `at` and `to` keyword
arguments.
 
The `to` keyword is a shortcut to the following code, which first instantiates a
`Method1` model and then passes the models as input to the `field` method.
"""

# %%
xs = ps.field("x", [1, 2])
configs_m1 = ps.field("method", ps.initialize(Method1, xs))
pprint.pp(ps.initialize(Environment, configs_m1))

# %% [markdown]
"""
For convenience, we can instead directly use the initialize `to` argument.`:
"""

# %%
configs_m1 = ps.initialize(Method1, xs, to="method")
pprint.pp(ps.initialize(Environment, configs_m1))

# %% [markdown]
"""
Alternatively, we can directly create parameters using the full `method.x` path, 
and then initialize a model `at` the respective field.
"""

# %%
zs = ps.field("method.z", [3, 4])
configs_m2 = ps.initialize(Method2, zs, at="method")
pprint.pp(ps.initialize(Environment, configs_m2))

# %% [markdown]
"""
Which of the two methods ends up being more convenient depends on the use-case. Note 
that this kind of manual instantiation is only required when the submodel type is 
ambiguous. Otherwise, one can rely on the usual pydantic initialization logic.

The individual configurations can, of course, be then combined again to yield more 
complex configurations:
"""

# %%

models = ps.initialize(
    Environment,
    ps.config_product(
        ps.field("seed", ps.random_seeds(num=3)),
        ps.config_chain(configs_m1, configs_m2),
    ),
)
pprint.pp(models)

# %% [markdown]
"""
Next, we will give some details on the model class, before giving a final, 
full-fledged example in {doc}`example`.
"""
