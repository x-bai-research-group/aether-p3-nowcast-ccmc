package org.aetherp3.nowcast;

import static org.junit.jupiter.api.Assertions.assertEquals;

import java.lang.reflect.Field;
import java.time.LocalDate;
import java.util.Map;

import org.junit.jupiter.api.Test;

final class WeatherStoreTest {
    @SuppressWarnings("unchecked")
    @Test
    void productionSolarDefinitionsRemainExplicitAndIndependent() throws Exception {
        WeatherStore store = new WeatherStore();
        Field field = WeatherStore.class.getDeclaredField("solfsmy");
        field.setAccessible(true);
        Map<LocalDate, double[]> values = (Map<LocalDate, double[]>) field.get(store);
        LocalDate query = LocalDate.of(2024, 5, 24);
        double[] day1 = new double[11];
        day1[3] = 130.0; day1[4] = 137.25;
        day1[5] = 140.0; day1[6] = 141.0;
        double[] day2 = new double[11];
        day2[7] = 150.0; day2[8] = 151.0;
        double[] day5 = new double[11];
        day5[9] = 160.0; day5[10] = 161.0;
        values.put(query.minusDays(1), day1);
        values.put(query.minusDays(2), day2);
        values.put(query.minusDays(5), day5);

        WeatherStore.JbSolar jb = store.jbSolar(query);
        assertEquals(137.25, jb.f10b(), 0.0);
        assertEquals(141.0, jb.s10b(), 0.0);
        assertEquals(151.0, jb.m10b(), 0.0);
        assertEquals(161.0, jb.y10b(), 0.0);

        Field swAllField = WeatherStore.class.getDeclaredField("swAll");
        swAllField.setAccessible(true);
        Map<LocalDate, double[]> swAll = (Map<LocalDate, double[]>) swAllField.get(store);
        double[] swAllDay = new double[33];
        swAllDay[31] = 222.0; // centered value, deliberately different
        swAllDay[32] = 211.0; // causal trailing value used by production MSIS
        swAll.put(query, swAllDay);
        assertEquals(211.0, store.nrlAverageFlux(query), 0.0);
    }
}
