"""Reader for globally ordered fixed-width training and validation records."""

from __future__ import annotations

import json
import math
from pathlib import Path

import numpy as np

from .contract import (
    FEATURE_COUNT,
    FEATURE_NAMES,
    FEATURE_SLICES,
    SOURCE_DATASET_CONTRACT_ID,
)


SOURCE_DATASET_FEATURE_NAMES = tuple(
    {
        "F107_previous_day": "F107_prev_day_current",
        "F30_current_day": "F30_current",
        "log10_JB2008_density": "logJB_anchor",
        "log10_NRLMSISE00_density": "logMSIS_anchor",
    }.get(name, name)
    for name in FEATURE_NAMES
)


def record_dtype() -> np.dtype:
    return np.dtype(
        [
            ("x", "<f4", (FEATURE_COUNT,)),
            ("y_log10", "<f4"),
            ("utc_unix", "<i8"),
            ("satellite_id", "<i4"),
            ("block_id", "<i4"),
        ],
        align=False,
    )


def load_metadata(root: Path) -> dict:
    metadata = json.loads((Path(root) / "metadata.json").read_text(encoding="utf-8"))
    if metadata.get("contract") not in {
        SOURCE_DATASET_CONTRACT_ID,
        "aether-p3-nowcast-342-v1",
    }:
        raise ValueError("dataset does not use the AETHER-P3 342-input contract")
    if int(metadata.get("feature_count", -1)) != FEATURE_COUNT:
        raise ValueError("dataset feature count differs from the model contract")
    names = metadata.get("feature_names")
    if names is not None and tuple(names) not in {
        FEATURE_NAMES,
        SOURCE_DATASET_FEATURE_NAMES,
    }:
        raise ValueError("dataset feature names or ordering differ from the model")
    return metadata


def load_normalization(root: Path) -> tuple[np.ndarray, np.ndarray, float, float]:
    load_metadata(root)
    with np.load(Path(root) / "normalization.npz") as normalization:
        feature_mean = np.asarray(normalization["x_mean"], np.float32)
        feature_std = np.asarray(normalization["x_std"], np.float32)
        log_density_mean = float(np.asarray(normalization["y_mean"]).reshape(()))
        log_density_std = float(np.asarray(normalization["y_std"]).reshape(()))
    if feature_mean.shape != (FEATURE_COUNT,) or feature_std.shape != (
        FEATURE_COUNT,
    ):
        raise ValueError("normalization has the wrong feature dimension")
    if (
        not np.isfinite(feature_mean).all()
        or not np.isfinite(feature_std).all()
        or np.any(feature_std <= 0.0)
        or not np.isfinite([log_density_mean, log_density_std]).all()
        or log_density_std <= 0.0
    ):
        raise ValueError("normalization contains an invalid value")
    return feature_mean, feature_std, log_density_mean, log_density_std


def validate_dataset(root: Path) -> dict:
    """Validate the frozen record layout without reading density labels."""
    root = Path(root)
    metadata = load_metadata(root)
    row_bytes = record_dtype().itemsize
    for split in ("train", "val"):
        definition = metadata.get("splits", {}).get(split)
        if not isinstance(definition, dict) or not definition.get("shards"):
            raise ValueError(f"dataset split is missing: {split}")
        observed = 0
        for name in definition["shards"]:
            path = root / name
            if not path.is_file():
                raise FileNotFoundError(path)
            size = path.stat().st_size
            if size % row_bytes:
                raise ValueError(f"record shard has a partial row: {path}")
            observed += size // row_bytes
        expected = int(definition["records"])
        if observed != expected:
            raise ValueError(
                f"{split} record count is {observed}, metadata declares {expected}"
            )
    validation_block_counts = metadata.get("validation_block_counts")
    if not isinstance(validation_block_counts, dict) or any(
        int(record_count) <= 0
        for record_count in validation_block_counts.values()
    ):
        raise ValueError("validation block counts are missing or invalid")
    if sum(map(int, validation_block_counts.values())) != int(
        metadata["splits"]["val"]["records"]
    ):
        raise ValueError("validation block counts do not sum to validation records")
    load_normalization(root)
    return metadata


def _parse(serialized_record):
    import tensorflow as tf

    x_stop = FEATURE_COUNT * 4
    y_stop = x_stop + 4
    utc_stop = y_stop + 8
    satellite_stop = utc_stop + 4

    def record_bytes(start, length):
        return tf.strings.substr(serialized_record, start, length, unit="BYTE")

    flat_features = tf.io.decode_raw(
        record_bytes(0, x_stop), tf.float32, little_endian=True
    )
    return {
        "x": tf.ensure_shape(flat_features, (FEATURE_COUNT,)),
        "y_log10": tf.io.decode_raw(
            record_bytes(x_stop, 4),
            tf.float32,
            little_endian=True,
        )[0],
        "utc_unix": tf.io.decode_raw(
            record_bytes(y_stop, 8),
            tf.int64,
            little_endian=True,
        )[0],
        "satellite_id": tf.io.decode_raw(
            record_bytes(utc_stop, 4),
            tf.int32,
            little_endian=True,
        )[0],
        "block_id": tf.io.decode_raw(
            record_bytes(satellite_stop, 4),
            tf.int32,
            little_endian=True,
        )[0],
    }


def group_features(flat_features):
    import tensorflow as tf

    return {
        feature_slice.name: tf.reshape(
            flat_features[feature_slice.start : feature_slice.stop],
            feature_slice.shape,
        )
        for feature_slice in FEATURE_SLICES
    }


def make_dataset(
    root: Path, split: str, *, batch_size: int, include_identity: bool = False
):
    import tensorflow as tf

    root = Path(root)
    metadata = load_metadata(root)
    feature_mean, feature_std, log_density_mean, log_density_std = load_normalization(
        root
    )
    definition = metadata["splits"][split]
    paths = [str(root / name) for name in definition["shards"]]
    dataset = tf.data.FixedLengthRecordDataset(
        paths,
        record_bytes=record_dtype().itemsize,
        num_parallel_reads=1,
    )
    feature_mean_tensor = tf.constant(feature_mean)
    feature_std_tensor = tf.constant(feature_std)
    log_density_mean_tensor = tf.constant(log_density_mean, tf.float32)
    log_density_std_tensor = tf.constant(log_density_std, tf.float32)

    def prepare(serialized):
        row = _parse(serialized)
        features = group_features(
            (row["x"] - feature_mean_tensor) / feature_std_tensor
        )
        normalized_log_density = (
            row["y_log10"] - log_density_mean_tensor
        ) / log_density_std_tensor
        if not include_identity:
            return features, normalized_log_density
        record_identity = {
            name: row[name] for name in ("utc_unix", "satellite_id", "block_id")
        }
        return features, normalized_log_density, record_identity

    options = tf.data.Options()
    options.deterministic = True
    dataset = dataset.with_options(options)
    dataset = dataset.map(
        prepare, num_parallel_calls=tf.data.AUTOTUNE, deterministic=True
    )
    batch_count = math.ceil(int(definition["records"]) / batch_size)
    dataset = dataset.batch(batch_size)
    dataset = dataset.apply(tf.data.experimental.assert_cardinality(batch_count))
    return dataset.prefetch(tf.data.AUTOTUNE)
