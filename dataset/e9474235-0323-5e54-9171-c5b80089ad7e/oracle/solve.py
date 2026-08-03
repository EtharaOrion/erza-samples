"""Oracle reference solver. Reads the shipped target times and station list, computes
each station/time tide height by harmonic synthesis through oracle/tide_predict.py using
the station harmonic constants baked beside it, and writes /root/results.json.
Derives everything by computation; embeds no stored answer."""
import csv, json, os
from datetime import datetime
import tide_predict as tp

DATA = "/root/data"
OUT = "/root/results.json"
HERE = os.path.dirname(os.path.abspath(__file__))

def main():
    q = json.load(open(os.path.join(DATA, "question.json")))
    times = q["target_times_utc"]
    sids = [row["station_id"] for row in csv.DictReader(open(os.path.join(DATA, "stations.csv")))]
    defs = tp.load_definitions(os.path.join(HERE, "tidal_constituents.json"))
    stn = tp.load_stations(os.path.join(HERE, "harmonic_constants.json"))
    preds = {}
    for sid in sids:
        preds[sid] = {}
        for iso in times:
            dt = datetime.strptime(iso, "%Y-%m-%dT%H:%M:%SZ")
            preds[sid][iso] = round(tp.predict_height(stn[sid], defs, dt), 4)
    with open(OUT, "w") as f:
        json.dump({"predictions": preds}, f, indent=2); f.write("\n")

if __name__ == "__main__":
    main()
