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

**(γ, ν, α, β)**

Here, γ is the normalized mean log-density prediction. The remaining
parameters define the predictive Student-t distribution used to obtain density
intervals and separate aleatoric and epistemic uncertainty estimates. No
post-hoc calibration scale is applied.

The native global product has:

- five-minute temporal cadence;
- 2-degree latitude spacing;
- 4-degree longitude spacing;
- 230–530 km altitude coverage at 10 km spacing;
- NetCDF4 output containing density, predictive intervals, uncertainty
  components, and the four distribution parameters.

## One-command example

On Linux with Conda installed, a clean checkout can install the declared
environment, run the frozen model, and verify a reference NetCDF using one
command:

```bash
./scripts/run_example.sh
```

The first run creates the `aether-p3-nowcast` Conda environment and may take
several minutes while dependencies are installed. A successful end-to-end run
finishes with:

```text
AETHER-P3 example: PASS
Output: .../aether_p3_nowcast_20240528T120000Z.nc
```

The example evaluates eight grid points using the release model weights,
training normalization, and a committed array of 342-dimensional preprocessed
model inputs. No third-party source records are redistributed with this test.
The production `grid` command separately constructs the same input contract
from the complete operational driver archive.

## Scientific attribution

The uncertainty formulation, empirical density inputs, and orbital-environment
calculations build on the following work:

- Amini, A., Schwarting, W., Soleimany, A., and Rus, D. (2020),
  [*Deep Evidential Regression*](https://proceedings.neurips.cc/paper/2020/hash/aab085461de182608ee9f607f3f7d18f-Abstract.html),
  Advances in Neural Information Processing Systems 33.
- Bowman, B. R., et al. (2008),
  [*A New Empirical Thermospheric Density Model JB2008 Using New Solar and
  Geomagnetic Indices*](https://doi.org/10.2514/6.2008-6438), AIAA 2008-6438.
- Picone, J. M., Hedin, A. E., Drob, D. P., and Aikin, A. C. (2002),
  [*NRLMSISE-00 empirical model of the atmosphere: Statistical comparisons and
  scientific issues*](https://doi.org/10.1029/2002JA009430), Journal of
  Geophysical Research: Space Physics, 107(A12).
- Orekit Team,
  [Orekit 13.1.4](https://www.orekit.org/site-orekit-13.1.4/downloads.html),
  used for time scales, reference frames, Sun position, and the local JB2008
  and NRLMSISE-00 evaluations.

Authoritative sources for the satellite density observations and operational
space-weather drivers are listed in
[`docs/DATA_SOURCES.md`](docs/DATA_SOURCES.md).

## Manual installation

AETHER-P3 Nowcast requires Python 3.11 or 3.12, Java 17 or newer, and Maven
3.8 or newer. Create the supplied environment, install the Python package, and
build the Java feature generator:

```bash
conda env create -f environment.yml
conda activate aether-p3-nowcast
python -m pip install -e '.[test]'

cd feature_generator
mvn -q test package
cd ..
```

Manual installation and production use require the complete runtime driver
archive. The repository includes the model weights, normalization, Orekit
auxiliary data, and space-weather files that are below GitHub's individual-file
limit. Two high-resolution files are too large for ordinary GitHub storage and
must be placed under `data/space-weather`:

```text
AE.csv
solarwind.csv
```

Their authoritative sources and expected roles are documented in
[`docs/DATA_SOURCES.md`](docs/DATA_SOURCES.md). The exact filenames and causal
latencies are listed in
[`docs/INPUTS_AND_LATENCY.md`](docs/INPUTS_AND_LATENCY.md).

## Additional checks

Run the Python and Java checks:

```bash
scripts/run_checks.sh
```

Display the complete 342-input contract:

```bash
aether-p3-nowcast contract
```

## Generate a global nowcast

The following command generates one three-dimensional NetCDF field at the
requested UTC:

```bash
aether-p3-nowcast grid \
  --config config/production.json \
  --utc 2024-05-11T12:00:00Z \
  --output-dir output
```

The requested UTC must lie on a five-minute boundary. The production grid uses
2-degree latitude spacing, 4-degree longitude spacing, and altitudes from 230
to 530 km at 10 km spacing. Existing NetCDF files are never overwritten.

A preprocessed input fixture, a small production-path configuration, and a
reference output are provided under `examples/`. Additional installation,
input, output, and validation details are available in `docs/`.

## Train from a prepared dataset

Training data are not distributed with this repository. A compatible prepared
dataset can be checked and used as follows:

```bash
aether-p3-nowcast check --dataset-root /path/to/training_dataset
scripts/run_training.sh /path/to/training_dataset runs/training
```

The default `config/seeds.json` sets the training random seed to 20.
