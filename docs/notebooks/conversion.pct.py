# %% [markdown]
"""
# Format Conversion

Frequently, specific configurations are saves as files in various formats such as JSON,
YAML, TOML, or Python scripts. The {any}`pydantic_sweep.convert` module provides
utilities to facilitate conversion between these formats while maintaining the integrity
of the Pydantic models. Concertely, the module supports

- **Loading** models from JSON, YAML, TOML, and Python files
- **Writing** models to JSON, YAML, TOML, and Python files
- **Code generation** to convert models into executable Python code
- **Command-line interface** for batch conversions
"""

# %% [markdown]
"""
## Conversion between formats

The {any}`convert.load` function and {any}`convert.write` functions allow reading and
writing Pydantic models from and to various file formats. For example, the following
saves a model as yaml and then reads it back. The `model` argument to
{any}`convert.load` is the dot-separated import path to the Pydantic model class
(in this case ``__main__.Config``).
"""

# %%
import tempfile
from pathlib import Path

from pydantic_sweep import BaseModel, convert


class Config(BaseModel):
    name: str
    value: int
    path: Path


config = Config(name="test", value=42, path=Path("/tmp/data"))

with tempfile.TemporaryDirectory() as temp_dir:
    config_file = Path(temp_dir) / "config.yaml"
    convert.write(config_file, model=config)
    loaded_config = convert.load(config_file, model="__main__.Config")

assert loaded_config == config
print(loaded_config)

# %% [markdown]
"""
### Python Code

Storing configuration directly in Python files can be advantageous for complex setups,
as they allow for dynamic generation of configurations using code.
They are supported the same was as other formats,
with the difference that the `model` parameter to {any}`convert.load` is the variable
name inside the Python file that holds the model instance.
"""

# %%

with tempfile.TemporaryDirectory() as temp_dir:
    config_file = Path(temp_dir) / "config.py"
    convert.write(config_file, model=config)

    print("Written Python file:")
    with open(config_file) as f:
        print(f.read())

    loaded_config = convert.load(config_file, model="model")

assert loaded_config == config

# %% [markdown]
"""
## Command-Line Interface

The conversion module also provides a command-line interface (CLI) for converting
configuration files between different formats. This is particularly useful for batch
processing or integrating into existing workflows.
To use the CLI, you can run the following command in your terminal:
```bash
python -m pydantic_sweep.convert input_file output_file --model model_path/name
```
Here, `input_file` is the path to the source configuration file, `output_file` is
the path where the converted file should be saved, and `model_path` is the dot-separated
import path to the Pydantic model class (or variable name for Python files).
For example, to convert a JSON configuration file to YAML, you would run:
```bash
python -m pydantic_sweep.convert config.json config.yaml --model my_library.MyModel
```
"""
