"""Verify the executable AETHER-P3 example against its reference NetCDF."""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
from netCDF4 import Dataset


FIELDS = (
    "density",
    "density_lower_95",
    "density_upper_95",
    "aleatoric_std_log10",
    "epistemic_std_log10",
    "gamma",
    "nu",
    "alpha",
    "beta",
)
COORDINATES = ("time", "altitude", "latitude", "longitude")
PHYSICAL_FIELDS = ("density", "density_lower_95", "density_upper_95")


def arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--actual", type=Path, required=True)
    parser.add_argument("--reference", type=Path, required=True)
    return parser.parse_args()


def values(dataset: Dataset, name: str) -> np.ndarray:
    return np.asarray(dataset.variables[name][:], dtype=np.float64)


def verify(actual_path: Path, reference_path: Path) -> None:
    if not actual_path.is_file():
        raise FileNotFoundError(f"example output is missing: {actual_path}")
    if not reference_path.is_file():
        raise FileNotFoundError(f"reference output is missing: {reference_path}")

    with Dataset(actual_path) as actual, Dataset(reference_path) as reference:
        expected_dimensions = {
            "time": 1,
            "altitude": 2,
            "latitude": 2,
            "longitude": 2,
        }
        observed_dimensions = {
            name: len(actual.dimensions[name]) for name in expected_dimensions
        }
        if observed_dimensions != expected_dimensions:
            raise AssertionError(
                f"unexpected dimensions: {observed_dimensions}"
            )
        if actual.getncattr("Conventions") != "CF-1.10":
            raise AssertionError("the example is not declared as CF-1.10")
        if actual.getncattr("source") != "AETHER-P3 Nowcast":
            raise AssertionError("unexpected NetCDF source metadata")

        for name in COORDINATES:
            np.testing.assert_array_equal(values(actual, name), values(reference, name))

        for name in FIELDS:
            observed = values(actual, name)
            expected = values(reference, name)
            if observed.shape != (1, 2, 2, 2) or not np.isfinite(observed).all():
                raise AssertionError(f"{name} is incomplete or non-finite")
            if name in PHYSICAL_FIELDS:
                np.testing.assert_allclose(observed, expected, rtol=5.0e-3, atol=0.0)
            else:
                np.testing.assert_allclose(
                    observed, expected, rtol=5.0e-3, atol=5.0e-4
                )

        density = values(actual, "density")
        lower = values(actual, "density_lower_95")
        upper = values(actual, "density_upper_95")
        if not ((lower > 0.0).all() and (lower <= density).all() and (density <= upper).all()):
            raise AssertionError("density or its predictive interval is invalid")
        if not (values(actual, "nu") > 0.0).all():
            raise AssertionError("nu must be positive")
        if not (values(actual, "alpha") > 1.0).all():
            raise AssertionError("alpha must be greater than one")
        if not (values(actual, "beta") > 0.0).all():
            raise AssertionError("beta must be positive")


def main() -> None:
    args = arguments()
    verify(args.actual.resolve(), args.reference.resolve())
    print("AETHER-P3 example: PASS")
    print(f"Output: {args.actual.resolve()}")


if __name__ == "__main__":
    main()
