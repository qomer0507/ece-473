"""Phase 0 rain probe: daily PRCP from the NCEI Access Data Service (GHCN-Daily 'daily-summaries'), cached.

One request per station per <=25-year block. Cache: data/raw/rain/ncei_daily/<GHCN id>_<y0>_<y1>.csv
Usage: python scripts/p0_rain_fetch_ncei_daily.py
"""
import os, subprocess, time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "data", "raw", "rain", "ncei_daily")
BASE = "https://www.ncei.noaa.gov/access/services/data/v1"
STATIONS = {
    "TTN": "USW00014792", "PHL": "USW00013739", "PNE": "USW00094732", "ABE": "USW00014737",
    "EWR": "USW00014734", "NYC": "USW00094728", "JFK": "USW00094789", "LGA": "USW00014732",
    "WRI": "USW00014706", "NEL": "USW00014780", "BLM": "USW00054760", "DYL": "USW00054786",
}
BLOCKS = [(1865, 1899), (1900, 1924), (1925, 1949), (1950, 1974), (1975, 1999), (2000, 2026)]

if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    for sid, gid in STATIONS.items():
        for y0, y1 in BLOCKS:
            dst = os.path.join(OUT, f"{gid}_{y0}_{y1}.csv")
            if os.path.exists(dst):
                continue
            url = (f"{BASE}?dataset=daily-summaries&stations={gid}&dataTypes=PRCP&units=standard"
                   f"&startDate={y0}-01-01&endDate={y1}-12-31&format=csv&includeAttributes=true")
            for attempt in range(4):
                r = subprocess.run(["curl", "-sS", "-m", "300", "-w", "%{http_code}", "-o", dst + ".part", url],
                                   stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                code = r.stdout.decode()
                if code == "200":
                    os.replace(dst + ".part", dst)
                    break
                time.sleep(10 * (attempt + 1))
            n = sum(1 for _ in open(dst)) - 1 if os.path.exists(dst) else -1
            print(sid, gid, y0, y1, code, n, flush=True)
            with open(os.path.join(OUT, "requests.log"), "a") as lg:
                lg.write(f"{time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())}\t{sid}\t{gid}\t{code}\t{n}\t{url}\n")
            time.sleep(1.5)
