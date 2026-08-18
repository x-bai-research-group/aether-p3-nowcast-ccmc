# Contributing

Changes to the physical input contract, network, loss, validation panels, or
checkpoint rule require a new model version and a documented scientific
validation. Formal-test results must not be used to select those changes.

Before proposing a change, run:

```bash
scripts/run_checks.sh
```

Adding or replacing training data, bundled third-party data, model weights, or
reference NetCDF files requires explicit scientific and redistribution
approval.
