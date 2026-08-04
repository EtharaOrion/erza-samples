# TRUTH.md — the golden trajectory, answer-free

Every step a competent run takes, in order, derived from the reference solution.
No step states what it evaluates to. This file is safe to hand to the judge.

## Step 0 — Open what was baked

Read `/root/data/pairings.csv` and `/root/data/question.json`. The contract, the
column notes, the operating rule the block is flown under and the vocabulary of
limit names all live in the second file; do not infer the contract from the
prompt alone. Author a script. Seventeen pairings against seven limits each is
one hundred and nineteen comparisons, and hand assembly is neither checkable nor
reproducible.

## Step 1 — Put everything on one clock

Convert every clock time and every duration to whole minutes. Two conversions
carry the traps:

* a release time earlier on the clock than its report time is the next day, so
  the elapsed period is the difference taken modulo a full day;
* the history columns are durations, not clock times, and can exceed a day.

Nothing downstream should ever compare a string.

## Step 2 — Decide which regime each pairing is in

Split the roster on whether the crew is more than the minimum required pilots
with an onboard rest facility fitted. The two regimes are governed by different
matrices, and the matrices do not share report-time bands. A pairing routed to
the wrong matrix is wrong even when the arithmetic around it is right.

## Step 3 — Settle the duty period, net of any relief

The duty period runs from report to release. Where a rest opportunity is
scheduled inside it, the published relief is conditional and the conditions are a
conjunction: the operation must be unaugmented, the accommodation must be
suitable, the whole rest must fall inside the published night-time window, it
must last at least the published minimum, it must be scheduled in advance and not
be provided before the first segment is complete, and duty plus rest together
must not exceed the published combined ceiling. If any one condition fails,
nothing is excluded and the whole elapsed period is duty.

Take care with the window: it runs across midnight, so membership cannot be
decided by comparing endpoints.

## Step 4 — Read the maximum duty period out of the matrix

Select the row by the report time's own published band and the column by the
segment count, or — in the augmented regime — by the rest facility class and the
pilot count. The bands are irregular and the values do not follow a relation, so
neither the row nor the cell can be interpolated from its neighbours. Then apply
the adjustment that sits outside the matrix: the reduction that applies when the
crew is not acclimated to the theater the report time is expressed in.

## Step 5 — Read the maximum flight time

For the minimum required crew this is a report-time band of its own table, with
its own boundaries, which are not the boundaries of the duty-period matrix. For a
crew of three or four pilots it is a fixed ceiling stated in the section prose
rather than in any table.

## Step 6 — Take a signed margin against every limit

For each limit form `ceiling - scheduled quantity`, or `scheduled quantity -
floor` for a floor, in minutes, and keep the sign. Seven margins per pairing:
the duty period, the flight time, the rest immediately before report, the longest
duty-free period in the previous week, and the three rolling cumulative ceilings.

The rolling ceilings are the ones that are skipped. Each is a total over a window
ending at report, and the pairing being tested contributes to it: the history
column alone is not the quantity to compare.

## Step 7 — Take the smallest margin

The governing limit is the one with the smallest margin, ties resolved in the
order the contract lists the names. The pairing is inside every limit exactly
when that margin is not negative, so one enumeration answers both questions.
Report the duty-period margin, the governing name and the governing margin.

## Step 8 — Check something that could have disagreed

At least one of: re-read a matrix cell for one pairing and confirm the same value
by a second path; confirm that the pairings routed to the augmented matrix are
exactly those with more than the minimum crew; confirm that each margin's sign
agrees with a direct comparison of the two quantities it came from; confirm that
excluding a rest opportunity never produced a duty period longer than the elapsed
period. A clean script run is not verification — every wrong route on this task
produces a well-formed signed number in a plausible range.

## The crux

Two surfaces, and a run has to clear both.

The first is the matrix read on **both** axes, in the **right** regime. The
published values are arbitrary half hours over irregular bands with no generating
relation, so a run either holds them or does not; there is nothing in the roster
to recover them from, because no pairing carries a verdict and therefore no
pairing pins a cell from either side.

The second is the **enumeration**. The answer wanted is the tightest of seven
simultaneous limits, and on a real fraction of the roster the tightest one is not
the duty period. A run that reads the matrix perfectly and stops there is wrong
on those pairings, and nothing about its output looks wrong.

## Where runs break

* A single flat duty-day figure substituted for the matrix. The most common
  route, and the one a run without the tables produces.
* The matrix read on one axis — report time alone, or segment count alone.
* The unaugmented matrix applied to an augmented pairing, or one matrix's band
  boundaries carried across to the other.
* The acclimation reduction lost, because it lives in prose rather than in a cell.
* The relief for unforeseen circumstances added to a scheduled ceiling. This is
  the most defensible-looking error available here: the relief is real and
  published, but it applies to circumstances arising after a schedule is set, so
  it cannot enlarge a scheduled maximum.
* A scheduled accommodation rest excluded from duty without testing the published
  conditions, or a qualifying one counted as duty.
* The rolling ceilings compared against the history alone, without adding the
  pairing under test.
* The enumeration truncated at the duty period.

## What cannot be done

The environment declares no network. The limit tables are a public document, and
a run is expected to work from what it already knows plus the baked roster rather
than to fetch them; citing the source in prose is not a fetch. `/verifier`,
`/oracle` and `build/` are not readable work surfaces, and a run that probes them
is voided regardless of what it scores.

## Properties, not values

Bounds a correct answer satisfies, stated as properties so this file stays
answer-free:

* every margin is a signed whole number of minutes whose size is well under half
  a day, because the largest published duty ceiling is under twenty hours and the
  smallest is nine;
* no margin is exactly zero on this roster, so every governing limit is strictly
  the smallest and the compliance verdict is never on a knife edge;
* the governing margin is never larger than the duty-period margin, since it is a
  minimum over a set that contains it;
* the flight time of every pairing is strictly inside its duty period;
* every governing name is one of the seven the contract lists, and across the
  roster all seven occur;
* a pairing routed to the augmented matrix never has more segments than that
  section permits.

## Sources

US Government Publishing Office, GovInfo, Code of Federal Regulations, annual
edition, title 14 volume 3, part 117 (2023 edition):
`https://www.govinfo.gov/content/pkg/CFR-2023-title14-vol3/xml/CFR-2023-title14-vol3-part117.xml`

## Delta-lever

The maximum-flight-duty-period matrix — irregular clock bands by segment count,
arbitrary half-hour values, no generating relation, replaced by a second matrix
with different bands under augmentation — together with the discipline of taking
a margin against every limit the part imposes and reporting the tightest.
