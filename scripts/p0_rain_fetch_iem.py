"""Phase 0 rain probe: pull raw ASOS/METAR precipitation reports from IEM, one request at a time, cached.

Two requests per station against https://mesonet.agron.iastate.edu/cgi-bin/request/asos.py :
  A) p01i only, 1930-01-01 .. 1990-01-01 (all report types)  -> is there any hourly precip before ASOS?
  B) p01i + raw METAR text, 1990-01-01 .. 2026-11-01, report types 3 (routine) and 4 (special)
Times are UTC. missing=M, trace=T so the two can be told apart from numbers.
Cache: data/raw/rain/iem_asos/<SID>_<A|B>.csv.gz (never re-fetched if present).

Usage: python scripts/p0_rain_fetch_iem.py [SID ...]
"""
import gzip, os, subprocess, sys, time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "data", "raw", "rain", "iem_asos")
BASE = "https://mesonet.agron.iastate.edu/cgi-bin/request/asos.py"
STATIONS = ["TTN", "PHL", "PNE", "ABE", "EWR", "NYC", "JFK", "LGA", "WRI", "NEL", "BLM", "DYL"]
PARTS = {
    "A": "data=p01i&sts=1930-01-01T00:00:00Z&ets=1990-01-01T00:00:00Z",
    "B": "data=p01i&data=metar&sts=1990-01-01T00:00:00Z&ets=2026-11-01T00:00:00Z&report_type=3&report_type=4",
}


def fetch(sid, part):
    dst = os.path.join(OUT, f"{sid}_{part}.csv.gz")
    if os.path.exists(dst) and os.path.getsize(dst) > 100:
        print(f"cached {dst}", flush=True)
        return
    url = f"{BASE}?station={sid}&{PARTS[part]}&tz=UTC&format=onlycomma&missing=M&trace=T"
    tmp = dst + ".part"
    for attempt in range(4):
        t0 = time.time()
        with open(tmp, "wb") as fh:
            r = subprocess.run(["curl", "-sS", "--compressed", "-m", "1500", "-w", "%{http_code}", "-o", "-", url],
                               stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            body, code = r.stdout[:-3], r.stdout[-3:].decode()
            fh.write(gzip.compress(body, 6))
        ok = code == "200" and body.startswith(b"station,valid")
        print(f"{sid} {part} http={code} bytes={len(body)} secs={time.time()-t0:.0f} ok={ok} {r.stderr.decode()[:200]}", flush=True)
        if ok:
            os.replace(tmp, dst)
            with open(os.path.join(OUT, "requests.log"), "a") as lg:
                lg.write(f"{time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())}\t{sid}\t{part}\t{len(body)}\t{url}\n")
            return
        time.sleep(20 * (attempt + 1))
    print(f"FAILED {sid} {part}", flush=True)


if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    for sid in (sys.argv[1:] or STATIONS):
        for part in ("B", "A"):
            fetch(sid, part)
            time.sleep(3)
