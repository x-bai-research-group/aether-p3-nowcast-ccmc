"""Validation diagnostics that do not read evaluation benchmark cases."""

from __future__ import annotations

import json
import os
from pathlib import Path

import numpy as np

from .metrics import accuracy_metrics, predictive_uncertainty_metrics
from .network import NetworkConfig, build_model
from .records import load_metadata, load_normalization, make_dataset


MISSION_NAMES = {
    0: "CHAMP",
    1: "GRACE-A",
    2: "GOCE",
    3: "SWARM-A",
    4: "SWARM-B",
    5: "SWARM-C",
    6: "GRACE-FO",
}
SUMMARY_FIELDS = (
    "relative_error",
    "pearson_r",
    "physical_rmse",
    "mace",
    "student_t_95_coverage",
)


def _compute_metrics(
    normalized_log_density,
    nig_parameters,
    log_density_mean,
    log_density_std,
):
    observed_density = np.power(
        10.0,
        normalized_log_density * log_density_std + log_density_mean,
    )
    predicted_density = np.power(
        10.0,
        nig_parameters[:, 0] * log_density_std + log_density_mean,
    )
    metrics = accuracy_metrics(observed_density, predicted_density)
    metrics.update(
        predictive_uncertainty_metrics(
            normalized_log_density,
            nig_parameters,
        )
    )
    return metrics


def _mean_metrics(metric_groups):
    mean_metrics = {
        "records": int(sum(group_metrics["records"] for group_metrics in metric_groups))
    }
    for metric_name in SUMMARY_FIELDS:
        available_values = [
            group_metrics[metric_name]
            for group_metrics in metric_groups
            if group_metrics.get(metric_name) is not None
        ]
        mean_metrics[metric_name] = (
            None if not available_values else float(np.mean(available_values))
        )
    return mean_metrics


def evaluate(
    run_dir: Path, dataset_root: Path, output_dir: Path, *, batch_size: int = 4096
) -> dict:
    os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "1")
    import tensorflow as tf

    if (
        isinstance(batch_size, bool)
        or not isinstance(batch_size, int)
        or batch_size <= 0
    ):
        raise ValueError("batch_size must be a positive integer")
    run_dir = Path(run_dir).resolve()
    dataset_root = Path(dataset_root).resolve()
    training_audit = json.loads(
        (run_dir / "TRAINING_AUDIT.json").read_text(encoding="utf-8")
    )
    if training_audit.get("evaluation_benchmarks_used") is not False:
        raise RuntimeError("training audit does not exclude evaluation benchmarks")
    if Path(training_audit["configuration"]["dataset_root"]).resolve() != dataset_root:
        raise RuntimeError("validation dataset differs from training")
    checkpoint_path = Path(training_audit["checkpoint"])
    if not checkpoint_path.is_file():
        raise FileNotFoundError(checkpoint_path)
    precision_policy = (
        "mixed_float16"
        if training_audit["configuration"]["mixed_precision"]
        else "float32"
    )
    tf.keras.mixed_precision.set_global_policy(precision_policy)
    model = build_model(NetworkConfig(**training_audit["configuration"]["network"]))
    model.load_weights(checkpoint_path)
    dataset_metadata = load_metadata(dataset_root)
    _, _, log_density_mean, log_density_std = load_normalization(dataset_root)
    validation_dataset = make_dataset(
        dataset_root,
        "val",
        batch_size=batch_size,
        include_identity=True,
    )
    normalized_log_density_batches = []
    nig_parameter_batches = []
    validation_block_batches = []
    satellite_batches = []
    validation_batch_count = int(tf.data.experimental.cardinality(validation_dataset))
    for batch_number, (
        model_inputs,
        normalized_log_density,
        record_identity,
    ) in enumerate(
        validation_dataset,
        start=1,
    ):
        nig_parameters = np.asarray(model(model_inputs, training=False), np.float64)
        if (
            nig_parameters.shape != (len(normalized_log_density), 4)
            or not np.isfinite(nig_parameters).all()
        ):
            raise RuntimeError(f"invalid validation prediction in batch {batch_number}")
        normalized_log_density_batches.append(
            np.asarray(
                normalized_log_density,
                np.float64,
            )
        )
        nig_parameter_batches.append(nig_parameters)
        validation_block_batches.append(
            np.asarray(
                record_identity["block_id"],
                np.int32,
            )
        )
        satellite_batches.append(
            np.asarray(
                record_identity["satellite_id"],
                np.int32,
            )
        )
        if (
            batch_number == 1
            or batch_number % 20 == 0
            or batch_number == validation_batch_count
        ):
            print(
                f"[validation] {batch_number}/{validation_batch_count}",
                flush=True,
            )
    normalized_log_density = np.concatenate(normalized_log_density_batches)
    nig_parameters = np.concatenate(nig_parameter_batches)
    validation_block_id = np.concatenate(validation_block_batches)
    satellite_id = np.concatenate(satellite_batches)
    validation_block_names = list(dataset_metadata["validation_block_counts"])
    validation_block_metrics = {
        block_name: _compute_metrics(
            normalized_log_density[validation_block_id == block_index],
            nig_parameters[validation_block_id == block_index],
            log_density_mean,
            log_density_std,
        )
        for block_index, block_name in enumerate(validation_block_names)
    }
    mission_metrics = {
        MISSION_NAMES.get(
            int(identifier), f"mission-{int(identifier)}"
        ): _compute_metrics(
            normalized_log_density[satellite_id == identifier],
            nig_parameters[satellite_id == identifier],
            log_density_mean,
            log_density_std,
        )
        for identifier in np.unique(satellite_id)
    }
    validation_report = {
        "status": "VALIDATION_COMPLETE",
        "evaluation_benchmarks_read": False,
        "checkpoint": str(checkpoint_path),
        "selected_epoch": int(training_audit["selected_epoch"]),
        "selected_validation_panel_edl_loss": float(
            training_audit["selected_validation_panel_edl_loss"]
        ),
        "records": len(normalized_log_density),
        "all_rows": _compute_metrics(
            normalized_log_density,
            nig_parameters,
            log_density_mean,
            log_density_std,
        ),
        "block_macro": _mean_metrics(list(validation_block_metrics.values())),
        "by_block": validation_block_metrics,
        "by_mission": mission_metrics,
    }
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "validation_metrics.json").write_text(
        json.dumps(validation_report, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"[saved] {output_dir / 'validation_metrics.json'}", flush=True)
    return validation_report
