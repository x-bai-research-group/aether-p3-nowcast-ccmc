# Runtime data

Place the required space-weather drivers under:

```text
data/space-weather/
```

Orekit runtime data are expected under `data/orekit-data/`. The required
products, causality rules, and file names are listed in
[`docs/INPUTS_AND_LATENCY.md`](../docs/INPUTS_AND_LATENCY.md).

The space-weather and Orekit directories are excluded from version control
because their upstream access and redistribution terms are independent of the
model source code. Authoritative sources and product roles are documented in
[`docs/DATA_SOURCES.md`](../docs/DATA_SOURCES.md).
