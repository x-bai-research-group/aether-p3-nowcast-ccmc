"""Small command-line interface for training and serving AETHER-P3 Nowcast."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from . import MODEL_NAME
from .contract import FEATURE_COUNT, FEATURE_NAMES, FEATURE_SLICES


def parser() -> argparse.ArgumentParser:
    argument_parser = argparse.ArgumentParser(prog="aether-p3-nowcast")
    commands = argument_parser.add_subparsers(dest="command", required=True)

    contract = commands.add_parser("contract", help="Print the fixed input contract.")
    contract.add_argument("--output", type=Path)

    check = commands.add_parser(
        "check",
        help="Validate the dataset, network, and frozen training template.",
    )
    check.add_argument("--dataset-root", type=Path, required=True)
    check.add_argument(
        "--training-config",
        type=Path,
        default=Path("config/training.json"),
    )

    train = commands.add_parser("train", help="Train one independently seeded model.")
    train.add_argument("--config", type=Path, required=True)

    training_runs = commands.add_parser(
        "train-runs",
        help="Train one or more seeds listed in a configuration file.",
    )
    training_runs.add_argument("--dataset-root", type=Path, required=True)
    training_runs.add_argument("--output-root", type=Path, required=True)
    training_runs.add_argument(
        "--training-config",
        type=Path,
        default=Path("config/training.json"),
    )
    training_runs.add_argument(
        "--seeds-config",
        type=Path,
        default=Path("config/seeds.json"),
    )
    training_runs.add_argument("--validation-batch-size", type=int, default=4096)

    audit = commands.add_parser(
        "audit-runs",
        help="Repeat the validation-only seed-candidate audit.",
    )
    audit.add_argument("--output-root", type=Path, required=True)

    install = commands.add_parser(
        "install-model",
        help="Install the validation-selected candidate artifacts.",
    )
    install.add_argument("--output-root", type=Path, required=True)
    install.add_argument("--dataset-root", type=Path, required=True)
    install.add_argument("--model-root", type=Path, default=Path("model"))

    validation = commands.add_parser(
        "evaluate-validation",
        help="Evaluate one validation-frozen checkpoint.",
    )
    validation.add_argument("--run-dir", type=Path, required=True)
    validation.add_argument("--dataset-root", type=Path, required=True)
    validation.add_argument("--output-dir", type=Path, required=True)
    validation.add_argument("--batch-size", type=int, default=4096)

    grid = commands.add_parser("grid", help="Write one global 3-D NetCDF nowcast.")
    grid.add_argument("--config", type=Path, default=Path("config/production.json"))
    grid.add_argument("--utc", required=True)
    grid.add_argument("--output-dir", type=Path, required=True)
    grid.add_argument("--batch-size", type=int, default=4096)
    grid.add_argument("--workers", type=int, default=8)

    return argument_parser


def _contract() -> dict:
    return {
        "model_name": MODEL_NAME,
        "feature_count": FEATURE_COUNT,
        "feature_names": list(FEATURE_NAMES),
        "groups": [
            {
                "name": feature_slice.name,
                "start": feature_slice.start,
                "stop": feature_slice.stop,
                "shape": list(feature_slice.shape),
            }
            for feature_slice in FEATURE_SLICES
        ],
        "output": ["gamma", "nu", "alpha", "beta"],
    }


def main() -> None:
    args = parser().parse_args()
    if args.command == "contract":
        text = json.dumps(_contract(), indent=2) + "\n"
        if args.output is None:
            print(text, end="")
        else:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(text, encoding="utf-8")
        return
    if args.command == "train":
        from .training import train

        train(args.config)
        return
    if args.command == "check":
        from .network import NetworkConfig, build_model
        from .records import validate_dataset

        metadata = validate_dataset(args.dataset_root)
        training = json.loads(args.training_config.read_text(encoding="utf-8"))
        model = build_model(NetworkConfig(**training["network"]))
        report = {
            "status": "READY",
            "model_name": MODEL_NAME,
            "feature_count": FEATURE_COUNT,
            "parameter_count": model.count_params(),
            "training_rows": int(metadata["splits"]["train"]["records"]),
            "validation_rows": int(metadata["splits"]["val"]["records"]),
            "evaluation_benchmarks_used": False,
        }
        print(json.dumps(report, indent=2))
        return
    if args.command == "train-runs":
        from .training_runs import run

        run(
            args.dataset_root,
            args.output_root,
            args.training_config,
            args.seeds_config,
            validation_batch_size=args.validation_batch_size,
        )
        return
    if args.command == "audit-runs":
        from .training_runs import audit

        audit(args.output_root)
        return
    if args.command == "install-model":
        from .training_runs import install

        install(args.output_root, args.dataset_root, args.model_root)
        return
    if args.command == "evaluate-validation":
        from .validation import evaluate

        evaluate(
            args.run_dir,
            args.dataset_root,
            args.output_dir,
            batch_size=args.batch_size,
        )
        return
    if args.command == "grid":
        from .grid import generate

        generate(
            args.config,
            args.utc,
            args.output_dir,
            batch_size=args.batch_size,
            workers=args.workers,
        )
        return
    raise AssertionError(args.command)
