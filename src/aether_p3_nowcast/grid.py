"""Generate one CF-style global three-dimensional nowcast snapshot."""

from __future__ import annotations

import json
import math
import subprocess
import tempfile
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

from . import MODEL_NAME, MODEL_VERSION
from .contract import CONTRACT_ID, FEATURE_COUNT
from .inference import NowcastModel


FIELD_UNITS = {
    "density": "kg m-3",
    "density_lower_95": "kg m-3",
    "density_upper_95": "kg m-3",
    "aleatoric_std_log10": "1",
    "epistemic_std_log10": "1",
    "gamma": "1",
    "nu": "1",
    "alpha": "1",
    "beta": "1",
}


def _resolve(value: str, bundle_root: Path) -> Path:
    path = Path(value)
    return path if path.is_absolute() else (bundle_root / path).resolve()


def _bundle_root(config_path: Path, config: dict) -> Path:
    root = Path(config.get("bundle_root", "."))
    if root.is_absolute():
        return root
    return (config_path.resolve().parent / root).resolve()


def _utc(value: str, cadence_seconds: int) -> datetime:
    utc = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if utc.tzinfo is None:
        utc = utc.replace(tzinfo=timezone.utc)
    utc = utc.astimezone(timezone.utc)
    if int(utc.timestamp()) % cadence_seconds or utc.microsecond:
        raise ValueError(f"UTC must lie on the {cadence_seconds}-second grid")
    return utc


def _axis(specification, name: str) -> np.ndarray:
    start, stop, step = map(float, specification)
    intervals = (stop - start) / step
    if step <= 0.0 or stop < start or abs(intervals - round(intervals)) > 1.0e-9:
        raise ValueError(f"invalid {name} grid")
    values = start + np.arange(round(intervals) + 1, dtype=np.float64) * step
    if len(values) < 2:
        raise ValueError(f"{name} grid must contain at least two points")
    return values


def _query(
    utc: datetime, altitude_km, latitude_deg, longitude_deg
) -> np.ndarray:
    height_km, latitude, longitude = np.meshgrid(
        altitude_km, latitude_deg, longitude_deg, indexing="ij"
    )
    height_km = height_km.ravel()
    latitude = latitude.ravel()
    longitude = longitude.ravel()
    day = (utc.date() - datetime(utc.year, 1, 1, tzinfo=timezone.utc).date()).days
    days = 366 if datetime(utc.year, 12, 31).timetuple().tm_yday == 366 else 365
    day_angle = 2.0 * math.pi * day / days
    utc_hours = utc.hour + utc.minute / 60.0
    utc_angle = 2.0 * math.pi * utc_hours / 24.0
    local_time_angle = (
        2.0 * math.pi * np.mod(utc_hours + longitude / 15.0, 24.0) / 24.0
    )
    longitude_rad = np.deg2rad(longitude)
    return np.column_stack(
        (
            np.deg2rad(latitude),
            np.sin(longitude_rad),
            np.cos(longitude_rad),
            height_km,
            np.full(len(latitude), math.sin(day_angle)),
            np.full(len(latitude), math.cos(day_angle)),
            np.full(len(latitude), math.sin(utc_angle)),
            np.full(len(latitude), math.cos(utc_angle)),
            np.sin(local_time_angle),
            np.cos(local_time_angle),
        )
    ).astype(np.float32)


def _generate_features(
    config: dict,
    bundle_root: Path,
    utc: datetime,
    work_dir: Path,
    latitude_deg,
    longitude_deg,
    altitude_km,
    workers: int,
) -> dict:
    jar = _resolve(config["feature_generator_jar"], bundle_root)
    weather = _resolve(config["space_weather_root"], bundle_root)
    orekit = _resolve(config["orekit_root"], bundle_root)
    for path, label in (
        (jar, "feature generator"),
        (weather, "space weather"),
        (orekit, "Orekit data"),
    ):
        if not path.exists():
            raise FileNotFoundError(f"{label} is missing: {path}")
    command = [
        "java",
        "-Xmx14g",
        "-cp",
        str(jar),
        "org.aetherp3.nowcast.GridFeatureMain",
        "--utc",
        utc.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "--weather",
        str(weather),
        "--orekit",
        str(orekit),
        "--output-dir",
        str(work_dir),
        "--lat-start",
        str(latitude_deg[0]),
        "--lat-end",
        str(latitude_deg[-1]),
        "--lat-step",
        str(latitude_deg[1] - latitude_deg[0]),
        "--lon-start",
        str(longitude_deg[0]),
        "--lon-end",
        str(longitude_deg[-1]),
        "--lon-step",
        str(longitude_deg[1] - longitude_deg[0]),
        "--alt-start",
        str(altitude_km[0]),
        "--alt-end",
        str(altitude_km[-1]),
        "--alt-step",
        str(altitude_km[1] - altitude_km[0]),
        "--workers",
        str(workers),
        "--feature-contract",
        CONTRACT_ID,
    ]
    print("[command] " + " ".join(command), flush=True)
    subprocess.run(command, cwd=bundle_root, check=True)
    return json.loads((work_dir / "grid_features.json").read_text(encoding="utf-8"))


def _validate_feature_manifest(
    manifest: dict,
    utc: datetime,
    cadence_seconds: int,
    latitude_deg: np.ndarray,
    longitude_deg: np.ndarray,
    altitude_km: np.ndarray,
) -> None:
    axes = {
        "latitude": latitude_deg,
        "longitude": longitude_deg,
        "altitude": altitude_km,
    }
    expected_points = int(np.prod([len(values) for values in axes.values()]))
    valid = (
        manifest.get("contract") == CONTRACT_ID
        and int(manifest.get("utc_unix", -1)) == int(utc.timestamp())
        and int(manifest.get("cadence_seconds", -1)) == cadence_seconds
        and manifest.get("record_order") == ["altitude", "latitude", "longitude"]
        and int(manifest.get("points", -1)) == expected_points
        and manifest.get("shared_features") == "shared_features.bin"
        and manifest.get("empirical_anchors") == "empirical_anchors.bin"
        and manifest.get("empirical_columns")
        == ["log10_JB2008_density", "log10_NRLMSISE00_density"]
    )
    for name, values in axes.items():
        axis = manifest.get(name, {})
        unit = "km" if name == "altitude" else "deg"
        valid = valid and (
            int(axis.get("count", -1)) == len(values)
            and np.isclose(float(axis.get(f"start_{unit}", np.nan)), values[0])
            and np.isclose(float(axis.get(f"end_{unit}", np.nan)), values[-1])
            and np.isclose(
                float(axis.get(f"step_{unit}", np.nan)), values[1] - values[0]
            )
        )
    if not valid:
        raise RuntimeError("feature generator manifest does not match the requested grid")


def _write(
    output_path: Path,
    utc: datetime,
    altitude_km,
    latitude_deg,
    longitude_deg,
    predicted_fields: dict[str, np.ndarray],
    model_metadata: dict,
    cadence_seconds: int,
) -> None:
    from netCDF4 import Dataset

    field_shape = (len(altitude_km), len(latitude_deg), len(longitude_deg))
    field_size = int(np.prod(field_shape))
    if set(predicted_fields) != set(FIELD_UNITS) or any(
        np.asarray(values).size != field_size
        or not np.isfinite(np.asarray(values)).all()
        for values in predicted_fields.values()
    ):
        raise ValueError("predicted fields do not match the NetCDF grid")
    temporary_path = output_path.with_suffix(".nc.tmp")
    if output_path.exists() or temporary_path.exists():
        raise FileExistsError(output_path)
    with Dataset(temporary_path, "w", format="NETCDF4") as netcdf:
        netcdf.createDimension("time", 1)
        netcdf.createDimension("altitude", len(altitude_km))
        netcdf.createDimension("latitude", len(latitude_deg))
        netcdf.createDimension("longitude", len(longitude_deg))
        time_variable = netcdf.createVariable("time", "i8", ("time",))
        time_variable[:] = [int(utc.timestamp())]
        time_variable.units = "seconds since 1970-01-01 00:00:00 UTC"
        time_variable.calendar = "proleptic_gregorian"
        time_variable.standard_name = "time"
        time_variable.axis = "T"
        for coordinate_name, coordinate_values, units, standard_name, axis in (
            ("altitude", altitude_km, "km", "altitude", "Z"),
            ("latitude", latitude_deg, "degrees_north", "latitude", "Y"),
            ("longitude", longitude_deg, "degrees_east", "longitude", "X"),
        ):
            coordinate_variable = netcdf.createVariable(
                coordinate_name, "f4", (coordinate_name,)
            )
            coordinate_variable[:] = coordinate_values
            coordinate_variable.units = units
            coordinate_variable.standard_name = standard_name
            coordinate_variable.axis = axis
            if coordinate_name == "altitude":
                coordinate_variable.positive = "up"
        field_dimensions = ("time", "altitude", "latitude", "longitude")
        for field_name, field_values in predicted_fields.items():
            field_variable = netcdf.createVariable(
                field_name,
                "f4",
                field_dimensions,
                zlib=True,
                complevel=4,
                shuffle=True,
                chunksizes=(1, 1, len(latitude_deg), len(longitude_deg)),
            )
            field_variable[0] = field_values.reshape(field_shape)
            field_variable.units = FIELD_UNITS[field_name]
            field_variable.coordinates = "time altitude latitude longitude"
            field_variable.long_name = field_name.replace("_", " ")
            if field_name == "density":
                field_variable.standard_name = "air_density"
        netcdf.Conventions = "CF-1.10"
        netcdf.title = "AETHER-P3 Nowcast global thermospheric density"
        netcdf.source = "AETHER-P3 Nowcast"
        netcdf.model_version = model_metadata["model_version"]
        netcdf.feature_contract = CONTRACT_ID
        netcdf.native_cadence_seconds = cadence_seconds
        latitude_step = float(latitude_deg[1] - latitude_deg[0])
        longitude_step = float(longitude_deg[1] - longitude_deg[0])
        altitude_step = float(altitude_km[1] - altitude_km[0])
        netcdf.horizontal_grid = (
            f"{latitude_step:g} degree latitude by "
            f"{longitude_step:g} degree longitude"
        )
        netcdf.vertical_grid = (
            f"{float(altitude_km[0]):g} to {float(altitude_km[-1]):g} km "
            f"at {altitude_step:g} km spacing"
        )
        netcdf.recommended_core_altitude_km = "250-520"
        netcdf.uncertainty_distribution = "Student-t in normalized log10 density"
    temporary_path.replace(output_path)


def generate(
    config_path: Path,
    utc_text: str,
    output_dir: Path,
    *,
    batch_size: int = 4096,
    workers: int = 8,
) -> Path:
    config_path = Path(config_path).resolve()
    config = json.loads(config_path.read_text(encoding="utf-8"))
    if (
        config.get("model_name") != MODEL_NAME
        or config.get("model_version") != MODEL_VERSION
        or config.get("feature_contract") != CONTRACT_ID
    ):
        raise ValueError("production configuration has incompatible model metadata")
    cadence_seconds = config.get("cadence_seconds")
    if (
        isinstance(cadence_seconds, bool)
        or not isinstance(cadence_seconds, int)
        or cadence_seconds <= 0
        or 86_400 % cadence_seconds
    ):
        raise ValueError("cadence_seconds must be a positive integer divisor of one day")
    if (
        isinstance(batch_size, bool)
        or not isinstance(batch_size, int)
        or batch_size <= 0
    ):
        raise ValueError("batch_size must be a positive integer")
    if isinstance(workers, bool) or not isinstance(workers, int) or workers <= 0:
        raise ValueError("workers must be a positive integer")
    bundle_root = _bundle_root(config_path, config)
    utc = _utc(utc_text, cadence_seconds)
    latitude_deg = _axis(config["grid"]["latitude"], "latitude")
    longitude_deg = _axis(config["grid"]["longitude"], "longitude")
    altitude_km = _axis(config["grid"]["altitude_km"], "altitude")
    model = NowcastModel(_resolve(config["model_root"], bundle_root))
    output_dir = Path(output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = (
        output_dir / f"aether_p3_nowcast_{utc.strftime('%Y%m%dT%H%M%SZ')}.nc"
    )
    with tempfile.TemporaryDirectory(prefix=".features_", dir=output_dir) as directory:
        work_dir = Path(directory)
        feature_manifest = _generate_features(
            config,
            bundle_root,
            utc,
            work_dir,
            latitude_deg,
            longitude_deg,
            altitude_km,
            workers,
        )
        _validate_feature_manifest(
            feature_manifest,
            utc,
            cadence_seconds,
            latitude_deg,
            longitude_deg,
            altitude_km,
        )
        shared_features = np.fromfile(
            work_dir / "shared_features.bin", dtype="<f4"
        )
        grid_point_count = len(altitude_km) * len(latitude_deg) * len(longitude_deg)
        if shared_features.shape != (FEATURE_COUNT,):
            raise RuntimeError("feature generator returned the wrong contract")
        empirical_path = work_dir / "empirical_anchors.bin"
        if empirical_path.stat().st_size != grid_point_count * 2 * 4:
            raise RuntimeError("feature generator returned the wrong empirical grid size")
        empirical_anchors = np.memmap(
            empirical_path,
            dtype="<f4",
            mode="r",
            shape=(grid_point_count, 2),
        )
        grid_features = np.repeat(
            shared_features[None, :], grid_point_count, axis=0
        )
        grid_features[:, :10] = _query(
            utc, altitude_km, latitude_deg, longitude_deg
        )
        grid_features[:, -2:] = empirical_anchors
        nig_parameters = model.predict_parameters(
            grid_features, batch_size=batch_size
        )
        predicted_fields = model.physical_fields(nig_parameters)
        _write(
            output_path,
            utc,
            altitude_km,
            latitude_deg,
            longitude_deg,
            predicted_fields,
            model.metadata,
            cadence_seconds,
        )
    print(f"[saved] {output_path}", flush=True)
    return output_path
