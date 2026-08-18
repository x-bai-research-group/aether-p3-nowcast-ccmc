"""Load a released model and convert NIG outputs to physical density."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from . import MODEL_NAME, MODEL_PARAMETER_COUNT, MODEL_VERSION
from .contract import CONTRACT_ID, FEATURE_COUNT, FEATURE_SLICES
from .network import NetworkConfig, build_model


def group_features(flat_features: np.ndarray) -> dict[str, np.ndarray]:
    return {
        feature_slice.name: flat_features[
            :, feature_slice.start : feature_slice.stop
        ].reshape((len(flat_features), *feature_slice.shape))
        for feature_slice in FEATURE_SLICES
    }


class NowcastModel:
    """Frozen AETHER-P3 Nowcast model and training-only normalization."""

    def __init__(self, model_root: Path):
        import tensorflow as tf

        tf.keras.mixed_precision.set_global_policy("float32")
        model_root = Path(model_root).resolve()
        metadata = json.loads(
            (model_root / "metadata.json").read_text(encoding="utf-8")
        )
        if (
            metadata.get("model_name") != MODEL_NAME
            or metadata.get("model_version") != MODEL_VERSION
            or metadata.get("feature_contract") != CONTRACT_ID
            or int(metadata.get("feature_count", -1)) != FEATURE_COUNT
            or int(metadata.get("parameter_count", -1)) != MODEL_PARAMETER_COUNT
        ):
            raise ValueError("model metadata does not describe AETHER-P3 Nowcast")
        with np.load(model_root / "normalization.npz") as normalization:
            self.x_mean = np.asarray(normalization["x_mean"], np.float32)
            self.x_std = np.asarray(normalization["x_std"], np.float32)
            self.y_mean = float(np.asarray(normalization["y_mean"]).reshape(()))
            self.y_std = float(np.asarray(normalization["y_std"]).reshape(()))
        if (
            self.x_mean.shape != (FEATURE_COUNT,)
            or self.x_std.shape != (FEATURE_COUNT,)
            or not np.isfinite(self.x_mean).all()
            or not np.isfinite(self.x_std).all()
            or np.any(self.x_std <= 0.0)
            or not np.isfinite([self.y_mean, self.y_std]).all()
            or self.y_std <= 0.0
        ):
            raise ValueError("model normalization is invalid")
        self.model = build_model(NetworkConfig(**metadata["network"]))
        self.model.load_weights(model_root / "model.weights.h5")
        self.metadata = metadata

    def predict_parameters(
        self, features: np.ndarray, *, batch_size: int = 4096
    ) -> np.ndarray:
        if (
            isinstance(batch_size, bool)
            or not isinstance(batch_size, int)
            or batch_size <= 0
        ):
            raise ValueError("batch_size must be a positive integer")
        features = np.asarray(features, np.float32)
        if features.ndim != 2 or features.shape[1] != FEATURE_COUNT:
            raise ValueError(f"features must have shape (records, {FEATURE_COUNT})")
        if not np.isfinite(features).all():
            raise ValueError("features contain a non-finite value")
        normalized = (features - self.x_mean) / self.x_std
        output = np.empty((len(features), 4), np.float32)
        for start in range(0, len(features), batch_size):
            stop = min(start + batch_size, len(features))
            prediction = np.asarray(
                self.model(group_features(normalized[start:stop]), training=False),
                np.float32,
            )
            if (
                prediction.shape != (stop - start, 4)
                or not np.isfinite(prediction).all()
            ):
                raise RuntimeError("model produced invalid NIG parameters")
            output[start:stop] = prediction
        return output

    def physical_fields(self, parameters: np.ndarray) -> dict[str, np.ndarray]:
        from scipy.stats import t as student_t

        nig_parameters = np.asarray(parameters, np.float64)
        if (
            nig_parameters.ndim != 2
            or nig_parameters.shape[1] != 4
            or not np.isfinite(nig_parameters).all()
        ):
            raise ValueError(
                "parameters must be a finite array with shape (records, 4)"
            )
        gamma = nig_parameters[:, 0]
        nu = nig_parameters[:, 1]
        alpha = nig_parameters[:, 2]
        beta = nig_parameters[:, 3]
        if np.any(nu <= 0.0) or np.any(alpha <= 1.0) or np.any(beta <= 0.0):
            raise ValueError("NIG parameters require nu > 0, alpha > 1, and beta > 0")
        predictive_scale = np.sqrt(beta * (1.0 + nu) / (nu * alpha))
        interval_radius_95 = (
            student_t.ppf(0.975, 2.0 * alpha) * predictive_scale
        )

        def physical_density(normalized_log10_density):
            return np.power(
                10.0,
                normalized_log10_density * self.y_std + self.y_mean,
            ).astype(np.float32)

        physical_fields = {
            "density": physical_density(gamma),
            "density_lower_95": physical_density(gamma - interval_radius_95),
            "density_upper_95": physical_density(gamma + interval_radius_95),
            "aleatoric_std_log10": (np.sqrt(beta / (alpha - 1.0)) * self.y_std).astype(
                np.float32
            ),
            "epistemic_std_log10": (
                np.sqrt(beta / (nu * (alpha - 1.0))) * self.y_std
            ).astype(np.float32),
            "gamma": nig_parameters[:, 0].astype(np.float32),
            "nu": nig_parameters[:, 1].astype(np.float32),
            "alpha": nig_parameters[:, 2].astype(np.float32),
            "beta": nig_parameters[:, 3].astype(np.float32),
        }
        if not all(np.isfinite(values).all() for values in physical_fields.values()):
            raise RuntimeError("physical output contains a non-finite value")
        if (
            np.any(physical_fields["density_lower_95"] <= 0.0)
            or np.any(physical_fields["density"] <= 0.0)
            or np.any(physical_fields["density_upper_95"] <= 0.0)
            or np.any(
                physical_fields["density_lower_95"] > physical_fields["density"]
            )
            or np.any(
                physical_fields["density"] > physical_fields["density_upper_95"]
            )
        ):
            raise RuntimeError("physical density interval is invalid")
        return physical_fields
