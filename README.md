# AETHER-P3 Nowcast

AETHER-P3 Nowcast estimates global thermospheric neutral mass density and its
predictive uncertainty from the recent solar, geomagnetic, and solar-wind
state. The model is intended for low-Earth-orbit applications within
230–530 km altitude, with 250–520 km treated as its principal application
range.

The prediction target is

\[
y=\frac{\log_{10}(\rho)-\mu_y}{\sigma_y},
\]

where \(\rho\) is neutral mass density in kg m\(^{-3}\), and \(\mu_y\) and
\(\sigma_y\) are calculated from the training data. A single neural-network
evaluation returns the four normal-inverse-gamma parameters
\((\gamma,\nu,\alpha,\beta)\). They define a central density estimate and a
predictive Student-t distribution without post-hoc uncertainty scaling.

## Scientific inputs

The model uses 342 values organized by physical role.

| input group | shape | dimensions | physical information |
|---|---:|---:|---|
| location and time | 10 | 10 | latitude, periodic longitude, altitude, season, UTC, and local solar time |
| solar background | 2 | 2 | previous-day F10.7 and current-day F30 |
| solar-proxy history | 7 × 4 | 28 | delayed F10, S10, M10, and Y10 histories |
| short forcing history | 35 × 6 | 210 | Dst, ap30, GSM Bz, solar-wind speed, proton density, and AE over the preceding 170 minutes |
| long geomagnetic history | 45 × 2 | 90 | hourly AE and Dst from 48 to 4 hours before prediction |
| empirical references | 2 | 2 | current-location JB2008 and NRLMSISE-00 log-density estimates |

The histories contain only states at or before the requested time. Separate
encoders represent rapid upstream forcing, longer geomagnetic memory, solar
history, empirical-model context, and the requested location and time. These
representations are then combined to predict density and uncertainty jointly.

Longitude is represented by sine and cosine rather than a discontinuous scalar.
Consequently, the same geographic meridian has the same representation at
\(-180^\circ\) and \(+180^\circ\), preventing an artificial density seam in a
global field.

Detailed input definitions and temporal delays are given in
[Inputs and latency](docs/INPUTS_AND_LATENCY.md). Data sources and
preprocessing are described in [Data sources](docs/DATA_SOURCES.md) and
[Driver preprocessing](docs/DRIVER_PREPROCESSING.md).

## Output field

The standard product is a NetCDF4 field with dimensions
`time × altitude × latitude × longitude`. Its default grid is:

- one field every five minutes;
- 2° latitude spacing, centered from \(-89^\circ\) to \(+89^\circ\);
- 4° longitude spacing, centered from \(-178^\circ\) to \(+178^\circ\);
- 10 km altitude spacing from 230 to 530 km.

Each grid point contains density, the 95% predictive interval, aleatoric and
epistemic standard deviations in log-density, and
\((\gamma,\nu,\alpha,\beta)\). See [NetCDF output](docs/OUTPUT_NETCDF.md) for
the variable definitions.

## Data and evaluation

Accelerometer-derived densities from CHAMP, GRACE-A, GOCE, Swarm-C, and
GRACE-FO provide the observational target. Density observations are not
linearly interpolated. Missing or flagged OMNI solar-wind drivers in the
fixed research driver table were linearly interpolated before construction of
the model histories; this is separate from density-label processing.

Training and validation intervals are temporally disjoint and protected by a
48-hour history guard. Checkpoints are selected using validation data only.
The 12 reported cases are evaluation benchmarks rather than an untouched test
set because their results were considered when the final trained seed was
chosen. The complete definitions are in
[Validation protocol](docs/VALIDATION.md).

## Run the included example

On Linux with Conda installed:

```bash
./scripts/run_example.sh
```

This command creates the declared Python environment when necessary, evaluates
the released model on eight preprocessed examples, writes a small NetCDF file,
and compares it with the included reference. A successful run ends with:

```text
AETHER-P3 example: PASS
```

The example contains derived model inputs, not third-party source records.

## Generate a global field

Full field generation requires the driver files and Orekit data listed in
[Runtime data setup](docs/RUNTIME_DATA_SETUP.md):

```bash
conda env create -f environment.yml
conda activate aether-p3-nowcast
python -m pip install .

cd feature_generator
mvn -q test package
cd ..

aether-p3-nowcast grid \
  --config config/production.json \
  --utc 2024-05-11T12:00:00Z \
  --output-dir output
```

The requested UTC must lie on a five-minute boundary. Further installation and
training commands are provided in [Installation](docs/INSTALLATION.md) and the
[User guide](docs/USER_GUIDE.md).

## Computational requirements

A GPU is not required for inference. Complete global-field generation is
recommended on a system with at least 16 GB RAM. On the reference Ubuntu 24.04
system, one 251,100-point field required approximately 102 s on an Intel Core
Ultra 9 285K CPU and 27 s when TensorFlow inference used an NVIDIA RTX 5090.
Runtime depends on hardware, Java feature construction, empirical-model
evaluation, and driver-file access.

## Model release

| item | value |
|---|---|
| version | 1.0.0 |
| input definition | `aether-p3-nowcast-342-v1` |
| trained seed | 20 |
| selected epoch | 117 |
| model weights | `model/model.weights.h5` |
| weight SHA-256 | `eecc45f27e5fc40d80f74f1b2cc2c803f5c6d7dc6174ee17ae4225ffddec8a04` |
| supported Python | 3.11 or 3.12 |
| tested operating system | Ubuntu 24.04 x86-64 |

## Scientific references

- Wang, Y., and Bai, X. (2024), [*A Global Thermospheric Density Prediction
  Framework Based on a Deep Evidential
  Method*](https://doi.org/10.1029/2024SW004070), *Space Weather*, 22(12).
- Wang, R., and Bai, X. (2026), [*A Machine-Learning-Based Global
  Thermospheric Density Forecasting
  Model*](https://doi.org/10.1029/2026SW004968), *Space Weather*, 24(6).
- Amini, A., Schwarting, W., Soleimany, A., and Rus, D. (2020),
  [*Deep Evidential
  Regression*](https://proceedings.neurips.cc/paper/2020/hash/aab085461de182608ee9f607f3f7d18f-Abstract.html).
- Bowman, B. R., et al. (2008), [*A New Empirical Thermospheric Density Model
  JB2008 Using New Solar and Geomagnetic
  Indices*](https://doi.org/10.2514/6.2008-6438).
- Picone, J. M., et al. (2002), [*NRLMSISE-00 empirical model of the
  atmosphere*](https://doi.org/10.1029/2002JA009430).

Version 1.0.0 is a later nowcast implementation of the AETHER-P3 framework and
is not identical to the model configurations in the two AETHER-P3
publications.

## Contacts

- Scientific contact: Xiaoli Bai
  ([xiaoli.bai@rutgers.edu](mailto:xiaoli.bai@rutgers.edu))
- Technical contact: Ruochen Wang
  ([ruo.chen.wang@rutgers.edu](mailto:ruo.chen.wang@rutgers.edu))

The software is released under the MIT License. Third-party scientific data
remain subject to the terms of their original providers.
