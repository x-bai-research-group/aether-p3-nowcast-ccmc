package org.aetherp3.nowcast;

import java.time.LocalDate;
import java.time.LocalDateTime;
import java.time.ZoneOffset;

/** Stateless construction of the exact 342 physical inputs. */
public final class FeatureAssembler {
    private final WeatherStore weather;
    private final AtmosphereProvider atmosphere;

    public FeatureAssembler(WeatherStore weather, AtmosphereProvider atmosphere) {
        this.weather = weather;
        this.atmosphere = atmosphere;
    }

    public float[] build(Observation row) {
        double[] values = new double[FeatureContract.FEATURE_COUNT];
        int at = 0;
        LocalDateTime utc = row.utc();
        LocalDate date = utc.toLocalDate();
        double dayAngle = 2.0 * Math.PI * (date.getDayOfYear() - 1.0) / date.lengthOfYear();
        double seconds = utc.toLocalTime().toSecondOfDay() + utc.getNano() * 1.0e-9;
        double utHours = seconds / 3600.0;
        double utAngle = 2.0 * Math.PI * utHours / 24.0;
        double longitude = normalizeLongitude(row.longitudeDeg());
        double lstHours = modulo24(utHours + longitude / 15.0);
        double lstAngle = 2.0 * Math.PI * lstHours / 24.0;

        values[at++] = Math.toRadians(row.latitudeDeg());
        double longitudeRad = Math.toRadians(longitude);
        values[at++] = Math.sin(longitudeRad);
        values[at++] = Math.cos(longitudeRad);
        values[at++] = row.altitudeM() / 1000.0;
        values[at++] = Math.sin(dayAngle);
        values[at++] = Math.cos(dayAngle);
        values[at++] = Math.sin(utAngle);
        values[at++] = Math.cos(utAngle);
        values[at++] = Math.sin(lstAngle);
        values[at++] = Math.cos(lstAngle);

        values[at++] = weather.nrlDailyFlux(date);
        values[at++] = weather.f30(date);
        for (int state = 0; state < 7; state++) {
            values[at++] = weather.spectral(date, "F10", state + 1);
            values[at++] = weather.spectral(date, "S10", state + 1);
            values[at++] = weather.spectral(date, "M10", state + 2);
            values[at++] = weather.spectral(date, "Y10", state + 5);
        }

        for (int lag = 170; lag >= 0; lag -= 5) {
            LocalDateTime time = utc.minusMinutes(lag);
            values[at++] = weather.dst(time);
            values[at++] = weather.ap30(time);
            double[] wind = weather.solarWind(time, 5);
            values[at++] = wind[0];
            values[at++] = wind[1];
            values[at++] = wind[2];
            values[at++] = weather.ae(time, 5);
        }
        for (int lag = 48; lag >= 4; lag--) {
            LocalDateTime time = utc.minusHours(lag);
            values[at++] = weather.ae(time, 5);
            values[at++] = weather.dst(time);
        }

        AtmosphereProvider.Densities density = atmosphere.evaluate(row);
        values[at++] = Math.log10(density.jbKgM3());
        values[at++] = Math.log10(density.msisKgM3());
        if (at != FeatureContract.FEATURE_COUNT) {
            throw new AssertionError("feature assembly produced " + at + " values");
        }
        float[] result = new float[values.length];
        for (int i = 0; i < values.length; i++) {
            if (!Double.isFinite(values[i])) throw new IllegalArgumentException("non-finite feature " + i);
            result[i] = (float) values[i];
        }
        return result;
    }

    public static float target(Observation row) {
        return (float) Math.log10(row.densityKgM3());
    }

    public static long utcUnix(Observation row) {
        return row.utc().toEpochSecond(ZoneOffset.UTC);
    }

    private static double normalizeLongitude(double longitude) {
        double result = longitude % 360.0;
        if (result > 180.0) result -= 360.0;
        if (result <= -180.0) result += 360.0;
        return result;
    }

    private static double modulo24(double value) {
        double result = value % 24.0;
        return result < 0.0 ? result + 24.0 : result;
    }
}
