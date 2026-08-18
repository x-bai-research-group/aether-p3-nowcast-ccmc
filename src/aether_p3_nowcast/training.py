"""Deterministic full-pass training with one validation-only checkpoint rule."""

from __future__ import annotations

import json
import os
import random
from pathlib import Path

import numpy as np

from . import MODEL_NAME, MODEL_VERSION
from .losses import make_nig_loss, nig_components
from .network import NetworkConfig, build_model
from .records import make_dataset, validate_dataset


def _validate_training_configuration(configuration: dict) -> None:
    seed = configuration["seed"]
    if isinstance(seed, bool) or not isinstance(seed, int) or seed < 0:
        raise ValueError("seed must be a non-negative integer")
    positive_integer_keys = (
        "max_epochs",
        "batch_size",
        "lr_patience",
        "early_stopping_patience",
    )
    for key in positive_integer_keys:
        value = configuration[key]
        if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
            raise ValueError(f"{key} must be a positive integer")
    positive_float_keys = (
        "learning_rate",
        "minimum_learning_rate",
        "clipnorm",
    )
    for key in positive_float_keys:
        value = float(configuration[key])
        if not np.isfinite(value) or value <= 0.0:
            raise ValueError(f"{key} must be finite and positive")
    if float(configuration["minimum_learning_rate"]) > float(
        configuration["learning_rate"]
    ):
        raise ValueError("minimum_learning_rate cannot exceed learning_rate")
    reduction_factor = float(configuration["lr_reduction_factor"])
    if not np.isfinite(reduction_factor) or not 0.0 < reduction_factor < 1.0:
        raise ValueError("lr_reduction_factor must lie between zero and one")
    for key in ("minimum_delta", "weight_decay", "edl_coefficient"):
        value = float(configuration[key])
        if not np.isfinite(value) or value < 0.0:
            raise ValueError(f"{key} must be finite and non-negative")
    if not isinstance(configuration["mixed_precision"], bool):
        raise ValueError("mixed_precision must be true or false")
    if not isinstance(configuration["network"], dict):
        raise ValueError("network must be an object")


def _validation_loss(
    model, validation_dataset, edl_coefficient: float, block_count: int
) -> tuple[float, list[float]]:
    block_loss_totals = np.zeros(block_count, np.float64)
    block_record_counts = np.zeros(block_count, np.int64)
    for model_inputs, normalized_log_density, record_identity in validation_dataset:
        negative_log_likelihood, evidence_penalty = nig_components(
            normalized_log_density, model(model_inputs, training=False),
        )
        record_loss = np.asarray(
            negative_log_likelihood + edl_coefficient * evidence_penalty,
            np.float64,
        )
        block_ids = np.asarray(record_identity["block_id"], np.int32)
        for block_id in np.unique(block_ids):
            if block_id < 0 or block_id >= block_count:
                raise RuntimeError(f"invalid validation block id: {block_id}")
            records_in_block = block_ids == block_id
            block_loss_totals[block_id] += float(
                record_loss[records_in_block].sum()
            )
            block_record_counts[block_id] += int(records_in_block.sum())
    if np.any(block_record_counts == 0):
        raise RuntimeError(
            "empty validation blocks: "
            f"{np.flatnonzero(block_record_counts == 0).tolist()}"
        )
    mean_block_losses = block_loss_totals / block_record_counts
    return float(mean_block_losses.mean()), mean_block_losses.tolist()


def train(config_path: Path) -> dict:
    os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "1")
    os.environ.setdefault("TF_DETERMINISTIC_OPS", "1")
    import tensorflow as tf

    config_path = Path(config_path).resolve()
    training_configuration = json.loads(config_path.read_text(encoding="utf-8"))
    allowed = {
        "dataset_root",
        "run_dir",
        "seed",
        "max_epochs",
        "batch_size",
        "learning_rate",
        "minimum_learning_rate",
        "lr_reduction_factor",
        "lr_patience",
        "early_stopping_patience",
        "minimum_delta",
        "weight_decay",
        "clipnorm",
        "edl_coefficient",
        "mixed_precision",
        "network",
    }
    unknown = sorted(set(training_configuration) - allowed)
    if unknown:
        raise ValueError(f"unknown training keys: {unknown}")
    missing = sorted(allowed - set(training_configuration))
    if missing:
        raise ValueError(f"missing training keys: {missing}")
    _validate_training_configuration(training_configuration)
    dataset_root = Path(training_configuration["dataset_root"]).resolve()
    run_dir = Path(training_configuration["run_dir"]).resolve()
    if run_dir.exists() and any(run_dir.iterdir()):
        raise FileExistsError(f"run directory is not empty: {run_dir}")
    dataset_metadata = validate_dataset(dataset_root)
    block_count = len(dataset_metadata["validation_block_counts"])
    seed = int(training_configuration["seed"])
    random.seed(seed)
    np.random.seed(seed)
    tf.keras.utils.set_random_seed(seed)
    tf.config.experimental.enable_op_determinism()
    precision_policy = (
        "mixed_float16" if training_configuration["mixed_precision"] else "float32"
    )
    tf.keras.mixed_precision.set_global_policy(precision_policy)

    model = build_model(NetworkConfig(**training_configuration["network"]))
    edl_coefficient = float(training_configuration["edl_coefficient"])
    optimizer = tf.keras.optimizers.AdamW(
        learning_rate=float(training_configuration["learning_rate"]),
        weight_decay=float(training_configuration["weight_decay"]),
        clipnorm=float(training_configuration["clipnorm"]),
    )
    model.compile(optimizer=optimizer, loss=make_nig_loss(edl_coefficient))
    training_dataset = make_dataset(
        dataset_root,
        "train",
        batch_size=int(training_configuration["batch_size"]),
    )
    validation_dataset = make_dataset(
        dataset_root,
        "val",
        batch_size=int(training_configuration["batch_size"]),
        include_identity=True,
    )

    run_dir.mkdir(parents=True, exist_ok=True)
    checkpoint_directory = run_dir / "models"
    checkpoint_directory.mkdir()
    best_checkpoint = checkpoint_directory / "best.weights.h5"
    epoch_history = []
    best_validation_loss = float("inf")
    epochs_without_improvement = 0
    epochs_since_lr_reduction = 0
    for epoch in range(1, int(training_configuration["max_epochs"]) + 1):
        training_result = model.fit(training_dataset, epochs=1, verbose=1)
        validation_loss, block_losses = _validation_loss(
            model,
            validation_dataset,
            edl_coefficient,
            block_count,
        )
        validation_improved = validation_loss < best_validation_loss - float(
            training_configuration["minimum_delta"]
        )
        if validation_improved:
            best_validation_loss = validation_loss
            epochs_without_improvement = 0
            epochs_since_lr_reduction = 0
            model.save_weights(best_checkpoint)
        else:
            epochs_without_improvement += 1
            epochs_since_lr_reduction += 1
        current_learning_rate = float(
            tf.keras.backend.get_value(model.optimizer.learning_rate)
        )
        epoch_history.append(
            {
                "epoch": epoch,
                "train_loss": float(training_result.history["loss"][-1]),
                "validation_panel_edl_loss": validation_loss,
                "validation_block_edl_loss": block_losses,
                "learning_rate": current_learning_rate,
                "improved": validation_improved,
            }
        )
        (run_dir / "history.json").write_text(
            json.dumps(epoch_history, indent=2) + "\n",
            encoding="utf-8",
        )
        print(
            f"[validation] epoch={epoch} panel_edl={validation_loss:.8f} "
            f"best={best_validation_loss:.8f} "
            f"epochs_without_improvement={epochs_without_improvement}",
            flush=True,
        )
        if epochs_since_lr_reduction >= int(
            training_configuration["lr_patience"]
        ):
            reduced_learning_rate = max(
                float(training_configuration["minimum_learning_rate"]),
                current_learning_rate
                * float(training_configuration["lr_reduction_factor"]),
            )
            model.optimizer.learning_rate.assign(reduced_learning_rate)
            epochs_since_lr_reduction = 0
            print(
                f"[learning-rate] {current_learning_rate:.3e} -> "
                f"{reduced_learning_rate:.3e}",
                flush=True,
            )
        if epochs_without_improvement >= int(
            training_configuration["early_stopping_patience"]
        ):
            print(f"[early-stop] epoch={epoch}", flush=True)
            break
    if not best_checkpoint.is_file():
        raise RuntimeError("training did not save a validation checkpoint")
    selected_epoch = next(
        epoch_record["epoch"]
        for epoch_record in epoch_history
        if epoch_record["validation_panel_edl_loss"] == best_validation_loss
    )
    training_configuration["dataset_root"] = str(dataset_root)
    training_configuration["run_dir"] = str(run_dir)
    training_audit = {
        "status": "VALIDATION_CHECKPOINT_FROZEN",
        "model_name": MODEL_NAME,
        "model_version": MODEL_VERSION,
        "configuration": training_configuration,
        "dataset_contract": dataset_metadata["contract"],
        "training_rows": int(dataset_metadata["splits"]["train"]["records"]),
        "validation_rows": int(dataset_metadata["splits"]["val"]["records"]),
        "parameter_count": model.count_params(),
        "initialization": "independent seeded initialization from scratch",
        "completed_epochs": len(epoch_history),
        "selected_epoch": selected_epoch,
        "selected_validation_panel_edl_loss": best_validation_loss,
        "checkpoint": str(best_checkpoint),
        "checkpoint_rule": "minimum validation-panel-balanced full NIG-EDL loss",
        "formal_tests_used": False,
        "output": ["gamma", "nu", "alpha", "beta"],
    }
    (run_dir / "TRAINING_AUDIT.json").write_text(
        json.dumps(training_audit, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"[saved] {run_dir / 'TRAINING_AUDIT.json'}", flush=True)
    return training_audit
