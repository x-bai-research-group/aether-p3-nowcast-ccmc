# User guide

## Inspect the input contract

```bash
aether-p3-nowcast contract
```

## Verify a training dataset

```bash
aether-p3-nowcast check --dataset-root /path/to/training_dataset
```

## Train the model

```bash
scripts/run_training.sh /path/to/training_dataset runs/training
```

## Install the selected model

```bash
aether-p3-nowcast install-model \
  --output-root runs/training \
  --dataset-root /path/to/training_dataset \
  --model-root model
```

## Generate a grid

```bash
scripts/run_grid_nowcast.sh 2024-05-11T12:00:00Z output
```

The UTC must fall on a five-minute boundary. Existing outputs are never
overwritten.
