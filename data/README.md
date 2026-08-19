# Runtime data

Third-party space-weather and Orekit data are not redistributed in this
repository. Obtain them directly from the authoritative providers and place
them under these local directories:

```text
data/space-weather/
data/orekit-data/
```

Required filenames, roles, and sources are documented in
[`docs/RUNTIME_DATA_SETUP.md`](../docs/RUNTIME_DATA_SETUP.md). After preparing
the files, verify the local installation with:

```bash
python scripts/check_runtime_data.py
```

The one-command example uses a small preprocessed fixture and does not require
the third-party runtime archive.
