# TRUTH.md — ionosphere arc vertical-content calibration (golden trajectory)

The ordered moves a competent run makes, from opening the task to writing the
answer. Each step says **what to do and why**; **no step states what it evaluates
to**. Derived from `oracle/solve.sh` (the reference solution) with every value
stripped out — it describes the *method*, never a bias, a content figure, or an
arc's reference value.

**How to read this file.** It is method, not arithmetic. A reader who follows
every step faithfully lands on the oracle's answer; a reader who has the rules
can still get the wrong number by resolving an observable pair carelessly, which
is the point.

## What is being asked

Twelve tracking arcs, each one receiver watching one satellite for 121 epochs at
one-minute spacing. For each arc, the arithmetic mean over its epochs of the
vertical total electron content, in TECU. One graded quantity, twelve instances,
one uniform absolute tolerance.

## Step 0 — read the record

`/root/data/receivers.csv` gives, per receiver, the ordered pair of RINEX 3
observation codes it tracked on the two frequencies. That pair is not the same at
every receiver and it is the join key for everything downstream.
`/root/data/observations.csv` gives one row per receiver, satellite and epoch,
with the two code pseudoranges in metres and the satellite elevation angle in
degrees. `/root/data/question.json` lists the arcs to report and carries an
orientation figure. Twelve arcs of 121 epochs cannot be reduced by hand inside
the budget, so a solver is written and run.

## Step 1 — form the geometry-free code observable

Subtract the second-frequency range from the first at each epoch. Geometry,
clocks and the troposphere cancel; what survives is the differential ionospheric
delay plus the differential hardware delay. The task statement gives this
expression and its conversion constants outright, so nothing is withheld here.

## Step 2 — identify the observable pair actually reported

The hardware delay depends on the *signal*, not merely on the frequency. A
receiver tracking the civil code on the first frequency carries a different delay
from one tracking the encrypted code on that same frequency, and a receiver
tracking the modernised civil signal on the second frequency differs again. The
pair to look up is the pair that receiver reports, per `receivers.csv`.

## Step 3 — resolve the differential entry on each side  *(crux)*

The mounted reference supplies, per label, the published rows of a daily
differential signal bias product. A row is an **ordered pair** of observables and
its value is the first observable's bias minus the second's. Resolution follows a
precedence, and that order is the crux:

1. a row for exactly the wanted ordered pair — use it as published;
2. a row for the reversed pair — use it negated;
3. neither present — assemble the value as the signed sum along the shortest
   chain of published rows linking the two observables, each step contributing
   plus its value when traversed in the printed order and minus when traversed
   against it, tie-broken through the constellation's reference observables.

Rule 1 is not cosmetic. The rows of a real product are independent estimates from
one adjustment, not algebraically consistent identities: a chain assembled
through other rows and the directly published row for the same pair disagree by a
few tenths of a nanosecond, which is several TECU of content. So a run that
always chains gets the arcs whose pair is published wrong, and a run that never
chains cannot resolve the arcs whose pair is not published at all. Both branches
are exercised by this instance, and which branch applies can differ between the
satellite side and the station side of the same arc.

## Step 4 — sum the two sides  *(crux)*

The satellite entry and the station entry are separate rows and they add.
Neither alone is the total. This is the commonest real-world error in this
family, because a single-station user routinely holds satellite values and no
station values.

## Step 5 — remove, do not add  *(crux)*

The published definition of a bias is `observation minus true observation`, so
the true observable is `observation minus bias`. The total is **subtracted** from
the geometry-free observable, converted from its nanosecond scale to a range by
the speed of light. Reading "bias correction" as something to add inverts the
sign and doubles the resulting error.

## Step 6 — convert to slant content

Apply the frequency-dependent conversion the task statement pins. Nothing is
withheld here either; a run that gets this wrong has misread the prompt, not the
method.

## Step 7 — reduce to vertical and average

Apply the single-layer obliquity factor at each epoch's elevation angle, using
the Earth radius and shell height the task statement pins, then take the plain
arithmetic mean of the per-epoch vertical values over the arc. Averaging
trapezoidally instead is a defensible reduction convention and has been measured
to stay inside tolerance; it must not be treated as an error.

A sound run sanity-checks the outcome here: vertical content is positive and of
order tens of TECU, and one nanosecond of uncorrected delay is worth several
TECU, so a sign or side error is visible as an implausible magnitude rather than
as scatter.

## Step 8 — write the artifact

`/root/results.json`, one object under the contracted key, receiver then
satellite, values numeric and finite.

## Where runs break

The failure catalogue — each entry a route recomputed live and found decisively
outside tolerance — is in `../rubric.yaml` under `failure_modes`, with its
distance in tolerance units in `../expected_values.json` under `control_gaps`.
In outline:

- no instrumental term removed at all, which is the producible route for a run
  without the mounted reference;
- the orientation figure echoed unchanged;
- one side applied and the other forgotten;
- the total added rather than removed;
- every pair chained even where the direct row exists;
- a chain summed by magnitude instead of by each row's own sign;
- a non-reference signal treated as though it were the reference observable of
  its frequency.

## What cannot be done

The biases are not recoverable from the supplied record. Only the sum of the two
sides is observable on a link, each arc carries its own free content level, and
no station coordinates or azimuths are given, so no spatial model can tie the
arcs together. A run that claims to have solved for the biases from the
observations alone has not; it has fitted the arc's own content level and called
it a bias. Judge such a claim on its arithmetic, not on its confidence.
