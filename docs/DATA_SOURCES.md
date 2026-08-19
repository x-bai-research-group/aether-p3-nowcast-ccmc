# Scientific data sources

AETHER-P³ Nowcast combines accelerometer-derived density observations,
space-weather drivers, and two empirical thermosphere models. This document
identifies the source and scientific role of each product.

## Neutral-density observations

| mission | approximate coverage used in the research archive | source |
|---|---|---|
| CHAMP | 2000–2010 | [ESA multi-mission CHAMP DNS](https://swarm-diss.eo.esa.int/#swarm%2FMultimission%2FCHAMP%2FDNS) |
| GRACE-A | 2002–2017 | [ESA multi-mission GRACE Sat-1 DNS](https://swarm-diss.eo.esa.int/#swarm%2FMultimission%2FGRACE%2FDNS%2FSat_1) |
| GOCE | 2009–2013 | [ESA GOCE Thermosphere Data, TDC_GOC_2](https://goce-ds.eo.esa.int/oads/access/collection/GOCE_Thermosphere_Data) |
| Swarm-C | 2014–2023 | [ESA Swarm Level-2 daily DNS/ACC](https://swarm-diss.eo.esa.int/#swarm%2FLevel2daily%2FEntire_mission_data%2FDNS%2FACC) |
| GRACE-FO Sat-1 | 2018–2023 | [ESA multi-mission GRACE-FO Sat-1 DNS](https://swarm-diss.eo.esa.int/#swarm%2FMultimission%2FGRACE-FO%2FDNS%2FSat_1) |

These densities are the supervised target. Valid observations are matched to
the model time grid; density is not created by linear interpolation between
satellite measurements.

## Solar and geomagnetic drivers

| model variable | local file | source |
|---|---|---|
| GSM Bz, solar-wind speed, proton density | `solarwind.csv` | [NASA SPDF high-resolution OMNI](https://omniweb.gsfc.nasa.gov/html/ow_data.html) |
| AE | `AE.csv` | acquired through [NASA SPDF OMNI](https://omniweb.gsfc.nasa.gov/html/ow_data.html); the index originates from [WDC Kyoto](https://wdc.kugi.kyoto-u.ac.jp/aedir/) |
| Dst | `DST.csv` | [WDC Kyoto](https://wdc.kugi.kyoto-u.ac.jp/dstae/index.html) |
| ap30 | `Apo30.csv` | [GFZ Hp30/Hp60 and ap30/ap60](https://kp.gfz.de/en/hp30-hp60) |
| observed F10.7 and Ap history | `SW-All.txt` | [CelesTrak space-weather data](https://celestrak.org/SpaceData/SW-All.txt) and [format description](https://celestrak.org/SpaceData/SpaceWx-format.php) |
| F10, S10, M10, Y10 and their smoothed values | `SOLFSMY.TXT` | [Space Environment Technologies JB2008 indices](https://sol.spacenvironment.net/JB2008/indices.html) |
| DTC storm correction | `DTCFILE.TXT` | [Space Environment Technologies JB2008 indices](https://sol.spacenvironment.net/JB2008/indices.html) |
| adjusted F30 | `radio_flux_adjusted.txt` | [CLS solar radio flux service](https://spaceweather.cls.fr/services/radioflux/) |

AE distributed through OMNI is derived by WDC Kyoto rather than independently
recomputed by OMNI. AE values may be released as final, provisional, or
quick-look products. The model data therefore use one fixed AE archive so that
training and inference refer to the same version.

The local OMNI solar-wind table is a preprocessed research product. Missing or
flagged magnetic-field and plasma values were linearly interpolated during its
construction. This driver interpolation is distinct from the density target,
which is not interpolated.

## Empirical density references

JB2008 and NRLMSISE-00 are evaluated at the requested UTC, latitude,
longitude, and altitude. Their log-density estimates are supplied to the
neural network as physical reference states; neither model is treated as the
observational target.

| model | inputs used in the local calculation | reference |
|---|---|---|
| JB2008 | F10/F10B and S10/S10B at D-1; M10/M10B at D-2; Y10/Y10B at D-5; hourly DTC | [Bowman et al. (2008)](https://doi.org/10.2514/6.2008-6438) |
| NRLMSISE-00 | previous-day F10.7, trailing 81-day F10.7 average, daily Ap, and seven-element 3-hour Ap history | [Picone et al. (2002)](https://doi.org/10.1029/2002JA009430) |

The NRLMSISE-00 reference uses a trailing rather than centered 81-day F10.7
average so that the calculation does not require future solar-flux values.
This is a causal nowcast adaptation of the usual retrospective input.

Both empirical models are evaluated locally using
[Orekit 13.1.4](https://www.orekit.org/site-orekit-13.1.4/downloads.html).
Orekit supplies time scales, Earth orientation, reference frames, geodetic
coordinates, and the Sun position. Returned densities are converted to
kg m$^{-3}$ before their logarithms enter the neural network.

## Data availability

Third-party source files are not distributed with this repository. The
required filenames and preparation instructions are listed in
[Runtime data setup](RUNTIME_DATA_SETUP.md), and the temporal transformations
are specified in [Driver preprocessing](DRIVER_PREPROCESSING.md).
