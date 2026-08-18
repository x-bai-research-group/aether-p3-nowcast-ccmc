from datetime import datetime, timezone

import numpy as np
from netCDF4 import Dataset

from aether_p3_nowcast.grid import _bundle_root, _utc, _write


def test_bundle_root_is_relative_to_configuration(tmp_path):
    config_path = tmp_path / "bundle" / "config" / "production.json"
    config_path.parent.mkdir(parents=True)
    assert _bundle_root(config_path, {"bundle_root": ".."}) == tmp_path / "bundle"


def test_utc_uses_configured_cadence():
    assert _utc("2024-05-11T12:05:00Z", 300).minute == 5


def test_netcdf_schema(tmp_path):
    altitude = np.array([250.0, 260.0])
    latitude = np.array([-1.0, 1.0])
    longitude = np.array([-2.0, 2.0])
    count = len(altitude) * len(latitude) * len(longitude)
    fields = {
        "density": np.full(count, 1.0e-12),
        "density_lower_95": np.full(count, 0.8e-12),
        "density_upper_95": np.full(count, 1.2e-12),
        "aleatoric_std_log10": np.full(count, 0.1),
        "epistemic_std_log10": np.full(count, 0.05),
        "gamma": np.zeros(count),
        "nu": np.ones(count),
        "alpha": np.full(count, 2.0),
        "beta": np.ones(count),
    }
    path = tmp_path / "sample.nc"
    _write(
        path,
        datetime(2024, 5, 11, 12, tzinfo=timezone.utc),
        altitude,
        latitude,
        longitude,
        fields,
        {"model_version": "test"},
        300,
    )
    with Dataset(path) as dataset:
        assert dataset.Conventions == "CF-1.10"
        assert dataset.source == "AETHER-P3 Nowcast"
        assert dataset.variables["density"].shape == (1, 2, 2, 2)
        assert dataset.variables["density"].units == "kg m-3"
        assert dataset.variables["longitude"].units == "degrees_east"
        assert dataset.native_cadence_seconds == 300
