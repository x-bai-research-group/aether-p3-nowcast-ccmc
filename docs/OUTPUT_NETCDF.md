# NetCDF output

The native file dimensions are ordered as:

```text
time, altitude, latitude, longitude
```

| variable | units | description |
|---|---|---|
| density | kg m-3 | central neutral-density estimate |
| density_lower_95 | kg m-3 | lower Student-t 95% predictive bound |
| density_upper_95 | kg m-3 | upper Student-t 95% predictive bound |
| aleatoric_std_log10 | 1 | aleatoric standard deviation in log10 density |
| epistemic_std_log10 | 1 | epistemic standard deviation in log10 density |
| gamma | 1 | normalized log10-density mean |
| nu | 1 | NIG nu parameter |
| alpha | 1 | NIG alpha parameter |
| beta | 1 | NIG beta parameter |

Files declare CF-1.10 conventions and include model version, feature contract,
native cadence, grid definition, and recommended altitude range.
