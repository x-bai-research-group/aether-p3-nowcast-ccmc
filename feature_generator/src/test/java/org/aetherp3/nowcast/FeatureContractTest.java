package org.aetherp3.nowcast;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertTrue;

import org.junit.jupiter.api.Test;

final class FeatureContractTest {
    @Test
    void contractHasExactDimensionsAndPeriodicLongitude() {
        assertEquals(342, FeatureContract.names().size());
        assertEquals(342, FeatureContract.names().stream().distinct().count());
        assertTrue(FeatureContract.names().contains("query_sin_lon"));
        assertTrue(FeatureContract.names().contains("query_cos_lon"));
        assertTrue(FeatureContract.names().contains("F107_previous_day"));
        assertTrue(FeatureContract.names().contains("F10_lag_1d"));
        assertTrue(!FeatureContract.names().contains("SOLFSMY_F81c_lag_1d"));
        assertTrue(!FeatureContract.names().contains("F107A_81d_trailing"));
    }

    @Test
    void contractGroupsAreContiguous() {
        int cursor = 0;
        for (FeatureContract.Group group : FeatureContract.groups().values()) {
            assertEquals(cursor, group.start());
            cursor = group.stop();
        }
        assertEquals(FeatureContract.FEATURE_COUNT, cursor);
    }

    @Test
    void onlyProductionContractIsAccepted() {
        assertEquals(342, FeatureContract.featureCount(FeatureContract.ID));
    }
}
