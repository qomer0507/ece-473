"""Fetch the NWS daily climate report (CLI) json from IEM for the rain stations, one file per station-year.

    python scripts/rain_fetch_cli.py            # KTTN, KPHL, KABE, 1995-2026
Cached in data/raw/rain/iem_cli/<KXXX>_<year>.json. Existing files are kept (not downloaded again); files already
cached by the Kalshi workstream in data/raw/kalshi/iem_cli/ are not fetched again either. 2 s between requests.
"""
import json
import os
import sys
import time
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "data", "raw", "rain", "iem_cli")
OTHER = os.path.join(ROOT, "data", "raw", "kalshi", "iem_cli")
URL = "https://mesonet.agron.iastate.edu/json/cli.py?station={sid}&year={year}"


def main(stations=("KTTN", "KPHL", "KABE"), first=1995, last=2026):
    os.makedirs(OUT, exist_ok=True)
    log = open(os.path.join(OUT, "fetch.log"), "a")
    for sid in stations:
        for year in range(first, last + 1):
            name = f"{sid}_{year}.json"
            if os.path.exists(os.path.join(OUT, name)) or os.path.exists(os.path.join(OTHER, name)):
                continue
            url = URL.format(sid=sid, year=year)
            try:
                with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "course-project"}), timeout=60) as r:
                    body = r.read()
                n = len(json.loads(body).get("results", []))
                with open(os.path.join(OUT, name), "wb") as fh:
                    fh.write(body)
                msg = f"{time.strftime('%F %T', time.gmtime())} {name} rows={n}"
            except Exception as exc:  # recorded, not retried silently
                msg = f"{time.strftime('%F %T', time.gmtime())} {name} FAILED {exc!r}"
            print(msg)
            log.write(msg + "\n")
            log.flush()
            time.sleep(2)


if __name__ == "__main__":
    main(*( [sys.argv[1].split(",")] if len(sys.argv) > 1 else [] ))
