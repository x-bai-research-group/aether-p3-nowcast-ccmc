package org.aetherp3.nowcast;

import java.time.LocalDateTime;

import org.hipparchus.geometry.euclidean.threed.Vector3D;
import org.orekit.bodies.CelestialBodyFactory;
import org.orekit.bodies.GeodeticPoint;
import org.orekit.bodies.OneAxisEllipsoid;
import org.orekit.frames.Frame;
import org.orekit.frames.FramesFactory;
import org.orekit.models.earth.atmosphere.JB2008;
import org.orekit.models.earth.atmosphere.JB2008InputParameters;
import org.orekit.models.earth.atmosphere.NRLMSISE00;
import org.orekit.models.earth.atmosphere.NRLMSISE00InputParameters;
import org.orekit.time.AbsoluteDate;
import org.orekit.time.DateTimeComponents;
import org.orekit.time.TimeScale;
import org.orekit.time.TimeScalesFactory;
import org.orekit.utils.Constants;
import org.orekit.utils.ExtendedPositionProvider;
import org.orekit.utils.IERSConventions;

/** Current-location JB2008 and NRLMSISE-00 anchors using public Orekit APIs. */
public final class AtmosphereProvider {
    public record Densities(double jbKgM3, double msisKgM3) {}

    private final TimeScale utc = TimeScalesFactory.getUTC();
    private final Frame itrf = FramesFactory.getITRF(IERSConventions.IERS_2010, true);
    private final OneAxisEllipsoid earth = new OneAxisEllipsoid(
            Constants.WGS84_EARTH_EQUATORIAL_RADIUS,
            Constants.WGS84_EARTH_FLATTENING, itrf);
    private final JB2008 jb;
    private final NRLMSISE00 msis;

    public AtmosphereProvider(WeatherStore weather) {
        ExtendedPositionProvider sun = CelestialBodyFactory.getSun();
        jb = new JB2008(new JbInputs(weather), sun, earth, utc);
        msis = new NRLMSISE00(new MsisInputs(weather), sun, earth, utc).withSwitch(9, -1);
    }

    public Densities evaluate(Observation row) {
        AbsoluteDate date = date(row.utc());
        Vector3D position = earth.transform(new GeodeticPoint(
                Math.toRadians(row.latitudeDeg()), Math.toRadians(row.longitudeDeg()), row.altitudeM()));
        double jbDensity = jb.getDensity(date, position, itrf);
        double msisDensity = msis.getDensity(date, position, itrf);
        require(jbDensity, "JB2008", row.utc());
        require(msisDensity, "NRLMSISE-00", row.utc());
        return new Densities(jbDensity, msisDensity);
    }

    private AbsoluteDate date(LocalDateTime value) {
        return new AbsoluteDate(value.getYear(), value.getMonthValue(), value.getDayOfMonth(),
                value.getHour(), value.getMinute(), value.getSecond() + value.getNano() * 1.0e-9, utc);
    }

    private static void require(double value, String model, LocalDateTime utc) {
        if (!Double.isFinite(value) || value <= 0.0) {
            throw new IllegalArgumentException(model + " returned invalid density at " + utc);
        }
    }

    private abstract static class Inputs {
        final WeatherStore weather;
        Inputs(WeatherStore weather) { this.weather = weather; }
        LocalDateTime utc(AbsoluteDate date) {
            DateTimeComponents value = date.getComponents(TimeScalesFactory.getUTC());
            return LocalDateTime.of(value.getDate().getYear(), value.getDate().getMonth(),
                    value.getDate().getDay(), value.getTime().getHour(),
                    value.getTime().getMinute(), (int) Math.floor(value.getTime().getSecond()));
        }
    }

    private static final class JbInputs extends Inputs implements JB2008InputParameters {
        JbInputs(WeatherStore weather) { super(weather); }
        @Override public AbsoluteDate getMinDate() { return AbsoluteDate.PAST_INFINITY; }
        @Override public AbsoluteDate getMaxDate() { return AbsoluteDate.FUTURE_INFINITY; }
        private WeatherStore.JbSolar solar(AbsoluteDate date) {
            return weather.jbSolar(utc(date).toLocalDate());
        }
        @Override public double getF10(AbsoluteDate date) { return solar(date).f10(); }
        @Override public double getF10B(AbsoluteDate date) { return solar(date).f10b(); }
        @Override public double getS10(AbsoluteDate date) { return solar(date).s10(); }
        @Override public double getS10B(AbsoluteDate date) { return solar(date).s10b(); }
        @Override public double getXM10(AbsoluteDate date) { return solar(date).m10(); }
        @Override public double getXM10B(AbsoluteDate date) { return solar(date).m10b(); }
        @Override public double getY10(AbsoluteDate date) { return solar(date).y10(); }
        @Override public double getY10B(AbsoluteDate date) { return solar(date).y10b(); }
        @Override public double getDSTDTC(AbsoluteDate date) { return weather.dstdtc(utc(date)); }
    }

    private static final class MsisInputs extends Inputs implements NRLMSISE00InputParameters {
        MsisInputs(WeatherStore weather) { super(weather); }
        @Override public AbsoluteDate getMinDate() { return AbsoluteDate.PAST_INFINITY; }
        @Override public AbsoluteDate getMaxDate() { return AbsoluteDate.FUTURE_INFINITY; }
        @Override public double getDailyFlux(AbsoluteDate date) {
            return weather.nrlDailyFlux(utc(date).toLocalDate());
        }
        @Override public double getAverageFlux(AbsoluteDate date) {
            return weather.nrlAverageFlux(utc(date).toLocalDate());
        }
        @Override public double[] getAp(AbsoluteDate date) { return weather.nrlAp(utc(date)); }
    }
}
