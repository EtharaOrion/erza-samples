Task:
For each detected source, determine the **ICRS sky coordinates** (Right
Ascension and Declination) that its image position corresponds to under the
field's world-coordinate system.

Input (`/root/data/`):

1. `image.hdr` — the FITS-style ASCII header of the image, one
   `KEY = VALUE / comment` card per line. It describes a gnomonic tangent-plane
   image and carries, among the usual image keywords: `CTYPE1` and `CTYPE2`,
   `CRPIX1` and `CRPIX2`, `CRVAL1` and `CRVAL2`, the linear transformation
   matrix `CD1_1`, `CD1_2`, `CD2_1`, `CD2_2`, `EQUINOX` and `RADESYS`.

2. `sources.csv` — the catalogue of 16 detected sources, with a header row and
   the columns `source_id,x,y`. `x` and `y` give a source's measured image
   position as 1-based FITS pixel coordinates; `CRPIX1` and `CRPIX2` are 1-based
   FITS pixel coordinates as well. Source ids are `S01` … `S16`.

The image's world-coordinate system is the standard FITS WCS gnomonic (TAN)
projection as defined by Greisen & Calabretta (2002), "Representations of
celestial coordinates in FITS" (Paper II). For every source, apply that
definition:

- the intermediate world coordinates follow from the CD matrix applied to the
  source's offset from the reference pixel `CRPIX1`, `CRPIX2`;
- the inverse TAN projection takes those intermediate world coordinates to
  native spherical coordinates;
- the native spherical coordinates are rotated onto celestial coordinates about
  the reference point (`CRVAL1`, `CRVAL2`).

Report both coordinates in degrees in the ICRS frame, with RA in the range
[0, 360).

Output:
Write `/root/results.json` with exactly:

```json
{"sources": {"S01": {"ra_deg": 123.456789, "dec_deg": 65.432109},
             "S02": {"ra_deg": ..., "dec_deg": ...},
             ...,
             "S16": {"ra_deg": ..., "dec_deg": ...}}}
```

- `sources` — for every source id `S01`…`S16`, an object with the two numeric
  fields `ra_deg` and `dec_deg`, the source's ICRS coordinates in degrees.

Scoring: one test case per source; a source passes iff the angular separation on
the sky between the reported position and the reference position is at most
0.0005 deg. Score = sources passed / 16.

The container has Python 3 with numpy installed; astropy is not installed. No
network access.
