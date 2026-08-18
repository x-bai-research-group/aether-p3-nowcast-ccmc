# Contributing

Changes to the physical input contract, network, loss, validation panels, or
checkpoint rule require a new model version and a documented scientific
validation. Formal-test results must not be used to select those changes.

Before proposing a change, run:

```bash
scripts/run_checks.sh
```

Do not commit training data, third-party space-weather archives, Orekit data,
model weights, or generated NetCDF files without explicit redistribution
approval.
