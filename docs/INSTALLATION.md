# Installation

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

Place the required space-weather files under `data/space-weather` and the
Orekit auxiliary data under `data/orekit-data`. Both locations are declared in
`config/production.json`. The required products and authoritative sources are
listed in [`DATA_SOURCES.md`](DATA_SOURCES.md). Run `scripts/run_checks.sh`
after installation.

## Runtime verification

Use the TensorFlow version declared by the environment and run the unit tests
and one reference NetCDF generation after installing the package on a new
system.
