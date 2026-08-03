"""Single-source FITS WCS gnomonic (TAN) pixel -> sky pipeline.

Implements the REAL, STANDARD FITS world-coordinate-system semantics for a
gnomonic (TAN) projection exactly as specified in Greisen & Calabretta (2002),
"Representations of celestial coordinates in FITS" (Paper II). The oracle, the
verifier and the build-time generator all import THIS module, so the shipped
data, the frozen expected values and the grade-time recomputation can never
drift apart.

The chain, in the order the standard defines it:

  1. linear step - intermediate world coordinates (x, y), in degrees, from the
     CD matrix applied to the offset of the pixel coordinate from the reference
     pixel. Catalogue pixel coordinates and CRPIXj are both 1-based FITS pixel
     coordinates, so the raw difference is used:

         x = CD1_1*(p1 - CRPIX1) + CD1_2*(p2 - CRPIX2)
         y = CD2_1*(p1 - CRPIX1) + CD2_2*(p2 - CRPIX2)

  2. inverse projection - native spherical coordinates (phi, theta) of the TAN
     projection (Paper II, table 13):

         R_theta = sqrt(x^2 + y^2)              [degrees]
         phi     = arg(-y, x)   i.e. atan2(x, -y)
         theta   = atan(180 / (pi * R_theta))

  3. spherical rotation - native to celestial. TAN is a zenithal projection, so
     theta_0 = 90 deg, the fiducial point is the native pole, and therefore
     (alpha_p, delta_p) = (CRVAL1, CRVAL2). The native longitude of the
     celestial pole is phi_p = LONPOLE. Paper II eq. (2):

         sin(delta) = sin(theta) sin(delta_p)
                      + cos(theta) cos(delta_p) cos(phi - phi_p)
         alpha = alpha_p + arg( sin(theta) cos(delta_p)
                                  - cos(theta) sin(delta_p) cos(phi - phi_p),
                                -cos(theta) sin(phi - phi_p) )

  4. RA is wrapped into [0, 360).

`bugs` is a build-time-only knob (never used by the oracle or the verifier).
Each flag swaps exactly ONE step of the chain above for a different reading of
the same standard, which is how gen.py proves each step is load-bearing.
"""
import csv
import math
import os

ALL_BUGS = (
    "no_lonpole",         # phi_p = 0 instead of LONPOLE (drops the native-pole
                          # longitude from the spherical rotation entirely)
    "cd_transposed",      # CD^T instead of CD (off-diagonal terms exchanged)
    "zero_based_pixels",  # pixel coordinates re-based to 0 while CRPIXj is left
                          # 1-based, i.e. an extra -1 on both axes
    "swapped_axes",       # phi = atan2(-y, x) instead of atan2(x, -y)
)

DEG = math.pi / 180.0


# --------------------------------------------------------------------------- #
# input                                                                        #
# --------------------------------------------------------------------------- #
def read_header(path):
    """Parse a FITS-style ASCII header (one `KEY = VALUE [/ comment]` card per
    line) into a dict. Quoted card values are returned as stripped strings,
    numeric card values as floats, anything else as the raw token."""
    hdr = {}
    with open(path) as fh:
        for line in fh:
            s = line.rstrip("\n").strip()
            if not s or s.startswith("#") or s == "END" or "=" not in s:
                continue
            key, rest = s.split("=", 1)
            key = key.strip()
            rest = rest.strip()
            if rest.startswith("'"):
                end = rest.index("'", 1)
                hdr[key] = rest[1:end].strip()
                continue
            rest = rest.split("/")[0].strip()
            try:
                hdr[key] = float(rest)
            except ValueError:
                hdr[key] = rest
    return hdr


def read_sources(path):
    """Return {source_id: (x, y)} of 1-based FITS pixel coordinates, read from
    the `source_id,x,y` CSV."""
    src = {}
    with open(path, newline="") as fh:
        for row in csv.DictReader(fh):
            src[row["source_id"].strip()] = (float(row["x"]), float(row["y"]))
    return src


# --------------------------------------------------------------------------- #
# the standard chain                                                           #
# --------------------------------------------------------------------------- #
def pixel_to_intermediate(px, py, hdr, bugs=frozenset()):
    """1-based pixel coordinate -> intermediate world coordinates (x, y) in
    degrees, via the CD matrix."""
    if "zero_based_pixels" in bugs:
        dx = (px - 1.0) - hdr["CRPIX1"]
        dy = (py - 1.0) - hdr["CRPIX2"]
    else:
        dx = px - hdr["CRPIX1"]
        dy = py - hdr["CRPIX2"]
    cd11, cd12 = hdr["CD1_1"], hdr["CD1_2"]
    cd21, cd22 = hdr["CD2_1"], hdr["CD2_2"]
    if "cd_transposed" in bugs:
        cd12, cd21 = cd21, cd12
    x = cd11 * dx + cd12 * dy
    y = cd21 * dx + cd22 * dy
    return x, y


def intermediate_to_native(x, y, bugs=frozenset()):
    """Inverse TAN: intermediate world coordinates (deg) -> native spherical
    (phi, theta) in degrees."""
    r = math.hypot(x, y)
    if "swapped_axes" in bugs:
        phi = math.degrees(math.atan2(-y, x))
    else:
        phi = math.degrees(math.atan2(x, -y))
    # atan2(180/pi, r) is atan(180/(pi*r)) with the r -> 0 limit (theta = 90)
    theta = math.degrees(math.atan2(180.0 / math.pi, r))
    return phi, theta


def native_to_celestial(phi, theta, hdr, bugs=frozenset()):
    """Native spherical (phi, theta) -> celestial (RA, Dec), all in degrees.

    For a zenithal projection the celestial coordinates of the native pole are
    (CRVAL1, CRVAL2) and its native longitude is phi_p = LONPOLE."""
    if "no_lonpole" in bugs:
        phi_p = 0.0
    else:
        phi_p = float(hdr.get("LONPOLE", 180.0))
    ap = hdr["CRVAL1"] * DEG
    dp = hdr["CRVAL2"] * DEG
    dphi = (phi - phi_p) * DEG
    th = theta * DEG
    sin_th, cos_th = math.sin(th), math.cos(th)
    sin_dp, cos_dp = math.sin(dp), math.cos(dp)
    cos_dphi = math.cos(dphi)

    sin_dec = sin_th * sin_dp + cos_th * cos_dp * cos_dphi
    sin_dec = min(1.0, max(-1.0, sin_dec))
    dec = math.degrees(math.asin(sin_dec))

    num = -cos_th * math.sin(dphi)
    den = sin_th * cos_dp - cos_th * sin_dp * cos_dphi
    ra = math.degrees(ap + math.atan2(num, den)) % 360.0
    return ra, dec


def pixel_to_sky(px, py, hdr, bugs=frozenset()):
    """1-based pixel coordinate -> (RA, Dec) in degrees, RA in [0, 360)."""
    x, y = pixel_to_intermediate(px, py, hdr, bugs)
    phi, theta = intermediate_to_native(x, y, bugs)
    return native_to_celestial(phi, theta, hdr, bugs)


def solve_all(data_dir, bugs=frozenset()):
    """Return {source_id: {"ra_deg": float, "dec_deg": float}} for every
    catalogued source."""
    hdr = read_header(os.path.join(data_dir, "image.hdr"))
    src = read_sources(os.path.join(data_dir, "sources.csv"))
    bugs = frozenset(bugs)
    out = {}
    for sid in sorted(src):
        px, py = src[sid]
        ra, dec = pixel_to_sky(px, py, hdr, bugs)
        out[sid] = {"ra_deg": ra, "dec_deg": dec}
    return out


# --------------------------------------------------------------------------- #
# geometry helper (used by the verifier for scoring and by gen.py for QC)       #
# --------------------------------------------------------------------------- #
def angular_separation(ra1, dec1, ra2, dec2):
    """Great-circle separation in degrees between two (RA, Dec) pairs, using the
    Vincenty formula (accurate at both small and large separations)."""
    a1, d1 = ra1 * DEG, dec1 * DEG
    a2, d2 = ra2 * DEG, dec2 * DEG
    dlon = a2 - a1
    sin_d1, cos_d1 = math.sin(d1), math.cos(d1)
    sin_d2, cos_d2 = math.sin(d2), math.cos(d2)
    sin_dl, cos_dl = math.sin(dlon), math.cos(dlon)
    num = math.hypot(cos_d2 * sin_dl,
                     cos_d1 * sin_d2 - sin_d1 * cos_d2 * cos_dl)
    den = sin_d1 * sin_d2 + cos_d1 * cos_d2 * cos_dl
    return math.degrees(math.atan2(num, den))


# --------------------------------------------------------------------------- #
# generator-only inverses (never used by the oracle or the verifier)           #
# --------------------------------------------------------------------------- #
def celestial_to_native(ra, dec, hdr):
    """Inverse of `native_to_celestial` (Paper II eq. 5)."""
    phi_p = float(hdr.get("LONPOLE", 180.0))
    ap = hdr["CRVAL1"] * DEG
    dp = hdr["CRVAL2"] * DEG
    a = ra * DEG - ap
    d = dec * DEG
    sin_d, cos_d = math.sin(d), math.cos(d)
    sin_dp, cos_dp = math.sin(dp), math.cos(dp)
    sin_th = sin_d * sin_dp + cos_d * cos_dp * math.cos(a)
    sin_th = min(1.0, max(-1.0, sin_th))
    theta = math.degrees(math.asin(sin_th))
    num = -cos_d * math.sin(a)
    den = sin_d * cos_dp - cos_d * sin_dp * math.cos(a)
    phi = phi_p + math.degrees(math.atan2(num, den))
    return phi, theta


def native_to_intermediate(phi, theta):
    """Forward TAN (Paper II, table 13)."""
    r = (180.0 / math.pi) / math.tan(theta * DEG)
    x = r * math.sin(phi * DEG)
    y = -r * math.cos(phi * DEG)
    return x, y


def intermediate_to_pixel(x, y, hdr):
    """Invert the CD matrix: intermediate world coordinates -> 1-based pixel."""
    a, b = hdr["CD1_1"], hdr["CD1_2"]
    c, d = hdr["CD2_1"], hdr["CD2_2"]
    det = a * d - b * c
    dx = (d * x - b * y) / det
    dy = (-c * x + a * y) / det
    return hdr["CRPIX1"] + dx, hdr["CRPIX2"] + dy


def sky_to_pixel(ra, dec, hdr):
    """(RA, Dec) in degrees -> 1-based pixel coordinate."""
    phi, theta = celestial_to_native(ra, dec, hdr)
    x, y = native_to_intermediate(phi, theta)
    return intermediate_to_pixel(x, y, hdr)
