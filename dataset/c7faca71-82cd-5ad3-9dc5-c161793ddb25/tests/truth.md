# truth.md — grader-side dossier for flight-duty-period-legality

Not the pipeline truth document. `verifier/process/TRUTH.md` is the answer-free
golden trajectory and is the file the judge reads. **This** file restates the
goldens and exists so a 0.0 can be attributed to a named route rather than
merely recorded.

## Delta-lever

Whether a published crew pairing is inside its legal ceilings turns on a cell of
the maximum-flight-duty-period matrix indexed by acclimated report time and
number of flight segments — ten irregular clock bands by seven segment columns
of arbitrary half-hour values with no generating relation — replaced by a second
matrix with different bands once the crew is augmented; and the answer wanted is
the tightest of seven simultaneous limits, so the default, which reaches for a
single flat duty-day figure and stops at the headline limit, misses every graded
figure.

Gap type: (b) a published constant set the default cannot reconstruct, applied
through (e) an enumeration the default truncates.
Failure family: F8 (enumeration discipline).

## Golden values

51 graded cases over 17 pairings (17 is prime; see the tolerance section for why
that matters less here than it does for a ratio task, and what stands in for it).

| pairing | fdp_margin_min | binding_limit | binding_margin_min |
|---|---|---|---|
| P01 | 23 | `flight_duty_period` | 23 |
| P02 | -18 | `flight_duty_period` | -18 |
| P03 | 7 | `flight_duty_period` | 7 |
| P04 | -12 | `flight_duty_period` | -12 |
| P05 | 34 | `flight_duty_period` | 34 |
| P06 | -22 | `flight_duty_period` | -22 |
| P07 | -41 | `flight_duty_period` | -41 |
| P08 | -27 | `flight_duty_period` | -27 |
| P09 | 9 | `flight_duty_period` | 9 |
| P10 | -26 | `flight_duty_period` | -26 |
| P11 | 11 | `flight_time` | -24 |
| P12 | 14 | `rest_before_duty` | -19 |
| P13 | 21 | `cumulative_flight_672h` | 11 |
| P14 | 38 | `cumulative_fdp_168h` | 18 |
| P15 | 14 | `cumulative_fdp_672h` | -6 |
| P16 | -25 | `free_period_168h` | -43 |
| P17 | 9 | `flight_time` | -14 |

Six of the seventeen pairings comply with every limit; eleven do not. All seven
limit names occur, so no run can score the name channel without enumerating.

## Derivation

For one pairing:

1. Report and release are read as minutes of the day on the crew's acclimated
   local clock; a release earlier on the clock than its report is the next day.
2. A scheduled rest opportunity is excluded from the duty period only when every
   condition of the split-duty section holds at once: unaugmented operation, a
   suitable accommodation, the whole rest inside 22:00–05:00 local, at least
   3 hours in the accommodation, scheduled in advance, not before the first
   segment is complete, and duty plus rest not more than 14 hours. Otherwise the
   whole elapsed period is duty.
3. The maximum duty period is the matrix cell the report time and the segment
   count select for an unaugmented pairing, or the cell the report time, rest
   facility class and pilot count select for an augmented one, less 30 minutes
   when the crew is not acclimated.
4. The maximum flight time is the report-time band of the flight-time table for
   the minimum required crew, or the fixed three- or four-pilot ceiling.
5. Seven signed margins in minutes follow: duty period, flight time, rest
   immediately before, longest duty-free period in the previous week, and the
   three rolling cumulative ceilings, each of which includes this pairing's own
   contribution.
6. `binding_limit` is the smallest of the seven, ties resolved in the published
   order; `binding_margin_min` is that margin; the pairing complies exactly when
   it is not negative.

## Independent recompute

The golden set is anchored by a **second formulation**, not by the oracle's own
pipeline, and it runs on every graded run rather than only at build time.

* `oracle/part117_tables.py` carries a hand transcription of the three tables and
  of the limits stated in the section prose, and answers a query by scanning an
  ordered list of clock ranges and subtracting the scheduled duty from the cell.
* `verifier/reg_reparse.py` shares none of that. It parses the three tables out
  of the `<GPOTABLE>` elements of the published regulation XML shipped at
  `verifier/part117.xml`, re-reads every non-tabular limit out of the published
  section prose with its own regular expressions, selects a row through a
  1440-entry minute-indexed array rather than an ordered scan, and expresses
  every duty-time margin as a release deadline in absolute clock minutes rather
  than as a maximum minus a duration.

Agreement: **exact, 0 minutes of disagreement**, over 23,040 table-cell queries,
15 section limits and all 119 pairing margins. `build/gen.py` refuses to build if
the two routes differ anywhere, and
`verifier/test_outputs.py::test_frozen_reference_matches_independent_recompute`
re-asserts the goldens through the XML route on every graded run.
`test_published_tables_are_intact` is a standing tripwire on the source itself:
the duty-period matrix must carry ten rows and seven segment columns, the
published clock bands in the published order, a tiling of the day with no gap or
overlap, values that are positive half hours, and section limits equal to the
values quoted from the published text. An absent or unreadable XML source is a
hard failure, never a skip.

## Plausibility envelope

Declared bound, asserted by `test_plausibility_envelope`:
`-720 <= margin <= 720` minutes for every graded margin, and no margin exactly
zero. The expected range follows from the regulation itself — the largest
published duty ceiling is 19:00 and the smallest is 9:00, so a margin whose size
exceeds twelve hours means a unit slip or a dropped day-wrap, the two ways a
reference of this shape goes wrong. The goldens run from -43 to +38 minutes,
comfortably inside it.

The roster carries its own envelope: 4:00–20:00 from report to release, flight
time strictly inside the duty period, 8:00–30:00 of rest immediately before,
one to nine segments, two to four pilots. All seventeen pairings sit inside it.

## Tolerance rationale

`tolerance_fdp_margin_min_abs = 1.0` minute and
`tolerance_binding_margin_min_abs = 1.0` minute. Name cases are exact string
matches and carry no tolerance.

*Lower bound.* `published_precision_ambiguity_margin_maxabs = 0.0`. Measured, not
asserted: every graded margin was recomputed through the second formulation and
differenced against the oracle's, worst disagreement 0 minutes over 119 margins.
There is no rounding freedom to find — every published cell is a whole or half
hour, every clock time in the roster is a whole minute, and every non-tabular
limit is an integral number of hours. The one minute allowed exists only so that
an integer computation performed in a different order cannot fail.

*Upper bound.* The smallest non-zero separation any recorded competing method
achieves on any graded margin is 10 tolerances, and the nearest real competitor
reproduces none of the 51 graded cases.

*On the prime count.* 17 pairings is prime, which is the convention this set uses
so that no golden lands on a round value through a denominator. It does less work
here than it does for a ratio, because these goldens are differences of clock
minutes rather than shares. What actually carries the guess resistance is
measured instead: no graded margin sits within tolerance of zero or of any
multiple of 30 minutes between -180 and +180, none coincides with a published
table cell, and none coincides with the elapsed duty period, the scheduled flight
time or the rest before duty of its own pairing —
`test_guess_resistance_and_decoy_freedom` re-measures all of that on every run.

## Wrong paths

Every entry is measured, in tolerance units, over the pairings it actually
alters. `graded_cases_reproduced` is out of `graded_cases_scored`.

| path | widest gap | smallest non-zero gap | reproduces |
|---|---|---|---|
| `flat_14h_duty_day` | 330× | 11× | 0 / 51 |
| `augmentation_ignored` | 360× | 37× | 0 / 21 |
| `report_row_ignored` | 240× | 11× | 20 / 51 |
| `segment_column_ignored` | 90× | 11× | 9 / 30 |
| `split_duty_relief_skipped` | 205× | 205× | 1 / 3 |
| `split_duty_relief_unconditional` | 190× | 29× | 0 / 9 |
| `unforeseen_extension_applied` | 120× | 11× | 14 / 51 |
| `unacclimated_reduction_skipped` | 30× | 30× | 4 / 9 |
| `cumulative_limits_ignored` | 20× | 10× | 45 / 51 |
| `flight_duty_period_only` | 35× | 10× | 37 / 51 |

`flat_14h_duty_day` is the nearest real competitor: the route a scheduler who
knows the limits exist but not the matrix actually takes. It is the only path
required to reproduce nothing, and it reproduces nothing — verified live by
`test_nearest_competitor_reproduces_no_graded_case`, not merely read from the
ledger.

Two paths reproduce most of the graded set and are recorded rather than hidden.
`cumulative_limits_ignored` and `flight_duty_period_only` both use the **correct**
matrix and fail only on the enumeration, so they isolate that channel; neither is
producible by a run that does not hold the matrix. `segment_column_ignored`
reproduces 9 of 30 because the published matrix's first two columns are equal
throughout and columns three and four repeat them in several bands, so on those
bands reading the matrix on one axis is not an error at all. That is a property
of the published table, and it is disclosed rather than engineered away.

The worst constant answer is `always flight_duty_period` on the name channel, at
10 of 17 names, i.e. 10 of 51 graded cases. That is the honest floor of this
instance and is recorded in `expected_values.json:constant_answer_floors`; it is
a consequence of the design choice that makes the nearest competitor reproduce
nothing, and the trade is argued in `build/build_report.json`.

## Citations and sources

* US Government Publishing Office, GovInfo, Code of Federal Regulations, annual
  edition, title 14 volume 3, part 117 (2023 edition).
  `https://www.govinfo.gov/content/pkg/CFR-2023-title14-vol3/xml/CFR-2023-title14-vol3-part117.xml`
  sha256 `c1e0020d662507e14388d3030b85cf15b492587bf7ad99f8b1db4a40d7136537`,
  44,616 bytes, HTTP 200. Shipped verbatim at `verifier/part117.xml`; every
  constant this task grades is parsed out of those bytes.
* Rights: GovInfo, About the Code of Federal Regulations / GPO policy —
  "Copyright protection under this title is not available for any work of the
  United States Government" and "public documents can generally be reprinted
  without legal restriction". Cited to GovInfo, which is the publisher of the
  bytes used, rather than to the agency site.

The roster is synthetic. No carrier, airport, aircraft or crew member is named or
implied, and none of the 51 graded figures is a published statistic of anything.
