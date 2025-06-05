# /// script
# dependencies = [
#   "pydantic-sweep~=0.3.1"
# ]
# ///

import argparse

from config import ExperimentConfig


def command_line_interface() -> ExperimentConfig:
    """Return the configuration passed as json on the command line."""
    # Receive a json-serialized configuration as a command line argument. This
    # requires and equivalent counter-part in the runner.py script.
    parser = argparse.ArgumentParser()
    parser.add_argument("--json", type=str, required=True)
    json_config = parser.parse_args().json

    # Reconstruct the config from json
    return ExperimentConfig.model_validate_json(json_config)


def main(config: ExperimentConfig) -> None:
    """Main training function."""
    print(f"Execute main with: {config!r}")
    # Your favorite program goes here...


if __name__ == "__main__":
    config = command_line_interface()
    main(config)
