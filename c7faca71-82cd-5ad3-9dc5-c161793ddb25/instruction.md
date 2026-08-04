Task:
The crew planning group of a US air carrier is auditing a block of published
pairings before the bid closes. For every pairing, report how much room it has
against the ceiling on its duty period, which of the ceilings and floors that
apply to it is closest to biting, and by how much.

Input (`/root/data/`):

1. `pairings.csv` - one row per pairing, with a header. Report and release times
   are clock times on the crew's acclimated local clock; a release time earlier
   on the clock than its report time means the pairing ends on the following
   day. Every duration is written `h:mm` and may run past twenty-four hours.

2. `question.json` - what operation the block is flown under, a note on each
   column of the roster, the set of ceiling and floor names to answer with
   (`limit_codes`), and the output contract.

Every row is a pairing as scheduled. None of them is a record of a flight that
has already been flown, and no unforeseen operational circumstance has arisen on
any of them.

Definitions, so the three reported figures are unambiguous:

- The *margin* of a ceiling is that ceiling minus the scheduled quantity it
  applies to, in whole minutes. The margin of a floor is the scheduled quantity
  minus that floor, in whole minutes. Either way a negative margin means the
  pairing is outside the limit by that many minutes.
- The *binding* limit is the one with the smallest margin. Where two would tie,
  take whichever appears first in `limit_codes`.
- A pairing is inside every limit exactly when the binding margin is not
  negative, so the sign of that one figure is the compliance verdict.

Output:
Write `/root/results.json` with exactly one entry per pairing:

```json
{"P00": {"fdp_margin_min": -9999,
         "binding_limit": "name_of_a_limit",
         "binding_margin_min": -9999}}
```

- `fdp_margin_min` - the margin against the ceiling on the flight duty period,
  in signed whole minutes.
- `binding_limit` - the name, taken from `limit_codes`, of the binding limit.
- `binding_margin_min` - the binding margin, in signed whole minutes.

(The key, the names and the numbers above are placeholders that show the JSON
shape only; they are not the answer, `P00` is not a pairing in the roster and
`name_of_a_limit` is not one of the names to answer with.)

Scoring: one test case per reported figure, 51 in total. A margin case passes
when the reported value is within 1 minute of the reference; a name case passes
when it matches the reference exactly. Score = cases passed / 51.

The container has Python 3. No network access.
