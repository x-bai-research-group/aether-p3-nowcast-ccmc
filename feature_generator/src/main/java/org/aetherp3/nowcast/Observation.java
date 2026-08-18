package org.aetherp3.nowcast;

import java.time.LocalDateTime;

public record Observation(LocalDateTime utc, LocalDateTime sourceUtc, double densityKgM3,
                          double altitudeM, double latitudeDeg, double longitudeDeg) {
    public boolean usable() {
        return utc != null && sourceUtc != null
                && Double.isFinite(densityKgM3) && densityKgM3 > 1.0e-18 && densityKgM3 < 1.0e-6
                && Double.isFinite(altitudeM) && altitudeM >= 100_000.0 && altitudeM <= 1_500_000.0
                && Double.isFinite(latitudeDeg) && latitudeDeg >= -90.0 && latitudeDeg <= 90.0
                && Double.isFinite(longitudeDeg) && Math.abs(longitudeDeg) <= 720.0;
    }

    public Observation onGrid(LocalDateTime gridUtc) {
        return new Observation(gridUtc, sourceUtc, densityKgM3, altitudeM,
                latitudeDeg, longitudeDeg);
    }
}
