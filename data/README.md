# Runtime data

The repository includes the following runtime drivers under
`data/space-weather`:

```text
Apo30.csv
DST.csv
DTCFILE.TXT
SOLFSMY.TXT
SW-All.txt
radio_flux_adjusted.txt
```

Two required files exceed GitHub's individual-file limit and must be supplied
locally in the same directory:

```text
AE.csv
solarwind.csv
```

The one-command reference test uses an already assembled model-input fixture
and therefore does not redistribute excerpts of these source products.

Orekit runtime data are included under `data/orekit-data/`. Required products,
causality rules, filenames, and authoritative sources are documented in
[`docs/INPUTS_AND_LATENCY.md`](../docs/INPUTS_AND_LATENCY.md) and
[`docs/DATA_SOURCES.md`](../docs/DATA_SOURCES.md).

Before any public redistribution, confirm the applicable upstream terms for
all third-party data products.
