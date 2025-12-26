# /// script
# dependencies = [
#   "pydantic-sweep~=0.3.8"
# ]
# ///


from config import ExperimentConfig

from pydantic_sweep.cli import ModelDumpCLI


def main(config: ExperimentConfig) -> None:
    """Main training function."""
    print(f"Execute main with: {config!r}")
    # Your favorite program goes here...


if __name__ == "__main__":
    # The runner and train script communicate via CLI arguments
    # pydantic-sweep provides helper functions for basic CLIs.
    config = ModelDumpCLI.from_cli(ExperimentConfig)
    main(config)
