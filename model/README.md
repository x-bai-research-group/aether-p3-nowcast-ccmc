# Model artifacts

The deployment bundle contains the release-designated AETHER-P3 Nowcast
seed20 model:

- `model.weights.h5`: deployed AETHER-P3 Nowcast weights;
- `normalization.npz`: training-only feature and target normalization;
- `metadata.json`: architecture, input contract, selected seed, validation
  objective, training-data scope, and release version;
- `dataset_metadata.json`: immutable source dataset contract and split counts.

Within the seed20 training run, the checkpoint was selected by validation
panel-balanced EDL loss. Formal-test performance did not select or replace the
checkpoint.
