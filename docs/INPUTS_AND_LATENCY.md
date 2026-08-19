# Model inputs and temporal context

AETHER-P3 Nowcast uses 342 inputs. They describe the requested point, the
background solar state, recent forcing, longer geomagnetic memory, and two
empirical density references.

## Input groups

| group | shape | dimensions | variables |
|---|---:|---:|---|
| location and time | 10 | 10 | latitude, \(\sin\lambda\), \(\cos\lambda\), altitude, seasonal sine/cosine, UTC sine/cosine, local-solar-time sine/cosine |
| solar background | 2 | 2 | previous-day F10.7, current-day adjusted F30 |
| solar-proxy history | 7 × 4 | 28 | F10, S10, M10, and Y10 at seven delayed daily states |
| short forcing history | 35 × 6 | 210 | Dst, ap30, GSM Bz, speed, proton density, and AE from \(t-170\) min to \(t\) |
| long geomagnetic history | 45 × 2 | 90 | AE and Dst from \(t-48\) h to \(t-4\) h |
| empirical references | 2 | 2 | \(\log_{10}\rho_{\mathrm{JB2008}}\) and \(\log_{10}\rho_{\mathrm{NRLMSISE00}}\) at the requested point |

The dimensions sum to \(10+2+28+210+90+2=342\).

## Physical interpretation

- Location, altitude, season, UTC, and local solar time describe the spatial
  and periodic structure of the thermosphere.
- F10.7 and F30 represent the slowly varying solar background.
- F10, S10, M10, and Y10 provide spectral solar information over several
  preceding days.
- Bz, solar-wind speed, proton density, AE, Dst, and ap30 describe the
  upstream forcing and geomagnetic response over minutes to hours.
- The 48-hour AE/Dst history represents delayed thermospheric response and
  recovery.
- JB2008 and NRLMSISE-00 provide physically structured reference densities
  that the neural network can correct using the other inputs.

## Time availability

All model lookups refer to times at or before the requested UTC:

- F10.7 uses the previous UTC day.
- F30 uses the current daily product.
- F10 and S10 use D-1 through D-7.
- M10 uses D-2 through D-8.
- Y10 uses D-5 through D-11.
- Dst uses its hourly UTC value.
- ap30 becomes available after completion of its half-hour interval.
- AE and the three solar-wind variables use the most recent table entry no
  more than five minutes old.

The local OMNI solar-wind table was linearly interpolated during offline
preparation. No additional interpolation is performed when histories are
assembled for inference. Density observations are not interpolated.

The required scientific files and their sources are listed in
[Runtime data setup](RUNTIME_DATA_SETUP.md). Exact preprocessing is described
in [Data preprocessing](DRIVER_PREPROCESSING.md).
