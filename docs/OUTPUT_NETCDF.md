# NetCDF output

Each file contains one three-dimensional thermospheric density field. The
dimensions are ordered as

```text
time, altitude, latitude, longitude
```

and the file declares CF-1.10 conventions.

## Probabilistic definition

For normalized log-density $y$, the model returns
$(\gamma,\nu,\alpha,\beta)$, with
$\nu>0$, $\alpha>1$, and $\beta>0$. The implied predictive distribution
is

$$
y \sim \mathrm{Student}\text{-}t\left(
2\alpha,\ \gamma,
\sqrt{\frac{\beta(1+\nu)}{\alpha\nu}}
\right).
$$

The central physical-density estimate is

$$
\hat{\rho}=10^{\mu_y+\sigma_y\gamma},
$$

where $\mu_y$ and $\sigma_y$ are the training target normalization.
The lower and upper density limits are obtained by transforming the 2.5% and
97.5% Student-t quantiles through the same logarithmic relation.

## Variables

| variable | units | scientific meaning |
|---|---|---|
| `density` | kg m$^{-3}$ | central neutral mass-density estimate |
| `density_lower_95` | kg m$^{-3}$ | lower 95% predictive bound |
| `density_upper_95` | kg m$^{-3}$ | upper 95% predictive bound |
| `aleatoric_std_log10` | dimensionless (log-density scale) | estimated data-related standard deviation in $\log_{10}\rho$ |
| `epistemic_std_log10` | dimensionless (log-density scale) | estimated model-related standard deviation in $\log_{10}\rho$ |
| `gamma` | dimensionless (normalized log-density) | predictive location parameter |
| `nu` | dimensionless | normal-inverse-gamma evidence parameter controlling mean uncertainty |
| `alpha` | dimensionless | normal-inverse-gamma shape parameter |
| `beta` | dimensionless | normal-inverse-gamma scale parameter in normalized target space |

The reported uncertainty components are

$$
\sigma_{\mathrm{aleatoric},\log_{10}\rho}
=\sigma_y\sqrt{\frac{\beta}{\alpha-1}},
\qquad
\sigma_{\mathrm{epistemic},\log_{10}\rho}
=\sigma_y\sqrt{\frac{\beta}{\nu(\alpha-1)}}.
$$

The predictive interval represents uncertainty in log-density and is generally
asymmetric after conversion to physical density.

## Coordinates and metadata

Files include UTC time, altitude, geodetic latitude, and longitude coordinates,
as well as model version, input-definition identifier, native cadence, grid
definition, and recommended altitude range.
