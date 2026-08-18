# Installation

## One-command reference installation

On Linux with Conda available, the recommended first run is:

```bash
./scripts/run_example.sh
```

This creates the declared environment when necessary, installs the package,
runs the frozen model with the committed preprocessed input fixture, and
verifies the resulting NetCDF against the reference output. The Java feature
generator and production driver archive are not required for this small test.

## System requirements

- Linux x86-64;
- Python 3.11 or 3.12;
- Java Development Kit 17 or newer;
- Maven 3.8 or newer;
- 64 GB system RAM recommended for training;
- a CUDA-capable GPU is strongly recommended for training.

## Python environment

```bash
conda env create -f environment.yml
conda activate aether-p3-nowcast
python -m pip install .
```

To run the optional source-code tests, install the test dependency separately:

```bash
python -m pip install '.[test]'
```

## Feature generator

```bash
cd feature_generator
mvn -q test package
cd ..
```

The expected executable is:

```text
feature_generator/target/aether-p3-feature-generator-1.0.0.jar
```

## External data

The repository includes Orekit auxiliary data and the space-weather files that
fit ordinary GitHub storage. Add the two larger required files, `AE.csv` and
`solarwind.csv`, under `data/space-weather`. Both runtime locations are
declared in `config/production.json`. Product definitions and authoritative
sources are listed in [`DATA_SOURCES.md`](DATA_SOURCES.md). Run
`scripts/run_checks.sh` after installation.

## Runtime verification

Use the TensorFlow version declared by the environment and run the unit tests
and one reference NetCDF generation after installing the package on a new
system.
