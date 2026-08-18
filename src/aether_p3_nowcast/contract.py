"""Immutable 342-input contract for AETHER-P3 Nowcast."""

from __future__ import annotations

from dataclasses import dataclass


CONTRACT_ID = "aether-p3-nowcast-342-v1"
SOURCE_DATASET_CONTRACT_ID = "aether-nowcast-342-periodic-lon-v1"
TARGET_NAME = "log10_density_kg_m3"
TARGET_TRANSFORM = "training-only z-score of log10(density_kg_m3)"

QUERY_NAMES = (
    "query_lat_rad",
    "query_sin_lon",
    "query_cos_lon",
    "query_alt_km",
    "query_sin_doy",
    "query_cos_doy",
    "query_sin_ut",
    "query_cos_ut",
    "query_sin_lst",
    "query_cos_lst",
)
SOLAR_BACKGROUND_NAMES = ("F107_previous_day", "F30_current_day")
SOLAR_HISTORY_NAMES = tuple(
    name
    for state in range(7)
    for name in (
        f"F10_lag_{state + 1}d",
        f"S10_lag_{state + 1}d",
        f"M10_lag_{state + 2}d",
        f"Y10_lag_{state + 5}d",
    )
)
SHORT_CHANNELS = (
    "Dst",
    "Ap30",
    "Bz_GSM_nT",
    "V_km_s",
    "proton_number_density_n_cc",
    "AE",
)
SHORT_LAGS_MINUTES = tuple(range(170, -1, -5))
SHORT_HISTORY_NAMES = tuple(
    f"{channel}_{'current' if lag == 0 else f'lag_{lag}m'}"
    for lag in SHORT_LAGS_MINUTES
    for channel in SHORT_CHANNELS
)
LONG_CHANNELS = ("AE", "Dst")
LONG_LAGS_HOURS = tuple(range(48, 3, -1))
LONG_HISTORY_NAMES = tuple(
    f"{channel}_lag_{lag}h" for lag in LONG_LAGS_HOURS for channel in LONG_CHANNELS
)
EMPIRICAL_NAMES = ("log10_JB2008_density", "log10_NRLMSISE00_density")
FEATURE_GROUPS = (
    ("query", QUERY_NAMES),
    ("solar_background", SOLAR_BACKGROUND_NAMES),
    ("solar_history", SOLAR_HISTORY_NAMES),
    ("short_history", SHORT_HISTORY_NAMES),
    ("long_history", LONG_HISTORY_NAMES),
    ("empirical", EMPIRICAL_NAMES),
)
FEATURE_NAMES = tuple(name for _group, names in FEATURE_GROUPS for name in names)
FEATURE_COUNT = len(FEATURE_NAMES)


@dataclass(frozen=True)
class FeatureSlice:
    name: str
    start: int
    stop: int
    shape: tuple[int, ...]

    @property
    def width(self) -> int:
        return self.stop - self.start


def _slices() -> tuple[FeatureSlice, ...]:
    shapes = {
        "query": (10,),
        "solar_background": (2,),
        "solar_history": (7, 4),
        "short_history": (35, 6),
        "long_history": (45, 2),
        "empirical": (2,),
    }
    cursor = 0
    feature_slices = []
    for group_name, feature_names in FEATURE_GROUPS:
        stop = cursor + len(feature_names)
        feature_slices.append(
            FeatureSlice(group_name, cursor, stop, shapes[group_name])
        )
        cursor = stop
    return tuple(feature_slices)


FEATURE_SLICES = _slices()
SLICE_BY_NAME = {
    feature_slice.name: feature_slice for feature_slice in FEATURE_SLICES
}


def validate_contract() -> None:
    if FEATURE_COUNT != 342:
        raise AssertionError(f"expected 342 inputs, found {FEATURE_COUNT}")
    if len(set(FEATURE_NAMES)) != FEATURE_COUNT:
        raise AssertionError("feature names are not unique")
    if FEATURE_SLICES[0].start != 0 or FEATURE_SLICES[-1].stop != FEATURE_COUNT:
        raise AssertionError("feature slices are not contiguous")
    for feature_slice in FEATURE_SLICES:
        width = 1
        for dimension_size in feature_slice.shape:
            width *= dimension_size
        if width != feature_slice.width:
            raise AssertionError(f"shape mismatch for {feature_slice.name}")


validate_contract()
