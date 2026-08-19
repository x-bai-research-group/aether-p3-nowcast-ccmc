# Orekit runtime data

This directory contains the minimal Orekit auxiliary-data subset required by
the AETHER-P3 Nowcast feature generator. It is derived from the official
[Orekit data repository](https://gitlab.orekit.org/orekit/orekit-data/).

## Included files

- `tai-utc.dat`: UTC--TAI and leap-second history.
- `itrf-versions.conf`: ITRF-version configuration for IERS Earth-orientation
  records.
- `Earth-Orientation-Parameters/IAU-2000/finals2000A.all`: IAU-2000 Earth
  orientation parameters used with the IERS-2010 terrestrial frame.
- `DE-440-ephemerides/lnxp1990.440`: JPL DE-440 ephemerides used to obtain the
  Sun position required by the JB2008 and NRLMSISE-00 calculations.
