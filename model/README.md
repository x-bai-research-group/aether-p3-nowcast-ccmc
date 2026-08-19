# Model artifacts

The deployment bundle contains the frozen AETHER-P3 Nowcast model:

- `model.weights.h5`: deployed AETHER-P3 Nowcast weights;
- `normalization.npz`: training-only feature and target normalization;
- `metadata.json`: architecture, input contract, selected seed, validation
  objective, training-data scope, release version, checkpoint filename, and
  checkpoint SHA-256;
- `dataset_metadata.json`: immutable source dataset contract and split counts.

The checkpoint was selected by validation panel-balanced EDL loss within its
training run. The 12 evaluation benchmark cases did not select or replace that
within-run checkpoint. Their results were reviewed when seed 20 was chosen as
the final deployed realization, so they are not described as an untouched
independent test set for final realization selection. The frozen metadata
records these two decisions separately: checkpoint selection excluded the
evaluation benchmarks, whereas release realization selection used a balanced
comparison across trained seeds.
