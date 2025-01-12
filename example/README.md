# Script execution with pydantic-sweeps

There are many ways to use `pydantic-sweep` in your experiment pipeline. Here we 
show one concrete example on how to connect your training scripts with pydantic models.
The example is split into three main files:

- `config.py` defines the base `pydantic` models that are used to execute your code.  
- `train.py` is the main experiment code. It receives a json-serialized 
  configuration on the command line, converts it to the configuration from `config.py`,
  and executes the training instructions.
- `runner.py` constructs a sequence of configurations based on `config.py` and sends 
  them to `train.py` as a command line argument.

If you have `uv` installed, you can execute the runner script directly by running
```bash
uv run --script runner.py
```
Otherwise, you can also execute it directly with `python`. Notably through the 
construction above, the `runner.py` script only depends on `conf.py` and is 
otherwise independent of any project-level dependencies that may be present in the 
`train.py` script. This means it can be executed independently.
