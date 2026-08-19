# Inputs and operational latency

The model consumes 342 values grouped by physical role.

| group | shape | dimensions | purpose |
|---|---:|---:|---|
| query | 10 | 10 | latitude, periodic longitude, altitude, season, UTC, and local solar time |
| solar background | 2 | 2 | previous-day F10.7 and current-day F30 |
| solar proxy history | 7 × 4 | 28 | causal F10, S10, M10, and Y10 states |
| fast forcing history | 35 × 6 | 210 | Dst, Ap30, Bz, solar-wind speed, proton density, and AE at five-minute spacing over 170 minutes |
| long memory | 45 × 2 | 90 | hourly AE and Dst from 4 to 48 hours |
| empirical anchors | 2 | 2 | current-location log10 JB2008 and NRLMSISE-00 density |

## Causality

- F10.7 uses the previous UTC day.
- The spectral proxies use their declared causal daily delays.
- Dst uses the current available hourly UTC bin.
- Ap30 uses the current completed 30-minute bin.
- AE, Bz, speed, and proton density use the most recent causal observation no
  more than five minutes old.
- Missing required drivers cause the inference request to fail rather than
  silently using future data or unconstrained interpolation.

## Required runtime files

The Java feature generator currently expects:

```text
SOLFSMY.TXT
SW-All.txt
radio_flux_adjusted.txt
DTCFILE.TXT
DST.csv or DST.txt
Apo30.csv
AE.csv or AE.txt
solarwind.csv
```

Orekit Earth-orientation and ephemeris data are also required. Redistribution
rights are not assumed: the repository does not distribute these third-party
runtime files. Authoritative sources and local setup instructions are provided
in [`RUNTIME_DATA_SETUP.md`](RUNTIME_DATA_SETUP.md). The construction of the
locally assembled CSV products and their UTC join into the model input are
specified in [`DRIVER_PREPROCESSING.md`](DRIVER_PREPROCESSING.md).
