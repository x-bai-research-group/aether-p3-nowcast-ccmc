package org.aetherp3.nowcast;

import java.io.BufferedOutputStream;
import java.io.DataOutputStream;
import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.time.LocalDateTime;
import java.time.ZoneOffset;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.concurrent.ExecutionException;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.Future;

import org.orekit.data.DataContext;
import org.orekit.data.DirectoryCrawler;

/** Builds the shared drivers and point-dependent empirical anchors for one 3-D grid. */
public final class GridFeatureMain {
    private GridFeatureMain() {}

    public static void main(String[] arguments) {
        try {
            run(parse(arguments));
        } catch (Exception ex) {
            System.err.println("ERROR: " + ex.getMessage());
            if (Boolean.getBoolean("aether.debug")) ex.printStackTrace(System.err);
            System.exit(2);
        }
    }

    static void run(Options options) throws IOException {
        FeatureContract.featureCount(options.contract());
        requireDirectory(options.weather(), "space weather");
        requireDirectory(options.orekit(), "Orekit data");
        if (options.utc().getSecond() != 0 || options.utc().getNano() != 0
                || options.utc().getMinute() % 5 != 0) {
            throw new IllegalArgumentException("--utc must lie on the five-minute UTC grid");
        }
        double[] latitude = axis(options.latitudeStart(), options.latitudeEnd(),
                options.latitudeStep(), "latitude");
        double[] longitude = axis(options.longitudeStart(), options.longitudeEnd(),
                options.longitudeStep(), "longitude");
        double[] altitude = axis(options.altitudeStart(), options.altitudeEnd(),
                options.altitudeStep(), "altitude");
        if (latitude[0] < -90.0 || latitude[latitude.length - 1] > 90.0) {
            throw new IllegalArgumentException("latitude grid exceeds [-90, 90] degrees");
        }
        if (altitude[0] < 100.0 || altitude[altitude.length - 1] > 1500.0) {
            throw new IllegalArgumentException("altitude grid exceeds [100, 1500] km");
        }

        Files.createDirectories(options.output());
        Path sharedPath = options.output().resolve("shared_features.bin");
        Path empiricalPath = options.output().resolve("empirical_anchors.bin");
        Path metadataPath = options.output().resolve("grid_features.json");
        for (Path path : new Path[]{sharedPath, empiricalPath, metadataPath}) {
            if (Files.exists(path)) throw new IOException("output already exists: " + path);
        }

        DataContext.getDefault().getDataProvidersManager()
                .addProvider(new DirectoryCrawler(options.orekit().toFile()));
        WeatherStore weather = WeatherStore.load(options.weather());
        AtmosphereProvider atmosphere = new AtmosphereProvider(weather);
        FeatureAssembler assembler = new FeatureAssembler(weather, atmosphere);
        Observation first = observation(options.utc(), altitude[0], latitude[0], longitude[0]);
        writeFloats(sharedPath, assembler.build(first));

        long points = (long) altitude.length * latitude.length * longitude.length;
        int workers = Math.min(options.workers(), (int) Math.min(points, Integer.MAX_VALUE));
        AtmosphereProvider[] providers = new AtmosphereProvider[workers];
        for (int worker = 0; worker < workers; worker++) {
            providers[worker] = new AtmosphereProvider(weather);
        }
        ExecutorService executor = Executors.newFixedThreadPool(workers);
        try (DataOutputStream output = new DataOutputStream(new BufferedOutputStream(
                Files.newOutputStream(empiricalPath), 1 << 20))) {
            for (int height = 0; height < altitude.length; height++) {
                int cells = latitude.length * longitude.length;
                float[] layer = new float[cells * 2];
                List<Future<?>> futures = new ArrayList<>(workers);
                final double heightKm = altitude[height];
                for (int worker = 0; worker < workers; worker++) {
                    final int thread = worker;
                    futures.add(executor.submit(() -> {
                        for (int cell = thread; cell < cells; cell += workers) {
                            int latIndex = cell / longitude.length;
                            int lonIndex = cell % longitude.length;
                            AtmosphereProvider.Densities values = providers[thread].evaluate(
                                    observation(options.utc(), heightKm,
                                            latitude[latIndex], longitude[lonIndex]));
                            layer[cell * 2] = (float) Math.log10(values.jbKgM3());
                            layer[cell * 2 + 1] = (float) Math.log10(values.msisKgM3());
                        }
                    }));
                }
                for (Future<?> future : futures) {
                    try {
                        future.get();
                    } catch (InterruptedException ex) {
                        Thread.currentThread().interrupt();
                        throw new IOException("grid feature generation was interrupted", ex);
                    } catch (ExecutionException ex) {
                        throw new IOException("empirical grid evaluation failed", ex.getCause());
                    }
                }
                for (float value : layer) writeFloat(output, value);
                System.out.printf("[grid-features] altitude=%.1f km layer=%d/%d points=%,d/%,d%n",
                        altitude[height], height + 1, altitude.length,
                        (long) (height + 1) * latitude.length * longitude.length, points);
            }
        } finally {
            executor.shutdownNow();
        }
        long expectedBytes = points * 2L * Float.BYTES;
        if (Files.size(empiricalPath) != expectedBytes) {
            throw new IOException("empirical-anchor file has unexpected size");
        }
        String json = """
                {
                  "contract": "%s",
                  "utc": "%sZ",
                  "utc_unix": %d,
                  "cadence_seconds": 300,
                  "record_order": ["altitude", "latitude", "longitude"],
                  "latitude": {"start_deg": %.9f, "end_deg": %.9f, "step_deg": %.9f, "count": %d},
                  "longitude": {"start_deg": %.9f, "end_deg": %.9f, "step_deg": %.9f, "count": %d},
                  "altitude": {"start_km": %.9f, "end_km": %.9f, "step_km": %.9f, "count": %d},
                  "points": %d,
                  "shared_features": "%s",
                  "empirical_anchors": "%s",
                  "empirical_columns": ["log10_JB2008_density", "log10_NRLMSISE00_density"]
                }
                """.formatted(
                options.contract(), options.utc(), options.utc().toEpochSecond(ZoneOffset.UTC),
                latitude[0], latitude[latitude.length - 1], options.latitudeStep(), latitude.length,
                longitude[0], longitude[longitude.length - 1], options.longitudeStep(), longitude.length,
                altitude[0], altitude[altitude.length - 1], options.altitudeStep(), altitude.length,
                points, sharedPath.getFileName(), empiricalPath.getFileName());
        Files.writeString(metadataPath, json, StandardCharsets.UTF_8);
        System.out.printf("[saved] %s points=%,d%n", metadataPath, points);
    }

    private static Observation observation(LocalDateTime utc, double altitudeKm,
                                           double latitudeDeg, double longitudeDeg) {
        // Canonicalize the duplicated date-line coordinate before every physical
        // model call.  -180 and +180 degrees are the same location and must not
        // acquire different empirical anchors from floating-point path choices.
        double canonicalLongitude = longitudeDeg % 360.0;
        if (canonicalLongitude > 180.0) canonicalLongitude -= 360.0;
        if (canonicalLongitude <= -180.0) canonicalLongitude += 360.0;
        return new Observation(utc, utc, 1.0e-12, altitudeKm * 1000.0,
                latitudeDeg, canonicalLongitude);
    }

    private static void writeFloats(Path path, float[] values) throws IOException {
        try (DataOutputStream output = new DataOutputStream(new BufferedOutputStream(
                Files.newOutputStream(path)))) {
            for (float value : values) writeFloat(output, value);
        }
    }

    private static void writeFloat(DataOutputStream output, float value) throws IOException {
        if (!Float.isFinite(value)) throw new IllegalArgumentException("non-finite grid feature");
        output.writeInt(Integer.reverseBytes(Float.floatToIntBits(value)));
    }

    private static double[] axis(double start, double end, double step, String name) {
        if (!Double.isFinite(start) || !Double.isFinite(end) || !Double.isFinite(step)
                || step <= 0.0 || end < start) {
            throw new IllegalArgumentException("invalid " + name + " grid");
        }
        double intervals = (end - start) / step;
        long rounded = Math.round(intervals);
        if (Math.abs(intervals - rounded) > 1.0e-9) {
            throw new IllegalArgumentException(name + " range is not divisible by its step");
        }
        int count = Math.toIntExact(rounded + 1L);
        double[] result = new double[count];
        for (int index = 0; index < count; index++) result[index] = start + index * step;
        return result;
    }

    private static Options parse(String[] arguments) {
        Map<String, String> values = new HashMap<>();
        for (int index = 0; index < arguments.length; index++) {
            if (!arguments[index].startsWith("--") || index + 1 >= arguments.length) {
                throw new IllegalArgumentException("expected --key value, got " + arguments[index]);
            }
            values.put(arguments[index], arguments[++index]);
        }
        return new Options(
                LocalDateTime.parse(required(values, "--utc").replace("Z", "")),
                Path.of(required(values, "--weather")), Path.of(required(values, "--orekit")),
                Path.of(required(values, "--output-dir")),
                number(values, "--lat-start", -89.0), number(values, "--lat-end", 89.0),
                number(values, "--lat-step", 2.0), number(values, "--lon-start", -178.0),
                number(values, "--lon-end", 178.0), number(values, "--lon-step", 4.0),
                number(values, "--alt-start", 230.0), number(values, "--alt-end", 530.0),
                number(values, "--alt-step", 10.0),
                values.getOrDefault("--feature-contract", FeatureContract.ID),
                integer(values, "--workers", Math.min(16,
                        Runtime.getRuntime().availableProcessors())));
    }

    private static String required(Map<String, String> values, String key) {
        String value = values.get(key);
        if (value == null || value.isBlank()) throw new IllegalArgumentException("missing " + key);
        return value;
    }

    private static double number(Map<String, String> values, String key, double fallback) {
        return Double.parseDouble(values.getOrDefault(key, Double.toString(fallback)));
    }

    private static int integer(Map<String, String> values, String key, int fallback) {
        int result = Integer.parseInt(values.getOrDefault(key, Integer.toString(fallback)));
        if (result <= 0) throw new IllegalArgumentException(key + " must be positive");
        return result;
    }

    private static void requireDirectory(Path path, String label) throws IOException {
        if (!Files.isDirectory(path)) throw new IOException(label + " directory missing: " + path);
    }

    record Options(LocalDateTime utc, Path weather, Path orekit, Path output,
                   double latitudeStart, double latitudeEnd, double latitudeStep,
                   double longitudeStart, double longitudeEnd, double longitudeStep,
                   double altitudeStart, double altitudeEnd, double altitudeStep,
                   String contract, int workers) {
        Options { FeatureContract.featureCount(contract); }
    }
}
