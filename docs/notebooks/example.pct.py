# %% [markdown]
"""
# Example

In the following, we will conclude the tutorial with a somewhat realistic example of
how to use the library. We start by defining nested models. For a full example on how
to connect your training scripts with `pydantic-sweep`, see the
[example folder](https://github.com/befelix/pydantic_sweep/tree/main/example)
in the GitHub repo.
"""

# %%

import pprint
from typing import Literal

import pydantic_sweep as ps


class MLP(ps.BaseModel):
    """Configuration for a MLP."""

    num_layers: int = 4
    neurons_per_layer: int = 128
    activation: Literal["tanh", "relu"] = "relu"


class LSTM(ps.BaseModel):
    """Configuration for a LSTM network."""

    num_layers: int = 4
    sequence_length: int = 20
    hidden_size: int = 128


class Learner(ps.BaseModel):
    network: MLP | LSTM = MLP()
    seed: int | None = None  # Optionally, fix the random seed
    learning_rate: float = 3e-4


# %% [markdown]
"""
Next, we configure our experiments. We want to do a comparison study, where we vary the
size of the neural networks individually for both `MLP` and `LSTM`.
"""

# %%
lstm_configs = ps.initialize(
    LSTM,
    to="network",
    configs=ps.config_product(
        ps.field("num_layers", [ps.DefaultValue, 5]),
        ps.field("sequence_length", [ps.DefaultValue, 30]),
    ),
)


mlp_configs = ps.initialize(
    MLP,
    to="network",
    configs=ps.field("num_layers", [ps.DefaultValue, 5]),
)

# %% [markdown]
"""
Next, we configure the main method. We want reproducible results, so we will fix the 
random seeds to random values, using the {any}`random_seeds` convenience method. In 
addition, we want to try smaller learning rates for the LSTM networks and larger ones
for the MLPs.
"""

# %%
models = ps.initialize(
    Learner,
    ps.config_product(
        ps.field("seed", ps.random_seeds(num=3)),
        ps.config_chain(
            ps.config_product(
                ps.field("learning_rate", [ps.DefaultValue, 1e-5]),
                lstm_configs,
            ),
            ps.config_product(
                ps.field("learning_rate", [ps.DefaultValue, 1e-3]),
                mlp_configs,
            ),
        ),
    ),
)

# This will raise an exception if we accidentally duplicated a configuration
ps.check_unique(models)

pprint.pp(models)

# %% [markdown]
"""
This yields a surprisingly complex configuration specification. Each of these models 
can now be passed to the experiment and consequently evaluated.

This marks the end of the tutorial. If you have any questions please open 
[an issue](https://github.com/befelix/pydantic_sweep/issues) on the project's Github 
page. Please also do this, if you find functionality missing or discover bugs. PRs 
are also always welcome.
"""
