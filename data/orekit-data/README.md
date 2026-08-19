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

The complete Orekit convenience archive also contains gravity, ocean-tide,
Marshall solar-activity, CSSI space-weather, and JB2008 space-environment
files. AETHER-P3 does not use those copies: its operational drivers and
JB2008/NRLMSISE-00 input parameters are read from `data/space-weather` by the
project's Java feature generator.

This subset has been checked against the complete Orekit directory using
AETHER-P3 grid-feature generation. The serialized shared features and
empirical-density anchors were identical for the audit case.
