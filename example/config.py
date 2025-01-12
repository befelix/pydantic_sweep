from typing import Literal

import pydantic

import pydantic_sweep as ps


class Method(ps.BaseModel):
    optimizer: Literal["SGD", "Adam"] = "Adam"
    lr: float = 3e-4


class ExperimentConfig(ps.BaseModel):
    seed: int | None = None
    method: Method = pydantic.Field(default_factory=Method)
