# Reference example

`input/preprocessed_example.npz` contains eight fully assembled 342-dimensional
model-input records at one UTC. It contains no original AE or solar-wind source
records. From the repository root, the recommended frozen-inference test is:

```bash
./scripts/run_example.sh
```

This command installs the declared environment when necessary, performs
inference, and verifies the result against the committed reference NetCDF.

`input/small_grid.json` remains a minimal request for testing the complete
production feature-generation path after the full driver archive has been
installed:

```bash
aether-p3-nowcast grid \
  --config examples/input/small_grid.json \
  --utc 2024-05-28T12:00:00Z \
  --output-dir output/example \
  --batch-size 8 \
  --workers 2
```

The committed reference NetCDF is stored in `examples/output`; the one-command
test writes a new copy under a unique directory below `output/` because
existing files are never overwritten. The production grid remains defined by
`config/production.json`. Output variables and units are documented in
[`docs/OUTPUT_NETCDF.md`](../docs/OUTPUT_NETCDF.md).
