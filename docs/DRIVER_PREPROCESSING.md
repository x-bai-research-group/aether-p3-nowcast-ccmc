# Data preprocessing and temporal assembly

This document describes the transformations used to construct the model target
and its 342 inputs. All times are interpreted in UTC.

## Density target

The target is accelerometer-derived neutral mass density. A valid satellite
observation is associated with the nearest point on the 30-second data grid
when it lies within the five-second matching tolerance. Density is not
interpolated between satellite observations.

The neural network is trained on normalized log-density,

\[
y=\frac{\log_{10}(\rho)-\mu_y}{\sigma_y},
\]

where \(\mu_y\) and \(\sigma_y\) are calculated only from the selected training
records. Feature normalization is likewise calculated from training records
only.

## Driver preparation

| quantity | native representation used by the model | preparation |
|---|---|---|
| Dst | hourly | finite Kyoto value assigned to its UTC hour |
| ap30 | half-hourly | linear ap30 becomes available at the end of its 30-minute interval |
| AE | one minute | OMNI-derived AE archive; valid range \(0\leq AE<99999\) nT |
| GSM Bz | one minute | selected OMNI column after offline interpolation |
| solar-wind speed | one minute | selected OMNI column after offline interpolation |
| proton density | one minute | selected OMNI column after offline interpolation |
| F10.7 and Ap | daily and 3-hourly | values read from `SW-All.txt` |
| F10, S10, M10, Y10 | daily | values read from `SOLFSMY.TXT` at the delays below |
| F30 | daily | adjusted current-day value |

### OMNI solar-wind interpolation

The historical OMNI files were concatenated in chronological one-minute order.
For columns 5–13 of the selected OMNI table, the preparation script classified
values greater than 999 as invalid and replaced them by one-dimensional linear
interpolation in time. Linear extrapolation was used at the outer boundary.
The three interpolated quantities that enter the model are GSM Bz,
solar-wind speed, and proton density.

This interpolation belongs to the construction of the fixed research driver
archive. The Java feature generator does not repeat it. It is also unrelated
to the density target: satellite density observations remain uninterpolated.

### AE provenance

AE was obtained through NASA SPDF OMNI, which distributes the index produced
by WDC Kyoto. Because final, provisional, and quick-look AE values may differ,
one fixed AE archive is used throughout model-data construction.

## Temporal input construction

For a requested time \(t\), the model histories are assembled as follows.

| input | states | times relative to \(t\) |
|---|---:|---|
| short forcing history | 35 | \(t-170\) min to \(t\), every 5 min |
| long AE/Dst history | 45 | \(t-48\) h to \(t-4\) h, every 1 h |
| F10 history | 7 | D-1 through D-7 |
| S10 history | 7 | D-1 through D-7 |
| M10 history | 7 | D-2 through D-8 |
| Y10 history | 7 | D-5 through D-11 |

Each short-history state contains Dst, ap30, GSM Bz, solar-wind speed, proton
density, and AE:

- Dst is assigned from the corresponding hourly UTC bin.
- ap30 is taken from the most recently completed half-hour interval.
- AE and the three solar-wind variables use the most recent table entry at or
  before the state time, with a maximum age of five minutes.

The long history contains AE and Dst. AE follows the same five-minute lookup
tolerance, while Dst retains its hourly value.

The two present solar-background inputs are previous-day observed F10.7 and
current-day adjusted F30.

## Empirical-model inputs

JB2008 uses F10/F10B and S10/S10B at D-1, M10/M10B at D-2,
Y10/Y10B at D-5, and the DTC value for the requested hour.

NRLMSISE-00 uses previous-day observed F10.7, a trailing 81-day F10.7 average,
daily Ap, and the seven-element 3-hour Ap history. The trailing average is used
instead of a centered average so that future solar-flux values are not needed.

JB2008 and NRLMSISE-00 are evaluated at the requested time and location. Their
two log-density estimates form the empirical-reference input group.

## Missing data and causality

The feature generator does not perform additional interpolation during a
prediction request. If a required value cannot be obtained from the supplied
tables under the temporal rules above, that input record is unavailable.

The lookup operation is causal with respect to the prepared tables: it never
selects a table row later than the requested history time. The fixed OMNI
solar-wind table nevertheless contains the offline interpolation described
above. These are separate stages and should not be conflated when interpreting
data latency.

Training and validation periods are separated by a 48-hour guard, equal to the
longest input-memory window. This prevents a validation interval from entering
the history of a training record.

## Local file schemas

The feature generator expects the following scientific columns:

| file | required columns |
|---|---|
| `AE.csv` | year, day of year, hour, minute, AE |
| `solarwind.csv` | year, day of year, hour, minute, selected OMNI columns; Bz, speed, and proton density at columns 8, 9, and 13 |
| `DST.csv` | UTC fields and Dst in the final column |
| `Apo30.csv` | date, half-hour interval, and linear ap30 at column 9 |

Daily solar products retain their provider formats. Installation paths and
source links are listed in [Runtime data setup](RUNTIME_DATA_SETUP.md).
