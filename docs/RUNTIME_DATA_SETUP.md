# Runtime data setup

The AETHER-P3 source code, frozen model, and small preprocessed example are
distributed in this repository. Third-party driver and Orekit data are not
redistributed. Users must obtain those products directly from their providers
and comply with the applicable provider terms.

## Driver data sources used in the current research implementation

Real-time data sources, publication latency, and update policies are
deployment-specific and are not fixed by this research release.

Place the following files under `data/space-weather/`:

| local filename | source and preparation |
|---|---|
| `SOLFSMY.TXT` | Download the JB2008 solar indices from [Space Environment Technologies](https://sol.spacenvironment.net/JB2008/indices.html). Preserve the provider's whitespace-delimited format. |
| `DTCFILE.TXT` | Download the JB2008 DTC file from [Space Environment Technologies](https://sol.spacenvironment.net/JB2008/indices.html). Preserve the provider's whitespace-delimited format. |
| `SW-All.txt` | Download the consolidated file from [CelesTrak](https://celestrak.org/SpaceData/SW-All.txt); its format is documented [here](https://celestrak.org/SpaceData/SpaceWx-format.php). |
| `radio_flux_adjusted.txt` | Obtain adjusted F30 data from the [CLS Solar Radio Flux service](https://spaceweather.cls.fr/services/radioflux/). The feature generator reads year, month, day, and adjusted F30 from the provider-style daily table. |
| `DST.csv` or `DST.txt` | Obtain hourly Dst from [WDC Kyoto](https://wdc.kugi.kyoto-u.ac.jp/dstae/index.html) and export UTC plus Dst in one of the formats accepted by `WeatherStore`. |
| `Apo30.csv` | Obtain linear ap30 from [GFZ](https://kp.gfz.de/en/hp30-hp60). The research file stores year, month, day, interval start/end, and ap30 in column 9. |
| `AE.csv` or `AE.txt` | Obtain the AE field through the [NASA SPDF high-resolution OMNI product](https://omniweb.gsfc.nasa.gov/html/ow_data.html). OMNI distributes AE values originating from [WDC Kyoto](https://wdc.kugi.kyoto-u.ac.jp/aedir/). The research CSV columns are year, day of year, hour, minute, and AE. |
| `solarwind.csv` | Obtain high-resolution OMNI data from [NASA SPDF OMNIWeb](https://omniweb.gsfc.nasa.gov/html/ow_data.html). The research CSV contains year, day of year, hour, minute, and the selected OMNI columns after the historical linear interpolation described in `DRIVER_PREPROCESSING.md`; the generator reads GSM Bz, speed, and proton density from columns 8, 9, and 13. |

The first four products are consumed in provider-style formats. The remaining
research CSV files are local preprocessing products and are not presented as
provider-issued operational files.

Use one frozen AE snapshot consistently for data generation and inference.
Final, provisional, and quick-look AE versions can differ, and OMNI and WDC
Kyoto may expose those versions on different schedules. Re-downloading AE at a
later date therefore does not guarantee values identical to the research
snapshot.

The exact canonical columns, retained source fields, validity filters, and UTC
assembly rules for these local products are defined in
[`DRIVER_PREPROCESSING.md`](DRIVER_PREPROCESSING.md). Format conversion does
not imply permission to redistribute the resulting table.

## Orekit auxiliary data

Obtain the official [Orekit data archive](https://gitlab.orekit.org/orekit/orekit-data/)
and place these files under `data/orekit-data/`:

```text
tai-utc.dat
itrf-versions.conf
Earth-Orientation-Parameters/IAU-2000/finals2000A.all
DE-440-ephemerides/lnxp1990.440
```

## Verify the local installation

```bash
python scripts/check_runtime_data.py
```

The check confirms that every required local file exists and is non-empty. It
does not verify provider licensing, publication latency, temporal coverage, or
scientific content.
