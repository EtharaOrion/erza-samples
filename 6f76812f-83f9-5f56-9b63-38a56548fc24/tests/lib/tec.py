"""Geometry-free code reduction to vertical total electron content.

Constants are the ones the task statement pins:
  * GPS L1 / L2 carrier frequencies, RINEX 3.05 table (files.igs.org,
    "L1 / 1575.42", "L2 / 1227.60" MHz);
  * the speed of light in vacuum, exact by SI definition;
  * the ionospheric constant kappa = e^2 / (8 pi^2 eps0 m_e) = 40.3082 m^3 s^-2
    from the CODATA values in physics.nist.gov/cuu/Constants/Table/allascii.txt;
  * the single-layer shell, BASE RADIUS 6371.0 km and HGT1 450.0 km, as
    carried in the header of a CODE global ionosphere map (IONEX).
"""
import math

F1_HZ = 1575.42e6
F2_HZ = 1227.60e6
C_LIGHT = 299792458.0
KAPPA = 40.3082
EARTH_RADIUS_KM = 6371.0
SHELL_HEIGHT_KM = 450.0
TECU = 1.0e16

# TECU of slant content per metre of geometry-free code delay, sign included.
TECU_PER_METRE = (
    F1_HZ * F1_HZ * F2_HZ * F2_HZ / (KAPPA * (F1_HZ * F1_HZ - F2_HZ * F2_HZ)) / TECU
)


def obliquity(elevation_deg):
    """Single-layer slant-to-vertical factor cos(z') at the pierce point."""
    ratio = EARTH_RADIUS_KM / (EARTH_RADIUS_KM + SHELL_HEIGHT_KM)
    sin_zp = ratio * math.cos(math.radians(elevation_deg))
    return math.sqrt(1.0 - sin_zp * sin_zp)


def slant_tec(range_l1_m, range_l2_m, total_bias_ns):
    """Calibrated slant content, TECU, from one epoch's two code ranges."""
    geometry_free = range_l1_m - range_l2_m
    bias_metres = C_LIGHT * total_bias_ns * 1.0e-9
    return -TECU_PER_METRE * (geometry_free - bias_metres)


def vertical_tec(range_l1_m, range_l2_m, elevation_deg, total_bias_ns):
    return slant_tec(range_l1_m, range_l2_m, total_bias_ns) * obliquity(elevation_deg)


def arc_mean_vtec(epochs, total_bias_ns):
    """Arithmetic mean of the per-epoch vertical content over one arc.

    `epochs` is a sequence of (range_l1_m, range_l2_m, elevation_deg).
    """
    values = [vertical_tec(r1, r2, el, total_bias_ns) for r1, r2, el in epochs]
    return sum(values) / len(values)
