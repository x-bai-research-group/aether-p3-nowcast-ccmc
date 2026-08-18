# AETHER-P3 Nowcast

AETHER-P3 Nowcast is a global thermospheric neutral-density model designed for
near-real-time estimation of density and predictive uncertainty. It combines
the current location and time, causal solar and geomagnetic histories, solar
wind conditions, and two empirical-density references.

The model uses 342 physical inputs divided into six groups:

| input group | shape | dimensions |
|---|---:|---:|
| location and time | 10 | 10 |
| solar background | 2 | 2 |
| solar-proxy history | 7 × 4 | 28 |
| short forcing history | 35 × 6 | 210 |
| long geomagnetic history | 45 × 2 | 90 |
| empirical density references | 2 | 2 |

Longitude is represented by sine and cosine, making the model continuous
across the international date line. Location and time are encoded separately
before being combined with the solar, geomagnetic, solar-wind, and empirical
states.

One model call jointly returns four normal-inverse-gamma parameters:

(γ, ν, α, β).

Here, γ is the normalized mean log-density prediction. The remaining
parameters define the predictive Student-t distribution used to obtain density
intervals and separate aleatoric and epistemic uncertainty estimates. No
post-hoc calibration scale is applied.

The native global product has:

- five-minute temporal cadence;
- 2-degree latitude spacing;
- 4-degree longitude spacing;
- 230--530 km altitude coverage at 10 km spacing;
- NetCDF4 output containing density, predictive intervals, uncertainty
  components, and the four distribution parameters.
