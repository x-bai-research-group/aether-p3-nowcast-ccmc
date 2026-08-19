#!/usr/bin/env python3
"""Check that locally supplied third-party runtime data are present."""

from __future__ import annotations

import argparse
from pathlib import Path


SPACE_WEATHER_FILES = (
    ("SOLFSMY.TXT",),
    ("SW-All.txt",),
    ("radio_flux_adjusted.txt",),
    ("DTCFILE.TXT",),
    ("DST.csv", "DST.txt"),
    ("Apo30.csv",),
    ("AE.csv", "AE.txt"),
    ("solarwind.csv",),
)

OREKIT_FILES = (
    "tai-utc.dat",
    "itrf-versions.conf",
    "Earth-Orientation-Parameters/IAU-2000/finals2000A.all",
    "DE-440-ephemerides/lnxp1990.440",
)


def _available(root: Path, alternatives: tuple[str, ...]) -> bool:
    return any(
        (root / filename).is_file() and (root / filename).stat().st_size > 0
        for filename in alternatives
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--data-root",
        type=Path,
        default=Path(__file__).resolve().parents[1] / "data",
        help="directory containing space-weather and orekit-data",
    )
    args = parser.parse_args()
    space_weather_root = args.data_root / "space-weather"
    orekit_root = args.data_root / "orekit-data"

    missing = [
        "space-weather/" + " or ".join(alternatives)
        for alternatives in SPACE_WEATHER_FILES
        if not _available(space_weather_root, alternatives)
    ]
    missing.extend(
        "orekit-data/" + filename
        for filename in OREKIT_FILES
        if not _available(orekit_root, (filename,))
    )
    if missing:
        print("AETHER-P3 runtime data: INCOMPLETE")
        for filename in missing:
            print(f"  missing: {filename}")
        print("See docs/RUNTIME_DATA_SETUP.md for authoritative sources.")
        return 2

    print("AETHER-P3 runtime data: COMPLETE")
    print(f"  space weather: {space_weather_root.resolve()}")
    print(f"  Orekit data:   {orekit_root.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
