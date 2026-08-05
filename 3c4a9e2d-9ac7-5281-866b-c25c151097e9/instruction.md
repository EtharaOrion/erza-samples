Task:
A UK operator of depots and packing sites is compiling its corporate
greenhouse-gas inventory for two reporting periods, calendar year 2024 and
calendar year 2025. The activity data has already been collected and
categorised; what remains is the conversion to emissions, done the way a UK
inventory is required to do it.

Input (`/root/data/`):

1. `activity_ledger.csv` — one row per activity line per reporting period,
   with a header and the columns `line_id`, `reporting_period`, `scope`,
   `category_level_1`, `category_level_2`, `category_level_3`, `column_text`,
   `unit`, `quantity` and `description`. The category columns follow the
   taxonomy used in the UK Government's published conversion-factor tables;
   `column_text` carries the sub-column where the taxonomy has one (a
   waste-disposal route or a material-sourcing basis) and is empty otherwise.
   Quantities are exact metered values in the stated unit.

2. `question.json` — the cases to report, the output contract, and notes.
   Each case is one ledger line, identified by its `line_id`.

For each case, compute the emissions of that ledger line in kilograms of CO2e,
at the precision the output contract asks for. The specification a UK inventory
is required to convert by is not reproduced in this prompt: determine it and
apply it correctly. The kWh lines state their calorific-value basis; the volume
lines are metered volume.

Output:
Write `/root/results.json` with exactly:

```json
{"kg_co2e": {"co2e-example-line-2099": 123456.789}}
```

- `kg_co2e` — for every entry in `question.json`'s `cases_to_report`, the
  emissions of that line in kg CO2e, keyed by `case_id`. Report at least four
  decimal places.

(The key and the number above are placeholders that show the JSON shape only.
They are not an answer: `co2e-example-line-2099` is not a case in this input,
and no graded line's emissions equal 123456.789 kg.)

Scoring:
Each `case_id` in `cases_to_report` is graded as one case, and there is exactly
one graded case per `case_id`. A case passes if and only if the value you report
for it falls within the grading tolerance of the reference value for that case.
Your score is the number of cases that pass divided by the total number of
graded cases, so every line earns credit on its own and one you get wrong costs
only that line.

The container has Python 3. No network access.
