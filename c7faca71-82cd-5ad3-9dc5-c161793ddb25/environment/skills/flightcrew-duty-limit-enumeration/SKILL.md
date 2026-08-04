---
name: flightcrew-duty-limit-enumeration
description: >-
  Decide whether a scheduled crew assignment sits inside every limit a duty-time
  regulation imposes on it, and which of those limits governs it, by taking the
  assignment's margin against each limit separately and reporting the smallest.
  Carries the published maximum-flight-time, unaugmented and augmented
  maximum-duty-period matrices for US air carrier flightcrew members, together
  with the acclimation reduction, the split-duty relief conditions, the
  cumulative ceilings and the minimum rest provisions. Use when an assignment
  has to be tested against a published duty-time regime and the answer wanted is
  compliance or the governing constraint. Do NOT use when the maximum duty
  period is supplied with the assignment rather than to be looked up, when the
  operation is outside the regime the matrices govern - cargo-only supplemental
  operations, on-demand and commuter operations, and operations flown under a
  fatigue risk management system approved in place of the numeric limits - when
  the record is an as-flown report rather than a schedule, because relief
  provisions for unforeseen circumstances then enter and the scheduled maxima
  stop being the operative ceiling, or when the question is how to build a
  compliant schedule rather than how to test one.
---

# Testing a scheduled assignment against a published duty-time regime

Source for every constant below: US Government Publishing Office, GovInfo,
annual edition of the Code of Federal Regulations, title 14, part 117 (2023
edition), <https://www.govinfo.gov/content/pkg/CFR-2023-title14-vol3/xml/CFR-2023-title14-vol3-part117.xml>.
Section numbers in brackets are that part's own.

## Why this needs a procedure rather than a lookup

A duty-time regime is not one number. It is a family of ceilings and floors that
apply at the same time to the same assignment, drawn from different paragraphs,
measured in different quantities and over different windows: one on the duty
period, one on flight time, two or three on rolling totals, one on the rest that
precedes the assignment and one on time free from duty in the recent past. An
assignment is lawful only if it is inside **all** of them, and the interesting
answer - the one that tells a scheduler what to change - is **which** of them is
closest to biting.

The failure this procedure exists to prevent is stopping at the first ceiling.
The headline duty-period matrix is the one everybody knows, so an analysis that
checks it and nothing else is confidently wrong on exactly the assignments that
matter: the long ones near a rolling ceiling, and the short ones behind a rest
period that was cut.

## The procedure

1. **Fix the regime and the scope.** Establish which operating rule the carrier
   flies under and therefore which limit set applies, and whether the record in
   hand is a *schedule* or an *as-flown report*. This matters more than it
   looks: relief for unforeseen circumstances applies to what happened, never to
   what was planned, so a scheduled assignment may not borrow it.

2. **Convert everything to one unit before comparing anything.** Whole minutes.
   Clock times, published cells, rolling totals and rest periods all become
   minutes, and a release time earlier on the clock than its report time is the
   next day.

3. **Compute the duty period itself, net of any relief.** The duty period runs
   from report to release. Where the regime allows a rest opportunity inside the
   period to be excluded from it, that exclusion is conditional: check every
   condition, and if any one fails, the whole elapsed period counts.

4. **Read the maximum duty period out of the matrix its own index selects.** The
   index is not one-dimensional. Which matrix depends on how the crew is
   composed and what rest facility is fitted; which row depends on the report
   time; which column depends on the number of segments, or on the crew size and
   facility class. Then apply any adjustment that sits outside the matrix - the
   acclimation reduction is the usual one, and it is in a different paragraph.

5. **Take a margin against every limit, not a verdict.** For each limit compute
   `limit - scheduled quantity` in minutes, signed. Keep the sign: a negative
   margin is an exceedance and its size is the amount of the exceedance.

6. **Report the smallest margin and name the limit it belongs to.** That is the
   governing limit. The assignment is compliant exactly when the smallest margin
   is not negative, so one enumeration answers both questions.

7. **Sanity-check the enumeration itself.** Every limit in the regime got a
   margin; no limit was applied twice; the units are minutes throughout; and the
   quantity compared against each ceiling is the one that ceiling is expressed
   in - duty hours against a duty ceiling, flight hours against a flight ceiling.

## The published limit set

### Maximum flight time, unaugmented operations [Table A, and 117.11(a)]

Indexed by report time in the acclimated theater's local clock.

| report time | maximum flight time |
|---|---|
| 00:00–04:59 | 8:00 |
| 05:00–19:59 | 9:00 |
| 20:00–23:59 | 8:00 |

With three pilots the flight-time ceiling is 13:00 and with four it is 17:00
[117.11(a)(2)–(3)]; the table above is for the minimum required crew.

### Maximum flight duty period, unaugmented [Table B, and 117.13]

Rows are the scheduled report time in the acclimated theater's local clock;
columns are the number of flight segments, the last covering seven or more.

| report time | 1 | 2 | 3 | 4 | 5 | 6 | 7+ |
|---|---|---|---|---|---|---|---|
| 00:00–03:59 | 9:00 | 9:00 | 9:00 | 9:00 | 9:00 | 9:00 | 9:00 |
| 04:00–04:59 | 10:00 | 10:00 | 10:00 | 10:00 | 9:00 | 9:00 | 9:00 |
| 05:00–05:59 | 12:00 | 12:00 | 12:00 | 12:00 | 11:30 | 11:00 | 10:30 |
| 06:00–06:59 | 13:00 | 13:00 | 12:00 | 12:00 | 11:30 | 11:00 | 10:30 |
| 07:00–11:59 | 14:00 | 14:00 | 13:00 | 13:00 | 12:30 | 12:00 | 11:30 |
| 12:00–12:59 | 13:00 | 13:00 | 13:00 | 13:00 | 12:30 | 12:00 | 11:30 |
| 13:00–16:59 | 12:00 | 12:00 | 12:00 | 12:00 | 11:30 | 11:00 | 10:30 |
| 17:00–21:59 | 12:00 | 12:00 | 11:00 | 11:00 | 10:00 | 9:00 | 9:00 |
| 22:00–22:59 | 11:00 | 11:00 | 10:00 | 10:00 | 9:00 | 9:00 | 9:00 |
| 23:00–23:59 | 10:00 | 10:00 | 10:00 | 9:00 | 9:00 | 9:00 | 9:00 |

The row boundaries are irregular on purpose and the values are not generated by
any formula - they were set band by band, so neither the row nor the cell can be
interpolated or guessed from its neighbours. The first two columns are equal
throughout, which is a property of the published table and not an invitation to
merge them: there is no combined "one to two segments" column, and reading one
into the table is the most common way of getting the later columns wrong.

If the crew is **not acclimated** to the theater the report time is expressed
in, the value taken from this table is reduced by 30 minutes [117.13(b)(1)].

### Maximum flight duty period, augmented [Table C, and 117.17]

Applies when the crew carries more than the minimum required pilots and an
onboard rest facility is fitted. Rows are the report time; columns are the class
of rest facility and the number of pilots.

| report time | cl.1 / 3 | cl.1 / 4 | cl.2 / 3 | cl.2 / 4 | cl.3 / 3 | cl.3 / 4 |
|---|---|---|---|---|---|---|
| 00:00–05:59 | 15:00 | 17:00 | 14:00 | 15:30 | 13:00 | 13:30 |
| 06:00–06:59 | 16:00 | 18:30 | 15:00 | 16:30 | 14:00 | 14:30 |
| 07:00–12:59 | 17:00 | 19:00 | 16:30 | 18:00 | 15:00 | 15:30 |
| 13:00–16:59 | 16:00 | 18:30 | 15:00 | 16:30 | 14:00 | 14:30 |
| 17:00–23:59 | 15:00 | 17:00 | 14:00 | 15:30 | 13:00 | 13:30 |

The unacclimated reduction of 30 minutes applies here too [117.17(b)(1)], and no
assignment under this section may involve more than three flight segments
[117.17(d)]. Note that the row bands here are **not** the row bands of the
unaugmented table; carrying one set of boundaries across to the other table is a
silent error, because several report times sit in differently-labelled rows.

### Rest opportunity inside the duty period [117.15]

For an unaugmented operation only, time spent in a suitable accommodation during
the duty period is excluded from that duty period if **all** of the following
hold. This is a conjunction; any single failure means nothing is excluded.

- the rest opportunity falls between 22:00 and 05:00 local time;
- the time in the accommodation is at least 3:00;
- it was scheduled before the duty period began;
- the rest actually provided is not less than the rest scheduled;
- it is not provided until the first segment has been completed;
- the duty period and the rest opportunity together do not exceed 14:00.

### Cumulative ceilings [117.23] and rest provisions [117.25]

| limit | ceiling or floor | window |
|---|---|---|
| flight time [117.23(b)(1)] | 100 hours | any 672 consecutive hours |
| flight duty period [117.23(c)(1)] | 60 hours | any 168 consecutive hours |
| flight duty period [117.23(c)(2)] | 190 hours | any 672 consecutive hours |
| free from all duty [117.25(b)] | at least 30 hours | within the past 168 hours |
| rest immediately before [117.25(e)] | at least 10 hours | immediately preceding |

A rolling total includes the assignment being tested. Adding the assignment is
the step that is skipped: checking the history against the ceiling and stopping
there passes an assignment that the assignment itself pushes over.

### Relief for unforeseen circumstances [117.19]

If unforeseen operational circumstances arise before takeoff, the pilot in
command and the certificate holder may extend the maximum duty period from
either matrix by up to 2 hours, once. This is relief applied to an operation in
progress. It has no bearing on whether a *schedule* was lawful when it was
published, and adding it to a scheduled maximum is a category error, not a
conservative allowance.

## Where this goes wrong in practice

- **A single flat duty-day figure.** There is no one number. Substituting the
  14:00 combined-period figure, or the duty-day figure from a superseded rule,
  is wrong on nearly every row of the matrix and wrong in both directions.
- **Reading the matrix on one axis.** Report time alone, or segment count alone,
  reproduces the correct cell only where the row happens to be flat.
- **Applying the unaugmented matrix to an augmented assignment.** The augmented
  matrix is not the unaugmented one plus a bonus; it is a different table with
  different row bands.
- **Losing an adjustment that sits outside the matrix.** The acclimation
  reduction and the split-duty exclusion both live in prose, not in a cell.
- **Stopping at the duty period.** The cumulative and rest limits govern a real
  fraction of real assignments, and they are invisible from the pairing sheet
  alone because they need the crew member's recent history.

## Sources

- US Government Publishing Office, GovInfo, Code of Federal Regulations, annual
  edition, title 14 (Aeronautics and Space), volume 3, part 117, 2023 edition:
  <https://www.govinfo.gov/content/pkg/CFR-2023-title14-vol3/xml/CFR-2023-title14-vol3-part117.xml>
  Every table and every numeric limit above is transcribed from that document;
  the bracketed section numbers are its own.
- The tables carry the designations the part gives them: Table A (maximum flight
  time, unaugmented), Table B (flight duty period, unaugmented) and Table C
  (flight duty period, augmented).
- The regime is amended from time to time. Check the edition date of whatever
  copy you are working from before relying on a cell; a table read out of a
  superseded edition is the quiet way to be wrong.
