# Driver preprocessing and temporal assembly

This document defines how the research driver archive is converted into the
342 model inputs. It is a data-format and causality contract, not a grant of
permission to redistribute provider data. Reformatting, selecting columns, or
combining date ranges does not remove the original provider's terms; the
provider files and the locally assembled tables are therefore excluded from
this repository.

## Source-file classes

The runtime archive contains two distinct classes of files.

| class | files | handling |
|---|---|---|
| provider-format daily tables | `SOLFSMY.TXT`, `DTCFILE.TXT`, `SW-All.txt` | Retained in the provider's numeric row layout; comments and nonnumeric header rows are ignored by the reader. |
| provider-style daily F30 archive | `radio_flux_adjusted.txt` | Daily rows are indexed by UTC date. The model reads year, month, day, and adjusted F30 from the first five columns. |
| locally assembled UTC tables | `DST.csv`, `Apo30.csv`, `AE.csv`, `solarwind.csv` | Provider exports covering the required years are placed in one chronological table per product and converted to the canonical schemas below. Sources are not averaged together. |

Each product remains in its own file. The files are not row-wise merged into a
single master table. `WeatherStore` performs the cross-product join at model
runtime using UTC keys and the causal rules below.

## Canonical locally assembled tables

All timestamps are UTC. Rows should be unique and chronological. A header is
optional for AE; the safest form for the other files is numeric rows only.

### Hourly Dst

Recommended `DST.csv` schema:

```text
year,month,day,hour,minute,second,source_aux,dst_nT
```

The current research file uses hourly rows, zero minute and second, and the
Kyoto Dst value in the final column. The auxiliary source field is retained
from local preparation but is not an inference input. The loader also accepts an ISO-UTC
timestamp followed by a final Dst value. It removes non-finite values and
sentinels with absolute magnitude at least 9000 nT, then indexes the remaining
value at the start of its UTC hour.

### Minute AE

`AE.csv` schema:

```text
year,day_of_year,hour,minute,AE_nT
```

Rows are constructed from the WDC Kyoto AE record without additional temporal
averaging during local format conversion. The loader retains finite values in
the range `0 <= AE < 99999` nT.

### Minute solar wind

`solarwind.csv` contains the high-resolution OMNI export in the selected-column
order used by the research archive:

```text
year,day_of_year,hour,minute,omni_5,omni_6,omni_7,
Bz_GSM_nT,speed_km_s,omni_10,omni_11,omni_12,proton_density_cm3
```

Only columns 8, 9, and 13 are model inputs. The intervening downloaded OMNI
columns are retained to preserve the established column positions but are
ignored by AETHER-P3. A row is rejected unless all three used values are
finite and satisfy `abs(Bz) < 1000 nT`, `0 < speed < 5000 km/s`, and
`0 <= proton density < 1000 cm^-3`.

### Half-hour ap30

The established `Apo30.csv` layout is:

```text
year,month,day,interval_start_hour,interval_aux_hour,
source_time_1,source_time_2,Hp30,ap30,source_flag
```

Only year, month, day, interval start, and ap30 are consumed. Decimal UTC hours
are converted to hour and minute. The ap30 value becomes available to the
model at `interval start + 30 minutes`, which prevents use before completion
of its half-hour interval. The remaining GFZ fields are retained for source
traceability but are not model inputs.

## Runtime temporal assembly

For a requested five-minute UTC, the Java feature generator constructs the
driver portion of the input as follows.

### Daily solar information

- Previous-day observed F10.7 is read from `SW-All.txt`.
- Current-day adjusted F30 is read from `radio_flux_adjusted.txt`.
- Seven solar-history states are read from `SOLFSMY.TXT`: F10 and S10 use
  lags D-1 through D-7, M10 uses D-2 through D-8, and Y10 uses D-5 through
  D-11.
- JB2008 uses F10/F10B and S10/S10B at D-1, M10/M10B at D-2, Y10/Y10B at
  D-5, and the query-hour DTC value.
- The causal NRLMSISE-00 anchor uses previous-day observed F10.7, the trailing
  81-day observed F10.7 average, daily Ap, and the required three-hour Ap
  history from `SW-All.txt`.

### Fast forcing history

Thirty-five states are assembled from 170 minutes before the query through the
query time at five-minute spacing. At each state:

- Dst uses the value indexed to the start of the corresponding UTC hour;
- ap30 uses the most recently completed half-hour interval;
- GSM Bz, solar-wind speed, proton density, and AE use the newest observation
  at or before that state, with a maximum age of five minutes.

### Long geomagnetic memory

Forty-five hourly states cover query time minus 48 hours through query time
minus 4 hours. Each state contains AE and Dst. AE retains the same five-minute
maximum causal age; Dst uses its hourly UTC value.

## Missing values and interpolation

The production assembler does not linearly interpolate, average across
providers, or look forward in time. If a required daily value, hourly value,
completed ap30 interval, or recent minute observation is unavailable, field
generation fails with the missing UTC rather than silently substituting a
future value. This behavior makes the assembled model input deterministic for
a fixed set of local source files.

## Reproduction boundary

The repository specifies the accepted local schemas, source-variable choices,
validity checks, units, and temporal join exactly. Provider download dates and
local archive versions are not frozen in version 1.0.0. Operational source
selection, publication latency, and automated acquisition will be finalized
with CCMC during onboarding.
