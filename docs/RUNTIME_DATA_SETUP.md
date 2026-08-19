# Scientific driver data

Full field generation requires the solar, geomagnetic, and auxiliary data
listed below. These third-party products are not distributed with the source
code.

Place the prepared driver files under `data/space-weather/`.

| local file | source | preparation used by the model |
|---|---|---|
| `SOLFSMY.TXT` | [SET JB2008 indices](https://sol.spacenvironment.net/JB2008/indices.html) | retain the provider daily table |
| `DTCFILE.TXT` | [SET JB2008 indices](https://sol.spacenvironment.net/JB2008/indices.html) | retain the provider hourly table |
| `SW-All.txt` | [CelesTrak](https://celestrak.org/SpaceData/SW-All.txt) | retain the provider table; [format](https://celestrak.org/SpaceData/SpaceWx-format.php) |
| `radio_flux_adjusted.txt` | [CLS solar radio flux](https://spaceweather.cls.fr/services/radioflux/) | retain year, month, day, and adjusted F30 |
| `DST.csv` | [WDC Kyoto](https://wdc.kugi.kyoto-u.ac.jp/dstae/index.html) | chronological hourly UTC table |
| `Apo30.csv` | [GFZ ap30](https://kp.gfz.de/en/hp30-hp60) | chronological half-hour table with linear ap30 in column 9 |
| `AE.csv` | [NASA SPDF OMNI](https://omniweb.gsfc.nasa.gov/html/ow_data.html), originally from [WDC Kyoto](https://wdc.kugi.kyoto-u.ac.jp/aedir/) | year, day of year, hour, minute, AE |
| `solarwind.csv` | [NASA SPDF high-resolution OMNI](https://omniweb.gsfc.nasa.gov/html/ow_data.html) | chronological minute table after the documented linear interpolation |

The required solar-wind columns are GSM Bz, speed, and proton density at
columns 8, 9, and 13 of the research table. The interpolation and all temporal
delays are defined in
[Data preprocessing](DRIVER_PREPROCESSING.md).

Use a consistent AE version throughout a model application. OMNI and WDC Kyoto
may provide final, provisional, or quick-look values at different times.

## Orekit data

Obtain the official [Orekit data archive](https://gitlab.orekit.org/orekit/orekit-data/)
and place these files under `data/orekit-data/`:

```text
tai-utc.dat
itrf-versions.conf
Earth-Orientation-Parameters/IAU-2000/finals2000A.all
DE-440-ephemerides/lnxp1990.440
```

They provide leap seconds, Earth orientation, terrestrial reference-frame
information, and the Sun ephemeris required by the JB2008 and NRLMSISE-00
calculations.

## Verify file availability

From the repository root, run:

```bash
python scripts/check_runtime_data.py
```

This command checks filenames and file presence. Scientific coverage and
version consistency remain the responsibility of the prepared local archive.
