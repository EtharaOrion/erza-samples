Task:
A vital-statistics office computes death rates. The numerators come from death
certificates, which record one of four legacy categories. The denominators come
from a census that let people name more than one category, so a census response
that names several categories has to be assigned across those categories before
it can be used as a denominator. The office does not assign each person to a
single category outright; it splits each response into fractional shares, using
the shares the national statistics agency's standard method gives.

For each record listed in the input, report the share of that record's response
group that is assigned to that record's target category.

Input (`/root/data/`):

1. `response_records.csv` - one row per record, with a header and the columns
   `record_id`, `area_id`, `age_years`, `sex`, `hispanic_origin`,
   `response_group` and `target_category`. `response_group` is the set of
   categories the census response named, joined by `+`. `target_category` is the
   one category whose share this record asks for. `area_id` is an opaque label.

2. `area_profile.csv` - one row per `area_id`, with that area's own composition:
   the percentage of its residents who reported each single category alone, the
   percentage who reported more than one, its census region, and how urban it is.

3. `question.json` - the records to report, what each category code means, the
   output contract, and an `orientation_flat_shares` block. That block gives one
   flat set of shares per response group for the whole country; it is supplied
   for orientation only.

The shares are not a fixed split of the response group. The agency estimated them
from a household survey and publishes them as fitted equations, one family of
equations per response group, evaluated on the person's own age, sex and origin
and on the composition of the area they live in. Which equation applies to a
given record is a property of that record, and neither the equations nor their
constants are recoverable from anything in `/root/data`.

Output:
Write `/root/results.json` with exactly:

```json
{"assignment_share": {"R-99": 42.7}}
```

- `assignment_share` - for every entry in `question.json`'s `records_to_report`,
  the share of that record's response group assigned to that record's
  `target_category`, keyed by `record_id`. Report at least six decimal places.

(The key and the number above are placeholders that show the JSON shape only.
They are not the answer: `R-99` is not a record in this input, and a share is a
number between 0 and 1, so `42.7` is roughly forty times larger than the largest
value any record could take.)

Scoring: one test case per record, 31 in total. A case passes iff the reported
value is within 0.002 of the reference. Score = cases passed / 31.

The container has Python 3 with numpy installed. No network access.
