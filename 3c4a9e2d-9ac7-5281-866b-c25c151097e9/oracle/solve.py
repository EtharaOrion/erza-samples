"""Reference solution. Converts each activity line to kg CO2e.

Reads /root/data only. The answer key is never opened: every line is converted
here from its own quantity and its own period's published factor, so agreement
with the key is a reproduction, not a copy.
"""

import csv
import json
import os
import sys
from decimal import Decimal, getcontext

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import factors  # noqa: E402

getcontext().prec = 50

DATA = os.environ.get("DATA_DIR", "/root/data")
OUT = os.environ.get("RESULTS_PATH", "/root/results.json")


def factor_for(rec):
    """The published factor for this line, in its own reporting period's edition.

    The ledger carries the published taxonomy's own columns, so the key is read
    straight off the row. Level 4 is empty for most rows but carries "kWh" on
    the electricity rows, so a miss is retried with it before giving up.
    """
    year = int(rec["reporting_period"][2:])
    table = factors.FACTORS[year]
    key = (rec["scope"], rec["category_level_1"], rec["category_level_2"],
           rec["category_level_3"], "", rec["column_text"], rec["unit"])
    if key not in table:
        key = key[:4] + ("kWh",) + key[5:]
    if key not in table:
        raise SystemExit("no published factor row for %r" % (key,))
    return Decimal(table[key])


def main():
    with open(os.path.join(DATA, "question.json")) as fh:
        question = json.load(fh)

    with open(os.path.join(DATA, "activity_ledger.csv"), newline="") as fh:
        ledger = {r["line_id"]: r for r in csv.DictReader(fh)}

    answers = {}
    for case in question["cases_to_report"]:
        cid = case["case_id"] if isinstance(case, dict) else case
        line_id = (case["line_id"] if isinstance(case, dict) and "line_id" in case
                   else cid[len("co2e-"):])
        rec = ledger[line_id]
        answers[cid] = float(Decimal(rec["quantity"]) * factor_for(rec))

    with open(OUT, "w") as fh:
        json.dump({"kg_co2e": answers}, fh, indent=2, sort_keys=True)
    print("wrote %d lines to %s" % (len(answers), OUT))


if __name__ == "__main__":
    main()
