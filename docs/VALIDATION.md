# Validation protocol

## Dataset separation

Training and validation intervals are temporally disjoint, with causal-history
guards around validation intervals. Formal cases are not read by the training
or checkpoint-selection code.

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

For each training run, formal results are generated only after its checkpoint
is fixed and cannot retroactively change that checkpoint. Release designation
is recorded separately from within-run checkpoint selection.
