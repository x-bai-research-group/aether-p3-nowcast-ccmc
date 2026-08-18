package org.aetherp3.nowcast;

import java.io.BufferedReader;
import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.time.LocalDate;
import java.time.LocalDateTime;
import java.time.ZoneOffset;
import java.util.Arrays;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

/** Unit-explicit in-memory space-weather archive for production features. */
public final class WeatherStore {
    public record JbSolar(double f10, double f10b, double s10, double s10b,
                          double m10, double m10b, double y10, double y10b) {}

    private final Map<LocalDate, double[]> solfsmy = new HashMap<>();
    private final Map<LocalDate, double[]> swAll = new HashMap<>();
    private final Map<LocalDate, double[]> f30 = new HashMap<>();
    private final Map<LocalDate, double[]> dtc = new HashMap<>();
    private final Map<LocalDateTime, Double> dst = new HashMap<>();
    private final Map<LocalDateTime, Double> ap30 = new HashMap<>();
    private DenseMinutes ae;
    private DenseMinutes solarWind;

    public static WeatherStore load(Path root) throws IOException {
        WeatherStore store = new WeatherStore();
        store.loadDailyDoy(root.resolve("SOLFSMY.TXT"), store.solfsmy, 11, "SOLFSMY");
        store.loadDailyYmd(root.resolve("SW-All.txt"), store.swAll, 33, "SW-All");
        store.loadDailyYmd(root.resolve("radio_flux_adjusted.txt"), store.f30, 5, "F30");
        store.loadDailyDoy(root.resolve("DTCFILE.TXT"), store.dtc, 26, "DTC");
        store.loadIndex(firstExisting(root.resolve("DST.csv"), root.resolve("DST.txt")), store.dst);
        store.loadAp30(root.resolve("Apo30.csv"));
        store.ae = DenseMinutes.loadAe(firstExisting(root.resolve("AE.csv"), root.resolve("AE.txt")));
        store.solarWind = DenseMinutes.loadSolarWind(root.resolve("solarwind.csv"));
        return store;
    }

    public JbSolar jbSolar(LocalDate date) {
        double[] day1 = require(solfsmy, date.minusDays(1), "SOLFSMY D-1");
        double[] day2 = require(solfsmy, date.minusDays(2), "SOLFSMY D-2");
        double[] day5 = require(solfsmy, date.minusDays(5), "SOLFSMY D-5");
        return new JbSolar(day1[3], day1[4], day1[5], day1[6],
                day2[7], day2[8], day5[9], day5[10]);
    }

    public double spectral(LocalDate date, String channel, int lagDays) {
        double[] row = require(solfsmy, date.minusDays(lagDays), "SOLFSMY " + channel);
        int column = switch (channel) {
            case "F10" -> 3;
            case "S10" -> 5;
            case "M10" -> 7;
            case "Y10" -> 9;
            default -> throw new IllegalArgumentException("unknown solar channel " + channel);
        };
        return finite(row[column], channel);
    }

    public double f107a(LocalDate date) {
        // SW-All zero-based column 32 is the last/trailing 81-day observed
        // average. Column 31 is centered and would leak future observations.
        return finite(require(swAll, date, "SW-All trailing F10.7A")[32],
                "trailing F10.7A");
    }

    public double f30(LocalDate date) {
        return finite(require(f30, date, "F30")[4], "F30");
    }

    public double nrlDailyFlux(LocalDate date) {
        return finite(require(swAll, date.minusDays(1), "SW-All F10.7 D-1")[30], "F10.7");
    }

    public double nrlAverageFlux(LocalDate date) {
        return f107a(date);
    }

    public double dstdtc(LocalDateTime utc) {
        double[] row = require(dtc, utc.toLocalDate(), "DTC");
        return finite(row[utc.getHour() + 2], "DTC hour");
    }

    public double dst(LocalDateTime utc) {
        LocalDateTime key = utc.withMinute(0).withSecond(0).withNano(0);
        Double value = dst.get(key);
        if (value == null || !Double.isFinite(value)) throw missing("Dst", key);
        return value;
    }

    public double ap30(LocalDateTime utc) {
        int minute = utc.getMinute() < 30 ? 0 : 30;
        LocalDateTime key = utc.withMinute(minute).withSecond(0).withNano(0);
        Double value = ap30.get(key);
        if (value == null || !Double.isFinite(value)) throw missing("Ap30", key);
        return value;
    }

    public double ae(LocalDateTime utc, int maximumAgeMinutes) {
        return causal(ae, utc, maximumAgeMinutes, 0, "AE");
    }

    public double[] solarWind(LocalDateTime utc, int maximumAgeMinutes) {
        for (int age = 0; age <= maximumAgeMinutes; age++) {
            double[] value = solarWind.value(utc.minusMinutes(age));
            if (value != null) return value;
        }
        throw missing("solar wind", utc);
    }

    public double[] nrlAp(LocalDateTime utc) {
        double[] values = new double[7];
        values[0] = finite(require(swAll, utc.toLocalDate(), "daily Ap")[22], "daily Ap");
        values[1] = ap3h(utc);
        values[2] = ap3h(utc.minusHours(3));
        values[3] = ap3h(utc.minusHours(6));
        values[4] = ap3h(utc.minusHours(9));
        values[5] = meanEightAp(utc.minusHours(12));
        values[6] = meanEightAp(utc.minusHours(36));
        return values;
    }

    private double ap3h(LocalDateTime utc) {
        return finite(require(swAll, utc.toLocalDate(), "3-hour Ap")[14 + utc.getHour() / 3], "Ap");
    }

    private double meanEightAp(LocalDateTime latest) {
        double sum = 0.0;
        for (int i = 0; i < 8; i++) sum += ap3h(latest.minusHours(3L * i));
        return sum / 8.0;
    }

    private static double causal(DenseMinutes series, LocalDateTime utc, int maximumAge,
                                 int channel, String name) {
        for (int age = 0; age <= maximumAge; age++) {
            double[] value = series.value(utc.minusMinutes(age));
            if (value != null) return value[channel];
        }
        throw missing(name, utc);
    }

    private void loadDailyDoy(Path file, Map<LocalDate, double[]> target,
                              int minimumColumns, String name) throws IOException {
        for (double[] row : numericRows(file)) {
            if (row.length < minimumColumns) continue;
            put(target, LocalDate.ofYearDay(integer(row[0]), integer(row[1])), row, name);
        }
        if (target.isEmpty()) throw new IOException(name + " has no rows: " + file);
    }

    private void loadDailyYmd(Path file, Map<LocalDate, double[]> target,
                              int minimumColumns, String name) throws IOException {
        for (double[] row : numericRows(file)) {
            if (row.length < minimumColumns) continue;
            put(target, LocalDate.of(integer(row[0]), integer(row[1]), integer(row[2])), row, name);
        }
        if (target.isEmpty()) throw new IOException(name + " has no rows: " + file);
    }

    private void loadIndex(Path file, Map<LocalDateTime, Double> target) throws IOException {
        try (BufferedReader reader = Files.newBufferedReader(file)) {
            String line;
            while ((line = reader.readLine()) != null) {
                String[] token = line.trim().split("[,\\s]+");
                try {
                    LocalDateTime utc;
                    double value;
                    if (token.length >= 3 && token[0].matches("\\d{4}-\\d{2}-\\d{2}")) {
                        utc = LocalDateTime.parse(token[0] + "T" + token[1].replace("Z", ""));
                        value = Double.parseDouble(token[token.length - 1]);
                    } else if (token[0].contains("T") || token[0].contains("-")) {
                        utc = LocalDateTime.parse(token[0].replace("Z", ""));
                        value = Double.parseDouble(token[token.length - 1]);
                    } else {
                        double[] row = parse(token);
                        int year = integer(row[0]);
                        if (row.length >= 7 && integer(row[1]) <= 12) {
                            utc = LocalDateTime.of(year, integer(row[1]), integer(row[2]),
                                    integer(row[3]), integer(row[4]), integer(row[5]));
                        } else if (row.length >= 5) {
                            utc = LocalDate.ofYearDay(year, integer(row[1]))
                                    .atTime(integer(row[2]), integer(row[3]));
                        } else continue;
                        value = row[row.length - 1];
                    }
                    if (!Double.isFinite(value) || Math.abs(value) >= 9000.0) continue;
                    utc = utc.withMinute(0).withSecond(0).withNano(0);
                    target.putIfAbsent(utc, value);
                } catch (RuntimeException ignored) {
                    // Header and malformed non-data rows are ignored.
                }
            }
        }
        if (target.isEmpty()) throw new IOException("Dst has no rows: " + file);
    }

    private void loadAp30(Path file) throws IOException {
        for (double[] row : numericRows(file)) {
            if (row.length < 9) continue;
            int hour = (int) Math.floor(row[3]);
            int minute = (int) Math.round((row[3] - hour) * 60.0);
            LocalDateTime available = LocalDateTime.of(
                    integer(row[0]), integer(row[1]), integer(row[2]), hour, minute).plusMinutes(30);
            ap30.put(available, finite(row[8], "Ap30"));
        }
        if (ap30.isEmpty()) throw new IOException("Ap30 has no rows: " + file);
    }

    private static List<double[]> numericRows(Path file) throws IOException {
        if (!Files.isRegularFile(file)) throw new IOException("required file missing: " + file);
        try (var lines = Files.lines(file)) {
            return lines.map(String::trim).filter(text -> !text.isEmpty())
                    .filter(text -> Character.isDigit(text.charAt(0)) || "+-.".indexOf(text.charAt(0)) >= 0)
                    .map(text -> parse(text.split("[,\\s]+"))).toList();
        }
    }

    private static double[] parse(String[] tokens) {
        double[] result = new double[tokens.length];
        for (int i = 0; i < tokens.length; i++) {
            try { result[i] = Double.parseDouble(tokens[i]); }
            catch (NumberFormatException ex) { result[i] = Double.NaN; }
        }
        return result;
    }

    private static int integer(double value) {
        if (!Double.isFinite(value) || value != Math.rint(value)) {
            throw new IllegalArgumentException("expected integer, got " + value);
        }
        return (int) value;
    }

    private static double finite(double value, String name) {
        if (!Double.isFinite(value)) throw new IllegalArgumentException(name + " is non-finite");
        return value;
    }

    private static <K> double[] require(Map<K, double[]> values, K key, String name) {
        double[] result = values.get(key);
        if (result == null) throw new IllegalArgumentException(name + " missing at " + key);
        return result;
    }

    private static <K> void put(Map<K, double[]> target, K key, double[] row, String name)
            throws IOException {
        if (target.putIfAbsent(key, Arrays.copyOf(row, row.length)) != null) {
            throw new IOException(name + " duplicate key " + key);
        }
    }

    private static Path firstExisting(Path first, Path second) throws IOException {
        if (Files.isRegularFile(first)) return first;
        if (Files.isRegularFile(second)) return second;
        throw new IOException("required file missing: " + first + " or " + second);
    }

    private static IllegalArgumentException missing(String name, Object utc) {
        return new IllegalArgumentException(name + " missing at " + utc);
    }

    private static final class DenseMinutes {
        private final long firstMinute;
        private final float[][] values;

        private DenseMinutes(long firstMinute, int length, int channels) {
            this.firstMinute = firstMinute;
            values = new float[channels][length];
            for (float[] channel : values) Arrays.fill(channel, Float.NaN);
        }

        static DenseMinutes loadAe(Path file) throws IOException {
            return load(file, 1, line -> {
                String[] token = line.trim().split("[,\\s]+");
                if (token.length < 5 || token[0].equalsIgnoreCase("year")) return null;
                try {
                    long minute = LocalDate.ofYearDay(Integer.parseInt(token[0]), Integer.parseInt(token[1]))
                            .atTime(Integer.parseInt(token[2]), Integer.parseInt(token[3]))
                            .toEpochSecond(ZoneOffset.UTC) / 60L;
                    float value = Float.parseFloat(token[4]);
                    if (!Float.isFinite(value) || value < 0.0f || value >= 99_999.0f) return null;
                    return new Point(minute, new float[]{value});
                } catch (RuntimeException ex) { return null; }
            });
        }

        static DenseMinutes loadSolarWind(Path file) throws IOException {
            return load(file, 3, line -> {
                String[] token = line.trim().split(",", -1);
                if (token.length < 13) return null;
                try {
                    long minute = LocalDate.ofYearDay(Integer.parseInt(token[0].trim()),
                                    Integer.parseInt(token[1].trim()))
                            .atTime(Integer.parseInt(token[2].trim()), Integer.parseInt(token[3].trim()))
                            .toEpochSecond(ZoneOffset.UTC) / 60L;
                    float bz = Float.parseFloat(token[7].trim());
                    float speed = Float.parseFloat(token[8].trim());
                    float density = Float.parseFloat(token[12].trim());
                    if (Math.abs(bz) >= 1000.0f || speed <= 0.0f || speed >= 5000.0f
                            || density < 0.0f || density >= 1000.0f) return null;
                    return new Point(minute, new float[]{bz, speed, density});
                } catch (RuntimeException ex) { return null; }
            });
        }

        private static DenseMinutes load(Path file, int channels, Parser parser) throws IOException {
            if (!Files.isRegularFile(file)) throw new IOException("required file missing: " + file);
            long first = Long.MAX_VALUE, last = Long.MIN_VALUE;
            try (BufferedReader reader = Files.newBufferedReader(file)) {
                String line;
                while ((line = reader.readLine()) != null) {
                    Point point = parser.parse(line);
                    if (point != null) { first = Math.min(first, point.minute()); last = Math.max(last, point.minute()); }
                }
            }
            if (first == Long.MAX_VALUE) throw new IOException("minute series has no rows: " + file);
            DenseMinutes result = new DenseMinutes(first, Math.toIntExact(last - first + 1), channels);
            try (BufferedReader reader = Files.newBufferedReader(file)) {
                String line;
                while ((line = reader.readLine()) != null) {
                    Point point = parser.parse(line);
                    if (point == null) continue;
                    int index = Math.toIntExact(point.minute() - first);
                    for (int channel = 0; channel < channels; channel++) {
                        result.values[channel][index] = point.values()[channel];
                    }
                }
            }
            return result;
        }

        double[] value(LocalDateTime utc) {
            long offset = utc.withSecond(0).withNano(0).toEpochSecond(ZoneOffset.UTC) / 60L - firstMinute;
            if (offset < 0 || offset >= values[0].length) return null;
            double[] result = new double[values.length];
            for (int channel = 0; channel < values.length; channel++) {
                float value = values[channel][(int) offset];
                if (!Float.isFinite(value)) return null;
                result[channel] = value;
            }
            return result;
        }

        private interface Parser { Point parse(String line); }
        private record Point(long minute, float[] values) {}
    }
}
