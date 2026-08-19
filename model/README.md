# Model artifacts

The deployment bundle contains the frozen AETHER-P3 Nowcast model:

- `model.weights.h5`: deployed AETHER-P3 Nowcast weights;
- `normalization.npz`: training-only feature and target normalization;
- `metadata.json`: architecture, input contract, selected seed, validation
  objective, training-data scope, and release version;
- `dataset_metadata.json`: immutable source dataset contract and split counts.

The checkpoint was selected by validation panel-balanced EDL loss within its
training run. Formal-test performance did not select or replace the
checkpoint.
