# Validation and evaluation

## Temporal separation

Training and validation intervals are disjoint. A 48-hour guard surrounds each
validation and evaluation interval, matching the longest AE/Dst memory used by
the model. This prevents observations inside a held-out interval from entering
the history of a training record.

The validation set contains multiple time blocks spanning different solar
conditions, geomagnetic activity levels, satellites, altitudes, and phases of
the solar cycle. Each block contributes equally to checkpoint selection,
regardless of its number of observations.

## Checkpoint selection

For every epoch, the normal-inverse-gamma evidential loss is averaged within
each validation block. The checkpoint score is the unweighted mean of these
block losses. The selected checkpoint is the epoch with the lowest score.

RE, correlation, RMSE, MACE, and 95% coverage describe model behavior but do
not replace the evidential validation loss as the checkpoint criterion.
Evaluation-benchmark cases are not used to choose an epoch.

## Accuracy metrics

For observed density \(\rho_i\) and prediction \(\hat{\rho}_i\):

\[
\mathrm{RE}
=\frac{1}{N}\sum_i
\left|\frac{\hat{\rho}_i-\rho_i}{\rho_i}\right|,
\qquad
\mathrm{RMSE}
=\sqrt{\frac{1}{N}\sum_i(\hat{\rho}_i-\rho_i)^2}.
\]

Pearson \(R\) measures agreement in the temporal variation of physical
density. RE, \(R\), and RMSE are interpreted together because they emphasize
different error properties.

## Uncertainty metrics

Student-t coverage is evaluated at nominal central interval probabilities

\[
0.05,\ 0.10,\ 0.20,\ldots,\ 0.90,\ 0.95,\ 0.99.
\]

MACE is the mean absolute difference between nominal and empirical coverage
over those levels. Smaller MACE indicates better calibration over the full
predictive distribution. T95 is the empirical coverage of the nominal 95%
interval; a well-calibrated value is close to 0.95.

MACE and T95 must be reported together. T95 alone can be close to 0.95 even
when the remaining predictive intervals are poorly calibrated.

## Evaluation benchmarks and released seed

Twelve satellite cases are used as evaluation benchmarks. They are excluded
from model fitting and from checkpoint selection within each seed. After all
seed-specific checkpoints were fixed, benchmark behavior was considered
together with validation performance when seed 20 was selected for release.

The benchmark cases therefore measure useful out-of-sample behavior, but they
are not described as an untouched independent test set after final seed
selection.
