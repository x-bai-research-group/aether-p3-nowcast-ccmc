import json
from pathlib import Path

from aether_p3_nowcast import (
    MODEL_NAME,
    MODEL_PARAMETER_COUNT,
    MODEL_VERSION,
)
from aether_p3_nowcast.contract import CONTRACT_ID, FEATURE_COUNT
from aether_p3_nowcast.inference import NowcastModel


def test_deployment_artifact_is_complete_and_loadable():
    root = Path(__file__).resolve().parents[1] / "model"
    required_files = (
        root / "model.weights.h5",
        root / "normalization.npz",
        root / "metadata.json",
    )
    assert all(path.is_file() for path in required_files)

    metadata = json.loads((root / "metadata.json").read_text(encoding="utf-8"))
    assert metadata["model_name"] == MODEL_NAME
    assert metadata["model_version"] == MODEL_VERSION
    assert metadata["feature_contract"] == CONTRACT_ID
    assert metadata["feature_count"] == FEATURE_COUNT
    assert metadata["parameter_count"] == MODEL_PARAMETER_COUNT
    assert metadata["output"] == ["gamma", "nu", "alpha", "beta"]
    assert metadata["checkpoint_selection_used_evaluation_benchmarks"] is False
    assert metadata["evaluation_benchmark_case_count"] == 12
    assert metadata["release_realization_selection"] == {
        "method": "balanced comparison across trained seeds",
        "used_evaluation_benchmarks": True,
    }

    model = NowcastModel(root)
    assert model.model.count_params() == MODEL_PARAMETER_COUNT
