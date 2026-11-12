"""Phase 0 rain probe: hourly liquid-precipitation groups (AA1..AA4) from NCEI 'global-hourly' (ISD), cached.

Purpose: IEM carries no hourly precipitation before ASOS (late 1990s). ISD does, for first-order stations.
One request per station per 5-year block, 1941-2005 (2005 gives an overlap with the IEM/METAR series).
Cache: data/raw/rain/ncei_global_hourly/<SID>_<y0>_<y1>.csv.gz
Usage: python scripts/p0_rain_fetch_ncei_hourly.py [SID ...]
"""
import gzip, os, subprocess, sys, time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "data", "raw", "rain", "ncei_global_hourly")
BASE = "https://www.ncei.noaa.gov/access/services/data/v1"
# USAF+WBAN ids from https://www.ncei.noaa.gov/pub/data/noaa/isd-history.csv (saved in ncei_global_hourly_probe/)
STATIONS = {
    "PHL": ["99999913739", "72408013739"], "EWR": ["99999914734", "72502014734"],
    "ABE": ["99999914737", "72517014737"], "LGA": ["99999914732", "72503014732"],
    "JFK": ["99999994789", "74486094789"], "NYC": ["99999994728", "72503394728", "72505394728"],
    "TTN": ["72409514792"], "PNE": ["99999994732", "72408594732"],
    "WRI": ["72409614706"], "NEL": ["99999914780", "72409014780"],
}

if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    for sid in (sys.argv[1:] or STATIONS):
        for y0 in range(1941, 2006, 5):
            y1 = y0 + 4
            dst = os.path.join(OUT, f"{sid}_{y0}_{y1}.csv.gz")
            if os.path.exists(dst):
                continue
            url = (f"{BASE}?dataset=global-hourly&stations={','.join(STATIONS[sid])}&dataTypes=AA1,AA2,AA3,AA4"
                   f"&startDate={y0}-01-01&endDate={y1}-12-31&format=csv")
            code, body = "000", b""
            for attempt in range(4):
                t0 = time.time()
                r = subprocess.run(["curl", "-sS", "--compressed", "-m", "600", "-w", "%{http_code}", "-o", "-", url],
                                   stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                body, code = r.stdout[:-3], r.stdout[-3:].decode()
                if code == "200":
                    with open(dst, "wb") as fh:
                        fh.write(gzip.compress(body, 6))
                    break
                time.sleep(15 * (attempt + 1))
            print(sid, y0, y1, code, len(body), f"{time.time()-t0:.0f}s", flush=True)
            with open(os.path.join(OUT, "requests.log"), "a") as lg:
                lg.write(f"{time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())}\t{sid}\t{code}\t{len(body)}\t{url}\n")
            time.sleep(1.5)
