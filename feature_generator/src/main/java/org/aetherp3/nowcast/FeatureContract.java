package org.aetherp3.nowcast;

import java.util.ArrayList;
import java.util.Collections;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/** Immutable production feature contract for AETHER-P3 Nowcast. */
public final class FeatureContract {
    public static final String ID = "aether-p3-nowcast-342-v1";
    public static final int FEATURE_COUNT = 342;
    public static final String TARGET = "log10_density_kg_m3";

    public record Group(String name, int start, int stop, int[] shape) {
        public Group {
            shape = shape.clone();
            if (start < 0 || stop <= start) throw new IllegalArgumentException("invalid group range");
        }

        @Override public int[] shape() { return shape.clone(); }
        public int width() { return stop - start; }
    }

    private static final List<String> NAMES;
    private static final Map<String, Group> GROUPS;

    static {
        List<String> names = new ArrayList<>(FEATURE_COUNT);
        Map<String, Group> groups = new LinkedHashMap<>();
        add(groups, names, "query", List.of(
                "query_lat_rad", "query_sin_lon", "query_cos_lon", "query_alt_km",
                "query_sin_doy", "query_cos_doy", "query_sin_ut", "query_cos_ut",
                "query_sin_lst", "query_cos_lst"), 10);
        add(groups, names, "solar_background", List.of(
                "F107_previous_day", "F30_current_day"), 2);

        List<String> solar = new ArrayList<>(28);
        for (int state = 0; state < 7; state++) {
            solar.add("F10_lag_" + (state + 1) + "d");
            solar.add("S10_lag_" + (state + 1) + "d");
            solar.add("M10_lag_" + (state + 2) + "d");
            solar.add("Y10_lag_" + (state + 5) + "d");
        }
        add(groups, names, "solar_history", solar, 7, 4);

        String[] shortChannels = {
                "Dst", "Ap30", "Bz_GSM_nT", "V_km_s",
                "proton_number_density_n_cc", "AE"
        };
        List<String> shortHistory = new ArrayList<>(210);
        for (int lag = 170; lag >= 0; lag -= 5) {
            for (String channel : shortChannels) {
                shortHistory.add(channel + "_" + (lag == 0 ? "current" : "lag_" + lag + "m"));
            }
        }
        add(groups, names, "short_history", shortHistory, 35, 6);

        List<String> longHistory = new ArrayList<>(90);
        for (int lag = 48; lag >= 4; lag--) {
            longHistory.add("AE_lag_" + lag + "h");
            longHistory.add("Dst_lag_" + lag + "h");
        }
        add(groups, names, "long_history", longHistory, 45, 2);
        add(groups, names, "empirical", List.of(
                "log10_JB2008_density", "log10_NRLMSISE00_density"), 2);

        if (names.size() != FEATURE_COUNT) {
            throw new ExceptionInInitializerError("expected 342 inputs, got " + names.size());
        }
        if (names.stream().distinct().count() != FEATURE_COUNT) {
            throw new ExceptionInInitializerError("feature names are not unique");
        }
        NAMES = Collections.unmodifiableList(names);
        GROUPS = Collections.unmodifiableMap(groups);
    }

    private FeatureContract() {}

    private static void add(Map<String, Group> groups, List<String> all, String name,
                            List<String> values, int... shape) {
        int product = 1;
        for (int value : shape) product *= value;
        if (product != values.size()) throw new IllegalArgumentException("shape mismatch for " + name);
        int start = all.size();
        all.addAll(values);
        groups.put(name, new Group(name, start, all.size(), shape));
    }

    public static List<String> names() { return NAMES; }
    public static Map<String, Group> groups() { return GROUPS; }

    public static int featureCount(String contract) {
        if (!ID.equals(contract)) {
            throw new IllegalArgumentException("unsupported feature contract: " + contract);
        }
        return FEATURE_COUNT;
    }
}
