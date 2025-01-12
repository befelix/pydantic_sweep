# /// script
# dependencies = [
#   "pydantic-sweep~=0.3.1"
# ]
# ///

import subprocess
import sys
from pathlib import Path

from config import ExperimentConfig

import pydantic_sweep as ps

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
    # Here, were calling subprocess with the current python executable. On a cluster,
    # one would instead schedule the corresponding run.
    subprocess.run(
        [sys.executable, script, "--json", experiment.model_dump_json()],
        check=True,
    )
