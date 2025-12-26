# /// script
# dependencies = [
#   "pydantic-sweep~=0.3.8"
# ]
# ///

import subprocess
import sys
from pathlib import Path

from config import ExperimentConfig

import pydantic_sweep as ps
from pydantic_sweep.cli import ModelDumpCLI

# Construct experiment configurations
experiments = ps.initialize(
    ExperimentConfig,
    ps.config_product(
        ps.field("seed", ps.random_seeds(3)),
        ps.config_zip(
            ps.field("method.optimizer", ["SGD", "Adam", ps.DefaultValue]),
            ps.field("method.lr", [1e-6, 1e-4, ps.DefaultValue]),
        ),
    ),
)

# Make sure they are unique
ps.check_unique(experiments)

# Call the script with all experiment configurations
script = Path(__file__).parent / "train.py"
for experiment in experiments:
    # The runner and train script communicate via CLI arguments
    # pydantic-sweep provides helper functions for basic CLIs.
    cli_args = ModelDumpCLI.cli_args(experiment)

    # Here, were calling subprocess with the current python executable. On a cluster,
    # one would instead schedule the corresponding run.
    subprocess.run(
        [sys.executable, str(script), *cli_args],
        check=True,
    )
