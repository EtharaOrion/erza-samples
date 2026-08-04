# Headers, environments, and answer hygiene

The unglamorous half of an astrometry job. None of it is hard; all of it has quietly
invalidated somebody's otherwise-correct solution.

## Parsing FITS-style ASCII cards

A card is `KEYWORD = VALUE / comment`, in principle fixed-format, in practice worth
parsing defensively.

- **Split on the first `=` only.** Comments contain equals signs.
- **Quoted values first, comment stripping second.** String-valued keywords —
  `CTYPEn`, `CUNITn`, `RADESYS`, `OBJECT` — are single-quoted. If you strip everything
  after the first `/` before you notice the quotes, a value like `'RA---TAN'` survives
  but a path- or date-like string does not, and you will not find out until something
  downstream is empty. Detect the leading quote, take the quoted span, discard the rest
  of the line.
- **Float only the unquoted remainder**, after removing the trailing comment. Values may
  be written in Fortran-ish exponent form; plain `float()` handles `1.2E-05` but not
  `1.2D-05`, so normalise if you see the latter.
- **Keywords contain hyphens and digits** — `MJD-OBS`, `CD1_1`, `PV2_1`. Do not
  restrict to identifier characters.
- **Skip blank lines and the `END` card**, and tolerate `COMMENT` / `HISTORY` cards,
  which have no `=` at all.

A dict of `{keyword: value}` is enough; you do not need a card object model. But do
inspect what you parsed before using it — printing the parsed dict once catches a
mangled `CTYPE` faster than debugging a 12° astrometric error.

## Reading the source catalogue

Plain CSV with a header row. Use `csv.DictReader` or split by hand; either way keep the
ids as **strings exactly as they appear in the file**. Source ids are usually a letter
prefix plus a zero-padded number; do not parse one to an integer and reformat it, and do
not sort as integers and re-pad — round-tripping through `int` is how zero padding gets
lost, and a de-padded id is a different key to whoever reads your output.

Pixel coordinates in a source catalogue are floats, not integers. Do not round them to
whole pixels; sub-pixel centroids are the entire point of source extraction, and at
typical plate scales one pixel is many times an arcsecond-level tolerance.

## Working without astropy

If the environment ships only numpy (or only the standard library), implement the
projection directly — the whole chain is a dozen lines of trigonometry and needs nothing
beyond `math`. Do not spend turns on `pip install astropy`, on vendoring wcslib, or on
searching the filesystem for a WCS package. In a no-network container those attempts
fail slowly and buy nothing.

numpy is convenient for the CD step but not required; if you do use it, remember the
matrix orientation trap (`cd @ offset`, not `offset @ cd`). A `math`-only implementation
sidesteps that trap entirely, at the cost of writing the two dot products out.

## Do not touch the inputs

The delivered header and catalogue are the reference copy that anyone reproducing your
astrometry will read. Treat them as read-only:

- Do not edit, reformat, normalise, move or rewrite the header or the catalogue.
- Do not replace them with symlinks, and do not symlink your answer file either.
- Copy them elsewhere if you want to experiment.

"Fixing" an input never fixes a convention error, and it destroys the one thing that
makes your result checkable.

## Answer hygiene

- Write to **exactly** the path requested, with **exactly** the top-level structure
  requested — a missing wrapper key fails every case at once.
- Include **every** id, spelled character-for-character as the catalogue spells it —
  zero padding included, and never re-derived from a loop counter.
- Emit plain JSON numbers at full double precision. `json.dump` on a Python float is
  fine; `round(v, 3)` is not — at arcsecond-scale tolerances a three-decimal round can
  consume the entire error budget on its own, turning a correct calculation into a
  failure. If you must format, use six decimals or more.
- Booleans are not numbers, `NaN` and `Infinity` are not valid JSON numbers, and a
  `NaN` here usually traces back to an unclamped `asin` argument. Assert finiteness
  before you write.
- Angles in degrees, RA already wrapped into [0, 360) by modulo, Dec in [-90, 90]. A
  Dec outside that range is generally rejected before the geometry is even compared, so
  an out-of-range value hides whatever the real error was.
