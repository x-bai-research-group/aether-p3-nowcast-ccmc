# Released model files

This directory contains the AETHER-P³ Nowcast model and the quantities needed
to reproduce its predictions:

- `model.weights.h5`: neural-network weights;
- `normalization.npz`: feature and target normalization calculated from the
  training data;
- `metadata.json`: model structure, input definition, selected random seed,
  validation objective, data scope, software version, and weight checksum;
- `dataset_metadata.json`: training and validation record counts and the
  associated data definition.

The checkpoint was selected by validation panel-balanced EDL loss within its
training run. The 12 evaluation benchmarks did not determine the checkpoint
epoch within any individual run. After every seed-specific checkpoint had been
fixed, benchmark results and validation behavior were considered together when
seed 20 was selected from the trained random seeds. The benchmarks are
therefore reported as evaluation cases rather than as an untouched independent
test set for the final model choice.
