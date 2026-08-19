#!/usr/bin/env python3
"""Benchmark frozen-model inference on preprocessed AETHER-P3 inputs."""

from __future__ import annotations

import argparse
import json
import platform
import statistics
import time
from pathlib import Path

import numpy as np

from aether_p3_nowcast.contract import FEATURE_COUNT
from aether_p3_nowcast.inference import NowcastModel


def arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--input",
        type=Path,
        default=Path("examples/input/preprocessed_example.npz"),
    )
    parser.add_argument("--model-root", type=Path, default=Path("model"))
    parser.add_argument("--points", type=int, default=251_100)
    parser.add_argument("--batch-size", type=int, default=4096)
    parser.add_argument("--repeats", type=int, default=3)
    parser.add_argument("--single-point-repeats", type=int, default=20)
    parser.add_argument("--output", type=Path)
    return parser.parse_args()


def positive(name: str, value: int) -> int:
    if isinstance(value, bool) or value <= 0:
        raise ValueError(f"{name} must be a positive integer")
    return value


def load_features(path: Path, point_count: int) -> np.ndarray:
    with np.load(path, allow_pickle=False) as example:
        source = np.asarray(example["features"], dtype=np.float32)
    if source.ndim != 2 or source.shape[1] != FEATURE_COUNT or len(source) == 0:
        raise ValueError(
            f"benchmark input must have shape (records, {FEATURE_COUNT})"
        )
    repetitions = (point_count + len(source) - 1) // len(source)
    return np.tile(source, (repetitions, 1))[:point_count]


def timed_prediction(
    model: NowcastModel, features: np.ndarray, batch_size: int
) -> tuple[float, float]:
    prediction_start = time.perf_counter()
    parameters = model.predict_parameters(features, batch_size=batch_size)
    prediction_seconds = time.perf_counter() - prediction_start

    conversion_start = time.perf_counter()
    model.physical_fields(parameters)
    conversion_seconds = time.perf_counter() - conversion_start
    return prediction_seconds, conversion_seconds


def median(values: list[float]) -> float:
    return float(statistics.median(values))


def main() -> None:
    args = arguments()
    point_count = positive("points", args.points)
    batch_size = positive("batch-size", args.batch_size)
    repeats = positive("repeats", args.repeats)
    single_repeats = positive("single-point-repeats", args.single_point_repeats)

    import tensorflow as tf

    load_start = time.perf_counter()
    model = NowcastModel(args.model_root)
    model_load_seconds = time.perf_counter() - load_start
    features = load_features(args.input, point_count)

    warmup_count = min(point_count, batch_size)
    timed_prediction(model, features[:warmup_count], warmup_count)

    single_times = []
    for _ in range(single_repeats):
        prediction, conversion = timed_prediction(model, features[:1], 1)
        single_times.append(prediction + conversion)

    prediction_times = []
    conversion_times = []
    for _ in range(repeats):
        prediction, conversion = timed_prediction(model, features, batch_size)
        prediction_times.append(prediction)
        conversion_times.append(conversion)

    prediction_seconds = median(prediction_times)
    conversion_seconds = median(conversion_times)
    total_seconds = prediction_seconds + conversion_seconds
    gpu_devices = [device.name for device in tf.config.list_physical_devices("GPU")]
    result = {
        "device_class": "GPU" if gpu_devices else "CPU",
        "gpu_devices": gpu_devices,
        "platform": platform.platform(),
        "python_version": platform.python_version(),
        "tensorflow_version": tf.__version__,
        "model_load_seconds": model_load_seconds,
        "single_point_warm_median_seconds": median(single_times),
        "field_point_count": point_count,
        "batch_size": batch_size,
        "field_prediction_median_seconds": prediction_seconds,
        "field_physical_conversion_median_seconds": conversion_seconds,
        "field_model_total_median_seconds": total_seconds,
        "field_points_per_second": point_count / total_seconds,
        "repeats": repeats,
    }
    rendered = json.dumps(result, indent=2)
    print(rendered)
    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered + "\n", encoding="utf-8")
        print(f"[saved] {args.output}")


if __name__ == "__main__":
    main()
