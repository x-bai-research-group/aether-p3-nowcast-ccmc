# Installation

## Reference example

On Linux with Conda installed, the shortest complete test is:

```bash
./scripts/run_example.sh
```

The script creates the declared environment when necessary, installs the
package, evaluates the released model on included preprocessed inputs, writes a
small NetCDF file, and compares it with the included reference.

This example does not require the Java feature generator or third-party driver
files.

## Requirements

- Linux x86-64;
- Python 3.11 or 3.12;
- Java Development Kit 17 or newer;
- Maven 3.8 or newer;
- at least 16 GB RAM recommended for global-field inference;
- 64 GB RAM and a CUDA-capable GPU recommended for training.

A GPU is optional for inference. On the reference system, a complete
251,100-point field required approximately 102 s on CPU and 27 s with an
NVIDIA RTX 5090. These times include feature generation, empirical-model
evaluation, neural-network inference, and NetCDF writing.

## Manual installation

```bash
conda env create -f environment.yml
conda activate aether-p3-nowcast
python -m pip install .
```

Build the Java feature generator:

```bash
cd feature_generator
mvn -q test package
cd ..
```

The resulting executable is:

```text
feature_generator/target/aether-p3-feature-generator-1.0.0.jar
```

## Scientific driver files

Obtain the external driver and Orekit files described in
[Scientific driver data](RUNTIME_DATA_SETUP.md), then check their presence:

```bash
python scripts/check_runtime_data.py
```

## Verification

Run the Python and Java checks:

```bash
scripts/run_checks.sh
```

Generate one global field:

```bash
aether-p3-nowcast grid \
  --config config/production.json \
  --utc 2024-05-11T12:00:00Z \
  --output-dir output
```

The UTC must lie on a five-minute boundary.
