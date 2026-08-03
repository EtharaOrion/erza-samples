"""Reference solution. Emits one payee detail record per payee from the baked
semantic data and the published field table, then writes /root/results.json.

Nothing here is stored: every position of every record is produced by walking
oracle/layout.py's transcription of the published table over the supplied
payee data.
"""

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import layout  # noqa: E402

DATA = os.environ.get("DATA_DIR", "/root/data")
OUT = os.environ.get("RESULTS_PATH", "/root/results.json")


def main():
    with open(os.path.join(DATA, "question.json")) as fh:
        question = json.load(fh)
    with open(os.path.join(DATA, "payees.json")) as fh:
        payees = json.load(fh)["payees"]

    payment_year = question["payment_year"]
    records = {}
    for payee in payees:
        records[payee["payee_ref"]] = layout.emit_record(payee, payment_year)

    with open(OUT, "w") as fh:
        json.dump({"records": records}, fh, indent=2, sort_keys=True)
    print("wrote %s (%d records)" % (OUT, len(records)))


if __name__ == "__main__":
    main()
