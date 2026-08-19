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

A GPU is not required for inference. At least 16 GB system RAM is recommended
for complete global-field generation. On the tested Intel Core Ultra 9 285K
CPU, a 251,100-point field required approximately 103 seconds end to end.

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

Third-party driver and Orekit data are not redistributed in this repository.
Follow [`RUNTIME_DATA_SETUP.md`](RUNTIME_DATA_SETUP.md), place the locally
obtained files at the paths declared in `config/production.json`, and run:

```bash
python scripts/check_runtime_data.py
```

The one-command preprocessed example remains available without these external
files.

## Runtime verification

Use the TensorFlow version declared by the environment and run the unit tests
and one reference NetCDF generation after installing the package on a new
system.
