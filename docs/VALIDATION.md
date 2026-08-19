# Validation protocol

## Dataset separation

Training and validation intervals are temporally disjoint, with causal-history
guards around validation and evaluation-benchmark intervals. The 12 evaluation
benchmark cases are excluded from model fitting and from the checkpoint
selection performed within each random-seed training run.

## Checkpoint selection

Each epoch is evaluated on every validation block. The single checkpoint
objective is the unweighted mean of block-level full NIG-EDL losses. Accuracy
and uncertainty diagnostics do not replace this objective.

## Reported metrics

- mean absolute relative error (RE);
- Pearson correlation (R);
- physical-density RMSE;
- mean absolute calibration error (MACE);
- Student-t 95% coverage (T95).

MACE and T95 must be interpreted together. A nominal T95 close to 0.95 does
not establish calibration across the full predictive distribution.

For each training run, evaluation-benchmark results are generated only after
its checkpoint is fixed and cannot retroactively change that checkpoint. The
final deployed realization is a separate selection: benchmark results were
reviewed as part of a balanced comparison across trained seeds when seed 20
was chosen for release. The 12 cases are therefore reported as evaluation
benchmarks, not as an untouched independent test set after all realization
selection was complete.
