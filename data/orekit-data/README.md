# Orekit runtime data

Orekit auxiliary data are not redistributed in this repository. Obtain the
official data from the
[Orekit data repository](https://gitlab.orekit.org/orekit/orekit-data/) and
place the following files at the paths shown below.

## Required files

- `tai-utc.dat`: UTC–TAI and leap-second history.
- `itrf-versions.conf`: ITRF-version configuration for IERS Earth-orientation
  records.
- `Earth-Orientation-Parameters/IAU-2000/finals2000A.all`: IAU-2000 Earth
  orientation parameters used with the IERS-2010 terrestrial frame.
- `DE-440-ephemerides/lnxp1990.440`: JPL DE-440 ephemerides used to obtain the
  Sun position required by the JB2008 and NRLMSISE-00 calculations.

Run `python scripts/check_runtime_data.py` from the repository root after the
files have been installed.
