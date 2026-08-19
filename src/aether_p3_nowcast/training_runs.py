"""Run one or more independently seeded training configurations."""

from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path

from . import MODEL_NAME, MODEL_PARAMETER_COUNT, MODEL_VERSION
from .contract import CONTRACT_ID, FEATURE_COUNT
from .training import train
from .validation import evaluate


def _load(path: Path) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def load_seeds(path: Path) -> tuple[int, ...]:
    configured_seeds = _load(path).get("seeds")
    if not isinstance(configured_seeds, list) or not configured_seeds:
        raise ValueError("seed configuration must contain a non-empty 'seeds' list")
    seeds = tuple(int(seed) for seed in configured_seeds)
    if any(value < 0 for value in seeds) or len(set(seeds)) != len(seeds):
        raise ValueError("seeds must be unique non-negative integers")
    return seeds


def _build_training_configuration(
    training_template: dict,
    dataset_root: Path,
    run_dir: Path,
    seed: int,
) -> dict:
    protected = {"dataset_root", "run_dir", "seed"} & set(training_template)
    if protected:
        raise ValueError(
            f"training template must not define run-specific keys: {sorted(protected)}"
        )
    return {
        "dataset_root": str(dataset_root.resolve()),
        "run_dir": str(run_dir.resolve()),
        "seed": seed,
        **training_template,
    }


def run(
    dataset_root: Path,
    output_root: Path,
    template_path: Path,
    seeds_path: Path,
    *,
    validation_batch_size: int = 4096,
) -> None:
    """Train every configured run and compute its validation metrics."""
    dataset_root = Path(dataset_root).resolve()
    output_root = Path(output_root).resolve()
    training_template = _load(template_path)
    seeds = load_seeds(seeds_path)
    configuration_directory = output_root / "configs"
    model_directory = output_root / "models"
    validation_directory = output_root / "validation"
    configuration_directory.mkdir(parents=True, exist_ok=True)
    model_directory.mkdir(parents=True, exist_ok=True)
    validation_directory.mkdir(parents=True, exist_ok=True)
    training_run_manifest = {
        "status": "AETHER_P3_TRAINING_RUNS_FROZEN",
        "model_name": MODEL_NAME,
        "model_version": MODEL_VERSION,
        "seeds": list(seeds),
        "dataset_root": str(dataset_root),
        "checkpoint_rule": "minimum validation-panel-balanced full NIG-EDL loss",
        "validation_candidate_rule": "minimum selected validation EDL loss",
        "evaluation_benchmarks_used": False,
    }
    manifest_path = output_root / "training_runs_manifest.json"
    if manifest_path.is_file() and _load(manifest_path) != training_run_manifest:
        raise RuntimeError(
            "existing training-run manifest differs from the configuration"
        )
    manifest_path.write_text(
        json.dumps(training_run_manifest, indent=2) + "\n",
        encoding="utf-8",
    )

    seed_count = len(seeds)
    for run_number, seed in enumerate(seeds, start=1):
        run_dir = model_directory / f"seed{seed}"
        config_path = configuration_directory / f"seed{seed}.json"
        training_configuration = _build_training_configuration(
            training_template,
            dataset_root,
            run_dir,
            seed,
        )
        if config_path.is_file() and _load(config_path) != training_configuration:
            raise RuntimeError(f"seed {seed} configuration changed")
        config_path.write_text(
            json.dumps(training_configuration, indent=2) + "\n",
            encoding="utf-8",
        )
        audit_path = run_dir / "TRAINING_AUDIT.json"
        if audit_path.is_file():
            training_audit = _load(audit_path)
            if training_audit["configuration"] != training_configuration:
                raise RuntimeError(f"completed seed {seed} used another configuration")
            print(
                f"[skip training {run_number}/{seed_count}] seed={seed}",
                flush=True,
            )
        else:
            if run_dir.exists() and any(run_dir.iterdir()):
                raise RuntimeError(
                    f"incomplete seed directory was preserved: {run_dir}"
                )
            print(f"[train {run_number}/{seed_count}] seed={seed}", flush=True)
            train(config_path)
        validation_output_directory = validation_directory / f"seed{seed}"
        validation_metrics_path = (
            validation_output_directory / "validation_metrics.json"
        )
        if validation_metrics_path.is_file():
            print(
                f"[skip validation {run_number}/{seed_count}] seed={seed}",
                flush=True,
            )
        else:
            if validation_output_directory.exists() and any(
                validation_output_directory.iterdir()
            ):
                raise RuntimeError(
                    "incomplete validation directory was preserved: "
                    f"{validation_output_directory}"
                )
            evaluate(
                run_dir,
                dataset_root,
                validation_output_directory,
                batch_size=validation_batch_size,
            )
    audit(output_root)


def audit(output_root: Path) -> dict:
    """Identify a validation-preferred seed without reading benchmark cases."""
    output_root = Path(output_root).resolve()
    training_run_manifest = _load(output_root / "training_runs_manifest.json")
    seeds = tuple(int(seed) for seed in training_run_manifest.get("seeds", []))
    if not seeds or training_run_manifest.get("evaluation_benchmarks_used") is not False:
        raise RuntimeError("training-run manifest is invalid")
    run_summaries = []
    common_training_configuration = None
    for seed in seeds:
        training_audit = _load(
            output_root / "models" / f"seed{seed}" / "TRAINING_AUDIT.json"
        )
        validation_report = _load(
            output_root / "validation" / f"seed{seed}" / "validation_metrics.json"
        )
        if validation_report.get("evaluation_benchmarks_read") is not False:
            raise RuntimeError(
                f"seed {seed} validation read evaluation benchmarks"
            )
        shared_configuration = dict(training_audit["configuration"])
        shared_configuration.pop("seed")
        shared_configuration.pop("run_dir")
        if common_training_configuration is None:
            common_training_configuration = shared_configuration
        elif shared_configuration != common_training_configuration:
            raise RuntimeError(f"seed {seed} differs beyond seed and run directory")
        run_summaries.append(
            {
                "seed": seed,
                "selected_epoch": int(training_audit["selected_epoch"]),
                "validation_edl_loss": float(
                    training_audit["selected_validation_panel_edl_loss"]
                ),
                "block_macro": validation_report["block_macro"],
                "all_rows": validation_report["all_rows"],
                "checkpoint": training_audit["checkpoint"],
            }
        )
    selected_run = min(
        run_summaries,
        key=lambda run_summary: run_summary["validation_edl_loss"],
    )
    selection_report = {
        "status": "VALIDATION_CANDIDATE_SELECTED",
        "evaluation_benchmarks_used": False,
        "selection_rule": training_run_manifest["validation_candidate_rule"],
        "selected": selected_run,
        "runs": run_summaries,
    }
    (output_root / "training_runs_audit.json").write_text(
        json.dumps(selection_report, indent=2) + "\n",
        encoding="utf-8",
    )
    lines = [
        "# AETHER-P3 Nowcast training-run validation audit",
        "",
        "> No evaluation-benchmark result is read or used by this selection.",
        "",
        f"- Validation-preferred seed: `{selected_run['seed']}`",
        f"- Selected epoch: `{selected_run['selected_epoch']}`",
        f"- Validation EDL loss: `{selected_run['validation_edl_loss']:.8f}`",
        "",
        "| seed | epoch | validation EDL | mean validation-block RE | R | "
        "RMSE | MACE | T95 |",
        "|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for run_summary in run_summaries:
        validation_metrics = run_summary["block_macro"]
        lines.append(
            f"| {run_summary['seed']} | {run_summary['selected_epoch']} | "
            f"{run_summary['validation_edl_loss']:.8f} | "
            f"{validation_metrics['relative_error']:.6f} | "
            f"{validation_metrics['pearson_r']:.6f} | "
            f"{validation_metrics['physical_rmse']:.6e} | "
            f"{validation_metrics['mace']:.6f} | "
            f"{validation_metrics['student_t_95_coverage']:.6f} |"
        )
    (output_root / "training_runs_audit.md").write_text(
        "\n".join(lines) + "\n",
        encoding="utf-8",
    )
    print(f"[selected] seed={selected_run['seed']}", flush=True)
    print(f"[saved] {output_root / 'training_runs_audit.md'}", flush=True)
    return selection_report


def install(output_root: Path, dataset_root: Path, model_root: Path) -> None:
    """Install the validation-selected checkpoint as the deployment artifact."""
    output_root = Path(output_root).resolve()
    dataset_root = Path(dataset_root).resolve()
    model_root = Path(model_root).resolve()
    selection = _load(output_root / "training_runs_audit.json")
    if (
        selection.get("status") != "VALIDATION_CANDIDATE_SELECTED"
        or selection.get("evaluation_benchmarks_used") is not False
    ):
        raise RuntimeError("candidate selection is not validation-only")
    selected = selection["selected"]
    checkpoint = Path(selected["checkpoint"])
    if not checkpoint.is_file():
        raise FileNotFoundError(checkpoint)
    normalization = dataset_root / "normalization.npz"
    dataset_metadata = dataset_root / "metadata.json"
    if not normalization.is_file() or not dataset_metadata.is_file():
        raise FileNotFoundError("training normalization or metadata is missing")
    model_root.mkdir(parents=True, exist_ok=True)
    destinations = {
        model_root / "model.weights.h5": checkpoint,
        model_root / "normalization.npz": normalization,
        model_root / "dataset_metadata.json": dataset_metadata,
    }
    existing = [str(path) for path in destinations if path.exists()]
    if existing:
        raise FileExistsError(f"deployment artifacts already exist: {existing}")
    for destination, source in destinations.items():
        shutil.copy2(source, destination)
    checkpoint_filename = "model.weights.h5"
    checkpoint_sha256 = hashlib.sha256(
        (model_root / checkpoint_filename).read_bytes()
    ).hexdigest()
    metadata = {
        "model_name": MODEL_NAME,
        "model_version": MODEL_VERSION,
        "feature_contract": CONTRACT_ID,
        "feature_count": FEATURE_COUNT,
        "parameter_count": MODEL_PARAMETER_COUNT,
        "selected_seed": int(selected["seed"]),
        "selected_epoch": int(selected["selected_epoch"]),
        "selected_validation_edl_loss": float(selected["validation_edl_loss"]),
        "checkpoint_filename": checkpoint_filename,
        "checkpoint_sha256": checkpoint_sha256,
        "checkpoint_selection_used_formal_tests": False,
        "checkpoint_selection_used_evaluation_benchmarks": False,
        "evaluation_benchmark_case_count": 12,
        "release_realization_selection": {
            "method": "minimum validation EDL loss across trained seeds",
            "selected_seed": int(selected["seed"]),
            "used_formal_tests": False,
            "used_evaluation_benchmarks": False,
        },
        "network": _load(output_root / "configs" / f"seed{selected['seed']}.json")[
            "network"
        ],
        "output": ["gamma", "nu", "alpha", "beta"],
    }
    (model_root / "metadata.json").write_text(
        json.dumps(metadata, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"[installed] {model_root}", flush=True)
