"""Oracle solver. Reads the shipped survey inputs, computes each station's true
azimuth by reducing the measured magnetic azimuth through the IGRF-13 magnetic
declination at the survey epoch, and writes /root/results.json. Derives
everything from the baked coefficient file; embeds no stored answer."""
import csv
import json
import os

import igrf_synth

DATA = "/root/data"
OUT = "/root/results.json"


def main():
    with open(os.path.join(DATA, "question.json")) as f:
        question = json.load(f)
    epoch = float(question["survey_epoch_decimal_year"])

    stations = {}
    with open(os.path.join(DATA, "stations.csv")) as f:
        for row in csv.DictReader(f):
            sid = row["station_id"]
            lat = float(row["latitude_deg"])
            lon = float(row["longitude_deg"])
            elev_km = float(row["elevation_m"]) / 1000.0
            mag_az = float(row["magnetic_azimuth_deg"])
            true_az = igrf_synth.true_azimuth(epoch, lat, lon, elev_km, mag_az)
            stations[sid] = {"true_azimuth_deg": true_az}

    with open(OUT, "w") as f:
        json.dump({"stations": stations}, f, indent=2)
        f.write("\n")


if __name__ == "__main__":
    main()
