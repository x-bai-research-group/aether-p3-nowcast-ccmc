# Data sources

This document identifies the authoritative sources for the observations,
drivers, empirical references, and auxiliary data used by AETHER-P3 Nowcast.

## Neutral-density observations

| mission | role | authoritative access |
|---|---|---|
| Swarm-C | training and validation density labels | [ESA Swarm Level-2 daily DNS/ACC](https://swarm-diss.eo.esa.int/#swarm%2FLevel2daily%2FEntire_mission_data%2FDNS%2FACC) |
| CHAMP | training and validation density labels | [ESA Swarm multi-mission CHAMP DNS](https://swarm-diss.eo.esa.int/#swarm%2FMultimission%2FCHAMP%2FDNS) |
| GRACE-A | training and validation density labels | [ESA Swarm multi-mission GRACE Sat-1 DNS](https://swarm-diss.eo.esa.int/#swarm%2FMultimission%2FGRACE%2FDNS%2FSat_1) |
| GRACE-FO Sat-1 | training and validation density labels | [ESA Swarm multi-mission GRACE-FO Sat-1 DNS](https://swarm-diss.eo.esa.int/#swarm%2FMultimission%2FGRACE-FO%2FDNS%2FSat_1) |
| GOCE | training and validation density labels | [ESA GOCE Thermosphere Data, TDC_GOC_2](https://goce-ds.eo.esa.int/oads/access/collection/GOCE_Thermosphere_Data) |

The ESA Swarm links use browser-side fragment routes and should be opened in a
web browser.

## Operational space-weather drivers

| local product | model variables | authoritative source |
|---|---|---|
| `solarwind.csv` | GSM Bz, solar-wind speed, and proton number density | [NASA SPDF OMNIWeb data documentation](https://omniweb.gsfc.nasa.gov/html/ow_data.html); use the high-resolution OMNI product |
| `DST.csv` or `DST.txt` | hourly Dst | [WDC for Geomagnetism, Kyoto: hourly Dst data](https://wdc.kugi.kyoto-u.ac.jp/dstae/index.html) |
| `AE.csv` or `AE.txt` | AE in the fast history and hourly AE in the long history | [WDC for Geomagnetism, Kyoto: hourly Dst and AE data](https://wdc.kugi.kyoto-u.ac.jp/dstae/index.html) |
| `Apo30.csv` | completed half-hour ap30 interval | [GFZ Hp30/Hp60 and linear ap30/ap60 data](https://kp.gfz.de/en/hp30-hp60) |
| `SW-All.txt` | previous-day observed F10.7, trailing 81-day F10.7, daily Ap, and 3-hour Ap required by NRLMSISE-00 | [CelesTrak SW-All data](https://celestrak.org/SpaceData/SW-All.txt) and [format documentation](https://celestrak.org/SpaceData/SpaceWx-format.php) |
| `SOLFSMY.TXT` | causal F10, S10, M10, and Y10 solar-proxy history; JB2008 inputs | [SET JB2008 current indices](https://sol.spacenvironment.net/JB2008/indices.html) |
| `DTCFILE.TXT` | JB2008 geomagnetic storm correction | [SET JB2008 current indices](https://sol.spacenvironment.net/JB2008/indices.html) |
| `radio_flux_adjusted.txt` | current-day F30 | [CLS Solar Radio Flux service](https://spaceweather.cls.fr/services/radioflux/) |

## Empirical references and auxiliary data

| component | role | authoritative source |
|---|---|---|
| JB2008 | current-location empirical density input | [SET JB2008 indices and model resources](https://sol.spacenvironment.net/JB2008/indices.html) |
| NRLMSISE-00 | current-location empirical density input | [NASA CCMC NRLMSISE-00 description](https://ccmc.gsfc.nasa.gov/models/NRLMSIS~00/) |
| Orekit data | Earth orientation, time scales, and reference-frame support | [Official Orekit 13.1.4 downloads and data instructions](https://www.orekit.org/site-orekit-13.1.4/downloads.html) |

JB2008 and NRLMSISE-00 densities are evaluated locally through Orekit; they are
not downloaded density grids.

### Orekit integration

The Java feature generator uses Orekit 13.1.4 and supplies model inputs through
custom implementations of `JB2008InputParameters` and
`NRLMSISE00InputParameters`.

- JB2008 receives F10/F10B and S10/S10B from `SOLFSMY.TXT` at D-1,
  M10/M10B at D-2, Y10/Y10B at D-5, and the hourly DTC value from
  `DTCFILE.TXT`.
- NRLMSISE-00 receives previous-day observed F10.7, the causal trailing 81-day
  observed F10.7 average, and its seven-element Ap history from `SW-All.txt`.
  Switch 9 is set to -1 so that the complete 3-hour Ap history is used rather
  than daily Ap alone.
- UTC, WGS-84 geodetic position, the ITRF/IERS-2010 frame, and the Orekit Sun
  position provider supply the time and geometry required by both models.
- The returned densities are in kg m-3 and enter the neural-network feature
  vector as `log10_JB2008_density` and `log10_NRLMSISE00_density`.

Ap30, AE, the separate hourly Dst file, OMNI solar-wind variables, and F30 do
not enter either Orekit empirical-model calculation. They are separate neural-
network drivers. JB2008 uses DTC from `DTCFILE.TXT`; NRLMSISE-00 uses the Ap
values in `SW-All.txt`.

The trailing F10.7 average is a deliberate causal nowcast choice. The
conventional retrospective NRLMSISE-00 specification uses a centered 81-day
average, so the resulting anchor should be described as a causal
NRLMSISE-00 implementation when exact retrospective reproducibility matters.

For scientific attribution, cite the original JB2008 and NRLMSISE-00 model
publications as well as the exact Orekit software release:

- Bowman, B. R., et al. (2008), *A New Empirical Thermospheric Density Model
  JB2008 Using New Solar and Geomagnetic Indices*, AIAA 2008-6438,
  https://doi.org/10.2514/6.2008-6438.
- Picone, J. M., Hedin, A. E., Drob, D. P., and Aikin, A. C. (2002),
  *NRLMSISE-00 empirical model of the atmosphere: Statistical comparisons and
  scientific issues*, https://doi.org/10.1029/2002JA009430.
- Orekit 13.1.4, https://doi.org/10.5281/zenodo.7249096, with the deployed
  version recorded explicitly.
