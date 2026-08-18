# Reference example

`input/small_grid.json` is a minimal executable grid request. It produces eight
grid points at one UTC time while using the same model and driver pipeline as
the production grid:

```bash
aether-p3-nowcast grid \
  --config examples/input/small_grid.json \
  --utc 2024-05-28T12:00:00Z \
  --output-dir examples/output \
  --batch-size 8 \
  --workers 2
```

The corresponding NetCDF file is stored in `examples/output`. The production
grid remains defined by `config/production.json`. Output variables and units
are documented in [`docs/OUTPUT_NETCDF.md`](../docs/OUTPUT_NETCDF.md).
