"""Run the frozen model on the committed preprocessed example inputs."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

from aether_p3_nowcast.contract import CONTRACT_ID, FEATURE_COUNT
from aether_p3_nowcast.grid import _write
from aether_p3_nowcast.inference import NowcastModel


def arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--model-root", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    return parser.parse_args()


def load_example(
    path: Path,
) -> tuple[np.ndarray, datetime, np.ndarray, np.ndarray, np.ndarray]:
    with np.load(path, allow_pickle=False) as example:
        features = np.asarray(example["features"], dtype=np.float32)
        utc_unix = int(np.asarray(example["utc_unix"]).reshape(()))
        altitude_km = np.asarray(example["altitude_km"], dtype=np.float32)
        latitude_deg = np.asarray(example["latitude_deg"], dtype=np.float32)
        longitude_deg = np.asarray(example["longitude_deg"], dtype=np.float32)
        feature_contract = str(np.asarray(example["feature_contract"]).reshape(()))

    expected_records = len(altitude_km) * len(latitude_deg) * len(longitude_deg)
    if feature_contract != CONTRACT_ID:
        raise ValueError("example feature contract is incompatible with this model")
    if features.shape != (expected_records, FEATURE_COUNT):
        raise ValueError("example features have an invalid shape")
    if not all(
        np.isfinite(values).all()
        for values in (features, altitude_km, latitude_deg, longitude_deg)
    ):
        raise ValueError("example input contains a non-finite value")

    utc = datetime.fromtimestamp(utc_unix, tz=timezone.utc)
    return features, utc, altitude_km, latitude_deg, longitude_deg


def main() -> None:
    args = arguments()
    features, utc, altitude_km, latitude_deg, longitude_deg = load_example(
        args.input
    )
    model = NowcastModel(args.model_root)
    parameters = model.predict_parameters(features, batch_size=len(features))
    fields = model.physical_fields(parameters)

    output_directory = args.output_dir.resolve()
    output_directory.mkdir(parents=True, exist_ok=True)
    output_path = output_directory / (
        f"aether_p3_nowcast_{utc.strftime('%Y%m%dT%H%M%SZ')}.nc"
    )
    _write(
        output_path,
        utc,
        altitude_km,
        latitude_deg,
        longitude_deg,
        fields,
        model.metadata,
        cadence_seconds=300,
    )
    print(f"[saved] {output_path}")


if __name__ == "__main__":
    main()
