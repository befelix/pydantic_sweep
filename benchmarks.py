#!/usr/bin/env python3
"""Performance benchmarks for pydantic-sweep operations."""

import math
import statistics
import time
from typing import Any

import pydantic_sweep as ps


class BenchmarkModel(ps.BaseModel):
    """Test model for benchmarking."""

    seed: int = 42
    lr: float = 1e-4
    batch_size: int = 32
    optimizer: str = "Adam"
    layers: list[int] = [64, 32, 16]  # noqa: RUF012


def benchmark_config_generation(n_configs: int = 2000) -> dict[str, Any]:
    """Benchmark configuration generation performance."""
    start = time.perf_counter()

    configs = ps.config_product(
        ps.field("seed", ps.random_seeds(n_configs, upper=10_000)),
        ps.field("lr", [1e-3, 1e-4, 1e-5, 1e-6]),
        ps.field("batch_size", [16, 32, 64, 128]),
        ps.field("optimizer", ["Adam", "SGD", "RMSprop"]),
    )

    generation_time = time.perf_counter() - start

    start = time.perf_counter()
    models = ps.initialize(BenchmarkModel, configs)
    initialization_time = time.perf_counter() - start

    start = time.perf_counter()
    ps.check_unique(models)
    uniqueness_check_time = time.perf_counter() - start

    return {
        "n_configs": len(configs),
        "generation_time": generation_time,
        "initialization_time": initialization_time,
        "uniqueness_check_time": uniqueness_check_time,
        "total_time": generation_time + initialization_time + uniqueness_check_time,
        "configs_per_second": len(configs) / (generation_time + initialization_time),
    }


if __name__ == "__main__":
    num_runs = 5
    all_results = []

    for i in range(num_runs):
        print(f"Running benchmark {i + 1}/{num_runs}...")
        results = benchmark_config_generation()
        all_results.append(results)

    # Calculate mean and standard error
    mean_results = {}
    stderr_results = {}

    for key in all_results[0].keys():
        values = [result[key] for result in all_results]
        mean_results[key] = statistics.mean(values)
        if len(values) > 1:
            stderr_results[key] = statistics.stdev(values) / math.sqrt(len(values))
        else:
            stderr_results[key] = 0.0

    # Print the benchmark results
    print("\nBenchmark Results:")
    print(f"{'Metric':<25} {'Mean':>12} {'Std Error':>12}")
    print("-" * 50)

    for key in mean_results:
        if key == "n_configs":
            print(f"{key:<25} {int(mean_results[key]):>12,d}")
        elif "time" in key:
            print(f"{key:<25} {mean_results[key]:>12.6f} ±{stderr_results[key]:.6f}")
        else:
            print(f"{key:<25} {mean_results[key]:>12.2f} ±{stderr_results[key]:.2f}")
