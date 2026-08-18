"""Accuracy and predictive-uncertainty metrics."""

from __future__ import annotations

import numpy as np


MACE_LEVELS = np.array(
    [0.05, 0.10, 0.20, 0.30, 0.40, 0.50, 0.60, 0.70, 0.80, 0.90, 0.95, 0.99],
    dtype=np.float64,
)


def accuracy_metrics(
    observed_density: np.ndarray,
    predicted_density: np.ndarray,
) -> dict[str, float | int]:
    observed_density = np.asarray(observed_density, np.float64)
    predicted_density = np.asarray(predicted_density, np.float64)
    valid_records = (
        np.isfinite(observed_density)
        & np.isfinite(predicted_density)
        & (observed_density > 0.0)
        & (predicted_density > 0.0)
    )
    if not np.any(valid_records):
        return {
            "records": 0,
            "relative_error": None,
            "pearson_r": None,
            "physical_rmse": None,
        }
    observed_density = observed_density[valid_records]
    predicted_density = predicted_density[valid_records]
    relative_residual = (predicted_density - observed_density) / observed_density
    correlation = (
        float(np.corrcoef(observed_density, predicted_density)[0, 1])
        if len(observed_density) > 1
        else None
    )
    return {
        "records": int(len(observed_density)),
        "relative_error": float(np.mean(np.abs(relative_residual))),
        "pearson_r": correlation,
        "physical_rmse": float(
            np.sqrt(np.mean(np.square(predicted_density - observed_density)))
        ),
    }


def predictive_uncertainty_metrics(
    normalized_log_density: np.ndarray,
    nig_parameters: np.ndarray,
) -> dict[str, float]:
    from scipy.stats import t as student_t

    normalized_log_density = np.asarray(
        normalized_log_density,
        np.float64,
    ).reshape(-1)
    gamma, nu, alpha, beta = np.asarray(nig_parameters, np.float64).T
    nu = np.maximum(nu, 1.0e-12)
    alpha = np.maximum(alpha, 1.0 + 1.0e-12)
    beta = np.maximum(beta, 1.0e-12)
    degrees = 2.0 * alpha
    scale = np.sqrt(beta * (1.0 + nu) / (nu * alpha))
    absolute_residual = np.abs(normalized_log_density - gamma)
    empirical_coverages = []
    for nominal_coverage in MACE_LEVELS:
        interval_radius = (
            student_t.ppf(
                (1.0 + nominal_coverage) / 2.0,
                degrees,
            )
            * scale
        )
        empirical_coverages.append(float(np.mean(absolute_residual <= interval_radius)))
    empirical_coverage_array = np.asarray(empirical_coverages)
    return {
        "mace": float(np.mean(np.abs(empirical_coverage_array - MACE_LEVELS))),
        "student_t_95_coverage": empirical_coverages[MACE_LEVELS.tolist().index(0.95)],
        "coverage_levels": MACE_LEVELS.tolist(),
        "empirical_coverages": empirical_coverages,
    }
