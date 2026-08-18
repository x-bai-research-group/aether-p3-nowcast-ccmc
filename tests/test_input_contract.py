from aether_p3_nowcast.contract import (
    FEATURE_COUNT,
    FEATURE_NAMES,
    FEATURE_SLICES,
    validate_contract,
)


def test_contract_is_complete_and_unique():
    validate_contract()
    assert FEATURE_COUNT == 342
    assert len(FEATURE_NAMES) == len(set(FEATURE_NAMES))
    assert {
        feature_slice.name: feature_slice.shape
        for feature_slice in FEATURE_SLICES
    } == {
        "query": (10,),
        "solar_background": (2,),
        "solar_history": (7, 4),
        "short_history": (35, 6),
        "long_history": (45, 2),
        "empirical": (2,),
    }


def test_periodic_longitude_replaces_scalar_longitude():
    assert "query_lon_rad" not in FEATURE_NAMES
    assert "query_sin_lon" in FEATURE_NAMES
    assert "query_cos_lon" in FEATURE_NAMES
