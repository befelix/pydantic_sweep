import re
import subprocess
import sys
from pathlib import Path

from pydantic_sweep import __version__

_EXPERIMENT_DIR = Path(__file__).parents[1] / "example"


def test_script_version():
    for name in ["runner.py", "train.py"]:
        with open(_EXPERIMENT_DIR / name) as f:
            for line in f.readlines():
                # No longer in the metadata
                if not line.startswith("#"):
                    break

                if "pydantic-sweep" in line:
                    major, minor, _ = __version__.split(".")
                    expected = rf"pydantic-sweep~={major}.{minor}.\d+"
                    match = re.search(expected, line)
                    assert match is not None, f"Version not correct: {line}"


def test_script_run():
    res = subprocess.run(
        [sys.executable, str(_EXPERIMENT_DIR / "runner.py")],
        check=True,
        capture_output=True,
        text=True,
    )
    assert "Execute main with:" in res.stdout
