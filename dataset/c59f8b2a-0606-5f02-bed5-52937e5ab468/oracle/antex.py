"""Receiver-antenna phase-centre correction from an ANTEX antenna block.

An ANTEX antenna block holds, per carrier frequency, a mean phase-centre offset
(PCO) vector in the local North/East/Up frame and a table of phase-centre
variations (PCV) on a regular azimuth by zenith-angle grid. Both are in
millimetres and both belong to that one antenna model.

Three operations are needed:

  parse_antex(path)                 - read one antenna block into a dict
  los_unit(az_deg, el_deg)          - line-of-sight unit vector in (N, E, U)
  correction(block, code, az, el)   - PCO projection plus the interpolated PCV

`correction` is used unchanged by the oracle and by the verifier's live
recompute, so the reference value and the graded value come from one definition.
"""

import math

_LABELS = (
    "START OF ANTENNA", "TYPE / SERIAL NO", "METH / BY / # / DATE", "DAZI",
    "ZEN1 / ZEN2 / DZEN", "# OF FREQUENCIES", "SINEX CODE", "COMMENT",
    "VALID FROM", "VALID UNTIL", "START OF FREQUENCY", "NORTH / EAST / UP",
    "END OF FREQUENCY", "START OF FREQ RMS", "END OF FREQ RMS", "END OF ANTENNA",
)


def parse_antex(path):
    """Read a single ANTEX antenna block.

    Returns {label, dazi, zen1, zen2, dzen, freqs: {code: {pco, noazi, grid}}},
    where `grid` maps an azimuth in degrees to the list of PCV values across the
    zenith-angle nodes.
    """
    block = {"label": "", "dazi": None, "zen1": None, "zen2": None,
             "dzen": None, "freqs": {}}
    current = None
    with open(path) as fh:
        for line in fh:
            line = line.rstrip("\n")
            if not line.strip():
                continue
            label = line[60:].strip()
            if label in _LABELS:
                if label == "TYPE / SERIAL NO":
                    block["label"] = line[0:20].strip()
                elif label == "DAZI":
                    block["dazi"] = float(line[2:8])
                elif label == "ZEN1 / ZEN2 / DZEN":
                    z1, z2, dz = (float(x) for x in line[2:20].split())
                    block.update(zen1=z1, zen2=z2, dzen=dz)
                elif label == "START OF FREQUENCY":
                    current = line[3:6]
                    block["freqs"][current] = {"pco": None, "noazi": None, "grid": {}}
                elif label == "NORTH / EAST / UP":
                    block["freqs"][current]["pco"] = tuple(
                        float(x) for x in line[0:30].split())
                elif label == "END OF FREQUENCY":
                    current = None
                continue
            if current is None:
                continue
            head = line[0:8].strip()
            values = [float(x) for x in line[8:].split()]
            if head == "NOAZI":
                block["freqs"][current]["noazi"] = values
            else:
                block["freqs"][current]["grid"][float(head)] = values
    if not block["freqs"]:
        raise ValueError("no frequency block found in %s" % path)
    return block


def los_unit(az_deg, el_deg):
    """Unit vector to the satellite in local (North, East, Up).

    Azimuth is measured clockwise from geodetic north, elevation above the
    horizon, both in degrees.
    """
    a = math.radians(az_deg)
    e = math.radians(el_deg)
    return (math.cos(e) * math.cos(a), math.cos(e) * math.sin(a), math.sin(e))


def pcv_at(block, code, az_deg, zen_deg):
    """Phase-centre variation, bilinear on the azimuth by zenith-angle grid."""
    freq = block["freqs"][code]
    grid = freq["grid"]
    azimuths = sorted(grid)
    dz = block["dzen"]
    da = block["dazi"]
    n_zen = len(grid[azimuths[0]])

    j = int((zen_deg - block["zen1"]) / dz)
    j = max(0, min(j, n_zen - 2))
    fz = (zen_deg - (block["zen1"] + j * dz)) / dz

    i = int((az_deg - azimuths[0]) / da)
    i = max(0, min(i, len(azimuths) - 2))
    fa = (az_deg - azimuths[i]) / da

    v00 = grid[azimuths[i]][j]
    v01 = grid[azimuths[i]][j + 1]
    v10 = grid[azimuths[i + 1]][j]
    v11 = grid[azimuths[i + 1]][j + 1]
    return ((1.0 - fa) * (1.0 - fz) * v00 + (1.0 - fa) * fz * v01
            + fa * (1.0 - fz) * v10 + fa * fz * v11)


def pco_projection(block, code, az_deg, el_deg):
    """The PCO vector projected onto the line of sight, in millimetres."""
    north, east, up = block["freqs"][code]["pco"]
    en, ee, eu = los_unit(az_deg, el_deg)
    return north * en + east * ee + up * eu


def correction(block, code, az_deg, el_deg):
    """Total receiver-antenna phase-centre correction, in millimetres."""
    zen = 90.0 - el_deg
    return pco_projection(block, code, az_deg, el_deg) + pcv_at(block, code, az_deg, zen)
