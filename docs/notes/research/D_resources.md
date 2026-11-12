# D. Data resources: what exists, how to get it, what it costs

Checked 2026-11-11. Web only (WebSearch and WebFetch). The shell could not reach NOAA, AWS or BigQuery.
WebFetch summarizes pages. Quoted rule text was returned in pieces. Counts made by the summarizer are marked "tallied".
Status codes: FREE-CONFIRMED (fetched and worked today), FREE-LIKELY (documented free, not exercised), PAID, UNKNOWN.
"From memory" means not verified today.

---

## 1. Kalshi

Base that worked today: `https://api.elections.kalshi.com/trade-api/v2`
Docs now show another base: `https://external-api.kalshi.com/trade-api/v2` (https://docs.kalshi.com/getting_started/quick_start_market_data). Not tested.
Docs state: "No authentication headers are required for the endpoints in this guide."

### 1a. Settlement station per series

All six `/series/{ticker}` responses name one settlement source: The Weather Company, https://weather.com/kalshi.
All six point to the same contract file: https://assets.kalshi.com/regulatory/product-certifications/GLOBALTEMPERATURE.pdf
The station code is only in each market's `rules_primary`. Pattern: "If the maximum temperature recorded at {City} ({CLI code}) for {date} is greater than X° fahrenheit according to The Weather Company, then the market resolves to Yes."

| Series | Series title | Code in rules_primary | Market sampled | Station behind the code |
|---|---|---|---|---|
| KXHIGHNY | Highest temperature in NYC | New York City (CLINYC) | KXHIGHNY-26OCT14-T85 | Central Park. Confirmed by older rules text and NHIGH.pdf. ICAO KNYC. |
| KXHIGHPHIL | Highest temperature in Philadelphia | Philadelphia (CLIPHL) | KXHIGHPHIL-26AUG23-T87 | Philadelphia Intl Airport, KPHL. Name inferred from the NWS CLI code. Not confirmed today. |
| KXHIGHTEWR | Newark, NJ (EWR) Daily Max Temp | Newark (CLIEWR) | KXHIGHTEWR-26NOV12-T65 | IEM CLI record names it "NEWARK INTL AIRPORT", product CLIEWR, WFO OKX. KEWR. |
| KXHIGHTTTN | Trenton, NJ Daily Max Temp | Trenton (CLITTN) | KXHIGHTTTN-26AUG29-T79 | IEM CLI record names it "TRENTON/MERCER CO.", product CLITTN, WFO PHI. KTTN. |
| KXHIGHTDC | Washington DC Daily Max Temp | Washington DC (CLIDCA) | KXHIGHTDC-26OCT13-T85 | Reagan National, KDCA. Name inferred from the code. Not confirmed today. |
| KXHIGHTBOS | (series title not fetched) | Boston (CLIBOS) | KXHIGHTBOS-26SEP15-T72 | Boston Logan, KBOS. Name inferred from the code. Not confirmed today. |

GHCN-Daily IDs for these stations, from memory, verify in ghcnd-stations.txt: Central Park USW00094728, PHL USW00013739, EWR USW00014734, TTN USW00014792, DCA USW00013743, BOS USW00014739.

Older rule wording, for the earlier part of the sample:
- HIGHNY-23JUL15: "highest temperature recorded in Central Park, New York", per the NWS report.
- HIGHNY-22MAY15: Central Park, per the NWS Daily Climate Report.
- KXHIGHPHIL-25JAN15: NWS Daily Climate Report, highest temperature in Philadelphia, PA. No station code in that text.
- Old contract terms: https://kalshi-public-docs.s3.amazonaws.com/contract_terms/NHIGH.pdf names "Central Park NY" and source page https://www.weather.gov/wrh/climate?wfo=okx

Open points:
- GLOBALTEMPERATURE.pdf (filed 2025-12-08) names no station. It lists the National Weather Service first among Source Agencies. The summary did not show The Weather Company in it. The API names The Weather Company. This mismatch is unresolved.
- Kalshi help page https://help.kalshi.com/markets/popular-markets/weather-markets still says daily markets settle on the NWS Daily Climate Report. It may be stale.
- Same help page: NWS climate reports use local standard time. In daylight time the day runs 1:00 AM to 12:59 AM. Station daily TMAX must match this day definition.
- weather.com/kalshi is a dynamic portal. Its station list and method could not be read.
- `rules_secondary` warns that preliminary Weather Company values can differ from final by rounding and unit conversion.

### 1b. Philadelphia history

- Earliest KXHIGHPHIL event found: **KXHIGHPHIL-24NOV20**. Six markets. Opened 2024-11-19T19:00Z.
- Empty: KXHIGHPHIL-24NOV19, -24NOV17, -24NOV08, -24OCT20.
- Present: -24NOV21, -24NOV25, -24DEC15, -25JAN15.
- No older Philadelphia ticker found. `/events?series_ticker=HIGHPHIL` returned an empty list. `/historical/markets?event_ticker=HIGHPHIL-24NOV15` returned an empty list. `/series/HIGHPHIL` failed with a client error (code not shown).
- `/historical/markets?series_ticker=KXHIGHPHIL` returns newest first with a cursor. Paging to the oldest was not done.
- So Philadelphia has about two years of history, not from 2026-03-28.

### 1c. NYC history

- Earliest HIGHNY event found: **HIGHNY-21AUG06**. One market (T86). Opened 2021-08-05T15:15Z.
- Empty: HIGHNY-21AUG05, -21AUG04, -21AUG01, -21JUL15.
- Present: -21AUG08 (one market), -21AUG15 (one market), -22MAY15 (at least three), -23JUL15 (six).
- Early days had one threshold market per day. The bracket ladder came later. The date of that change was not found.
- The date HIGHNY became KXHIGHNY was not checked.
- Earliest events for KXHIGHTDC and KXHIGHTBOS were not checked.

### 1d. Rate limits and data-use terms

- Rate limits: https://docs.kalshi.com/getting_started/rate_limits
  - Token buckets. A request costs 10 tokens by default. Basic tier: 200 read tokens per second. Advanced: 300.
  - Over the limit returns HTTP 429. No Retry-After header. Docs advise exponential backoff.
  - Limits for unauthenticated calls are not documented.
  - Today about one in three calls through the shared fetch service failed with a client error. Likely 429. Not confirmed.
- Historical tier: https://docs.kalshi.com/getting_started/historical_data
  - `GET /historical/cutoff` returned market_settled_ts 2026-09-12, trades_created_ts 2026-09-12.
  - Markets settled before the cutoff are under `/historical/...`. Newer ones are under the live endpoints.
- Data-use terms: Kalshi Developer Agreement v1.1, https://kalshi-public-docs.s3.amazonaws.com/Kalshi-Developer-Agreement.pdf
  - Summary of section 3: API use is for a member's own trading.
  - Summary of section 3.1: no sharing of data with third parties without prior written authorization.
  - Research use is not addressed.
  - Access is free. The licence for research and for redistribution is **UNKNOWN**.
  - Action: read sections 3 and 3.1 in full. Email Kalshi for written permission. Do not commit raw Kalshi data to a public repo. Publish code and derived statistics only.

### 1e. Do old candlesticks keep bid and ask?

Yes. FREE-CONFIRMED.
- Call: `/historical/markets/HIGHNY-23JUL15-T89/candlesticks?start_ts=1689343200&end_ts=1689480000&period_interval=60`
- Returned 23 hourly candles. Each has `yes_bid` and `yes_ask` with open, high, low, close as dollar strings.
- `price` fields are null in hours without trades. `volume` and `open_interest` are present.
- The window was 38 hours. Some hours are missing. Plan to forward-fill.
- Bid is often 0.0000 and ask 0.9900 or 1.0000. That means an empty side of the book, not a real quote. Filter these.
- Docs: https://docs.kalshi.com/api-reference/historical/get-historical-market-candlesticks.md . Allowed `period_interval`: 1, 60, 1440.
- The same call for HIGHNY-23JUL15-B88.5 failed three times with a client error. Cause unknown.

### 1f. Third-party archives

| Source | URL | What | Status |
|---|---|---|---|
| Hugging Face TrevorJS/kalshi-trades | https://huggingface.co/datasets/TrevorJS/kalshi-trades | 154.5M trades and 17.5M market rows, June 2021 to January 2026, 5.69 GB, CC-BY-4.0. Preview shows HIGHNY tickers. Bid and ask are one snapshot at fetch time, not a time series. | FREE-LIKELY (page read, files not downloaded) |
| Hugging Face ImpliedData/prediction-markets | https://huggingface.co/datasets/ImpliedData/prediction-markets | Seen in search only. | UNKNOWN |
| Apify actors (Kalshi weather scrapers) | https://apify.com/bigdavidson/kalshi-weather-markets | Wrappers on the public API. Not archives. | PAID or freemium, not checked |
| Allium | https://allium.so/blog/kalshi-historical-data-a-practical-guide/ | Commercial data vendor. | PAID (assumed, not checked) |
| therminal-py | https://pypi.org/project/therminal-py/ | Python SDK for Kalshi temperature markets plus NWS data. Operator unknown. | UNKNOWN |
| Kaggle | none found | Search found no Kalshi weather dataset. | UNKNOWN |

The Hugging Face set gives trade prints. Trades cross-check the candlesticks. It does not replace bid and ask history. Its CC-BY label may conflict with Kalshi's agreement.

---

## 2. NOAA station data

### GHCN-Daily routes

| Route | URL | Notes | Status |
|---|---|---|---|
| NCEI readme | https://www.ncei.noaa.gov/pub/data/ghcn/daily/readme.txt | Fetched. TMAX is tenths of °C. Quality flags listed. Cite Menne et al. 2012 and DOI 10.7289/V5D21VHZ. No licence text. | FREE-CONFIRMED (readme) |
| by_station CSV | https://www.ncei.noaa.gov/pub/data/ghcn/daily/by_station/ | Readme confirms the folder. One file per station, full record. File name `{ID}.csv.gz` is from memory. | FREE-LIKELY |
| Station list | https://www.ncei.noaa.gov/pub/data/ghcn/daily/ghcnd-stations.txt | Fixed width. ID cols 1-11, state cols 39-40. Not fetched (too large). | FREE-LIKELY |
| Inventory | https://www.ncei.noaa.gov/pub/data/ghcn/daily/ghcnd-inventory.txt | ID, lat, lon, element, first year, last year. Fetch failed (too large). | FREE-LIKELY |
| NCEI Access Data Service | https://www.ncei.noaa.gov/access/services/data/v1 | Docs: https://www.ncei.noaa.gov/support/access-data-service-api-user-documentation . No token mentioned. No stated limits. Docs warn of degraded service during cloud migration. | FREE-LIKELY |
| AWS open data | https://registry.opendata.aws/noaa-ghcn/ | Bucket `noaa-ghcn-pds`, us-east-1. `aws s3 ls --no-sign-request s3://noaa-ghcn-pds/`. No AWS account. CC0. Daily updates. The page says prefixes are changing. The by_station path was not confirmed. | FREE-LIKELY |
| BigQuery | `bigquery-public-data.ghcn_d` | Google docs: first 1 TB of queries per month free, a Cloud project is needed, billing is not (https://docs.cloud.google.com/bigquery/public-data). Table names `ghcnd_YYYY`, `ghcnd_stations`, `ghcnd_inventory` are from memory. Freshness not checked. | FREE-LIKELY |

Access Data Service example (built from the docs, not run):
`https://www.ncei.noaa.gov/access/services/data/v1?dataset=daily-summaries&stations=USW00094728,USW00014734&dataTypes=TMAX&startDate=2015-01-01&endDate=2025-12-31&format=csv&units=standard`

Recommended bulk route: download the by_station files for the chosen IDs. A few hundred small files. No rate limit is documented.

### Iowa Environmental Mesonet (IEM)

- Terms: https://mesonet.agron.iastate.edu/disclaimer.php . Public domain. Attribution appreciated. No rate guidance on that page.
- Daily summaries form: https://mesonet.agron.iastate.edu/request/daily.phtml . Variable `max_temp_f`. CSV, Excel or JSON. Networks by state (ASOS, COOP and others). For all stations at once, keep the span to one year or less.
- Backend: `https://mesonet.agron.iastate.edu/cgi-bin/request/daily.py?help` . The help page failed to load. Parameter names not verified.
- NWS CLI archive, the product Kalshi used before the switch: `https://mesonet.agron.iastate.edu/json/cli.py?station=KTTN&year=2025` . Worked today. Returns one record per day with `high`, `low`, `product` (for example CLITTN). One call per station-year. Archive start not stated.
- Status: FREE-CONFIRMED for cli.py. FREE-LIKELY for daily.py.

### How many stations report TMAX across 2015-2025?

The GHCN inventory could not be read here. ACIS station metadata was used instead. ACIS draws mainly on GHCN-Daily.
Call: `https://data.rcc-acis.org/StnMeta?state=NJ&elems=maxt&sdate=2015-01-01&edate=2025-12-31&meta=name,valid_daterange`
Rule: maxt record starts on or before 2015-01-01 and ends on or after 2025-12-01. Counts were tallied by the fetch summarizer.

| State | Any maxt data in 2015-2025 | Spanning 2015-2025 | Of which "Area" threaded records |
|---|---|---|---|
| NY | 210 | 142 | 17 |
| PA | 171 | 122 | 10 |
| NJ | 59 | 45 | 6 |
| CT | 36 | 22 | 2 |
| DE | 27 | 9 | 2 |
| Total | 503 | 340 | 37 |

- Rough answer: **about 300 real stations** (340 minus 37 threaded composites). Treat as plus or minus 10 percent.
- "Area" entries are ThreadEx composites. They duplicate airport stations. Drop them.
- A few names appear twice (Teterboro, Hartford Brainard).
- The rule checks first and last dates only. It does not check gaps. A completeness filter will cut the count further.
- So "hundreds" holds, at the low end. "Many hundreds" does not.

Exact count on a laptop:

```
curl -O https://www.ncei.noaa.gov/pub/data/ghcn/daily/ghcnd-stations.txt
curl -O https://www.ncei.noaa.gov/pub/data/ghcn/daily/ghcnd-inventory.txt
awk 'NR==FNR { st=substr($0,39,2); if (st ~ /^(NJ|NY|PA|CT|DE)$/) s[substr($0,1,11)]=st; next }
     ($1 in s) && $4=="TMAX" && $5<=2015 && $6>=2025 { n[s[$1]]++ }
     END { for (k in n) print k, n[k] }' ghcnd-stations.txt ghcnd-inventory.txt
```

---

## 3. Business weights

### Census County Business Patterns (CBP) and ZIP Code Business Patterns (ZBP)

- API page: https://www.census.gov/programs-surveys/cbp/data/api.html
- Latest year confirmed: **2023**. The 2024 endpoint could not be reached (fetch failed). Check `https://api.census.gov/data/2024/cbp`.
- Key: the CBP API page says "All data queries to the Census Data API now require an API key." The key is free. Sign-up page from memory: https://api.census.gov/data/key_signup.html
- Examples from https://api.census.gov/data/2023/cbp/examples.html :
  - County: `https://api.census.gov/data/2023/cbp?get=NAME,NAICS2017_LABEL,ESTAB,PAYANN,PAYQTR1,EMP&for=county:*&in=state:*&NAICS2017=00&LFO=001&EMPSZES=001&key=YOUR_KEY_GOES_HERE`
  - ZIP: `https://api.census.gov/data/2023/cbp?get=NAME,NAICS2017_LABEL,ESTAB,PAYANN,PAYQTR1,EMP&for=zip code:*&NAICS2017=00&LFO=001&EMPSZES=001&key=YOUR_KEY_GOES_HERE`
- ZIP data now sits in the same `cbp` endpoint. Encode the space in `zip code` as `%20`.
- Set `NAICS2017` to: `722` food services and drinking places, `713` amusement, gambling and recreation, `23` construction, `44-45` retail trade. Code labels are from memory. The predicate name is confirmed for 2023.
- Variables: https://api.census.gov/data/2023/cbp/variables.html
- Status: FREE-CONFIRMED for docs and examples. No live query was run (no key).

Known issues (https://www.census.gov/programs-surveys/cbp/technical-documentation/methodology.html):
- From 2017, a cell is published only if it has three or more establishments. Small ZIP by industry cells are missing, not zero.
- Employment and payroll carry noise. Flags: G under 2 percent, H 2 to 5 percent, J 5 percent or more.
- The page describes noise for employment and payroll only. Establishment counts are not described as noised. Use `ESTAB` for weights.
- At ZIP level, employment and payroll exist only for all sectors (NAICS 00). By industry only establishment counts by size class exist.
- Employment is for the week of March 12. Summer seasonal jobs are missed.
- Excluded: farms, rail, postal service, private households, public administration, most government.
- Census marks this methodology page "no longer current". It is reviewing alternatives to noise infusion.
- From memory: ZBP ZIP codes are postal ZIPs, not ZCTAs. Map them with care.
- Establishment counts ignore size. A stadium and a kiosk each count once.

### Which sectors are temperature-sensitive?

- Lazo, Lawson, Larsen, Waldman (2011), "U.S. Economic Sensitivity to Weather Variability", Bulletin of the American Meteorological Society. Summary read: https://news.ucar.edu/4810/economic-cost-weather-may-total-485-billion-us . Journal page failed to load.
  - Weather variability moves up to 3.4 percent of US GDP. Mining 14 percent, agriculture 12 percent, manufacturing 8 percent, utilities 7 percent. Retail trade 2 percent, services 3 percent.
  - New York was the most sensitive state at 13.5 percent of state product.
  - This cuts against a heavy retail weight.
- Roth Tran (2022), "Sellin' in the Rain: Weather, Climate, and Retail Sales", FRB San Francisco Working Paper 2022-02, https://doi.org/10.24148/wp2022-02 . Letter: https://www.frbsf.org/research-and-insights/publications/economic-letter/2022/08/impact-of-weather-on-retail-sales/ . Earlier version: https://www.federalreserve.gov/econres/feds/files/2019067pap.pdf
  - Daily sales at over 100 stores of one apparel and sporting goods brand, 2010 to 2013.
  - A one standard deviation weather shock moves sales about 10 percent over four weeks. Bad-weather losses persist. Good-weather gains fade.
  - One brand only.
- Gap: neither source measures restaurants, recreation or construction directly. A source for NAICS 722, 713 and 23 is still needed.

---

## 4. Forecast archives for a pricing baseline

| Source | URL | Back to 2023? | Cost and limits | Status |
|---|---|---|---|---|
| Open-Meteo Historical Forecast API | https://open-meteo.com/en/docs/historical-forecast-api ; endpoint `https://historical-forecast-api.open-meteo.com/v1/forecast` | Yes. GFS from 2021-03-23, HRRR from 2018, ECMWF IFS 9 km from 2017, NBM from 2024-10-08. | Free for non-commercial use. 10,000 calls per day, 5,000 per hour, 600 per minute. CC BY 4.0. (https://open-meteo.com/en/pricing) | FREE-LIKELY |
| Open-Meteo Previous Runs API | https://open-meteo.com/en/docs/previous-runs-api ; endpoint `https://previous-runs-api.open-meteo.com/v1/forecast` | Partly. GFS 2 m temperature from March 2021. Most other models from January 2024. | Same free tier. | FREE-LIKELY |
| IEM MOS archive | https://mesonet.agron.iastate.edu/mos/ ; `/api/1/mos.json?station=KNYC&model=GFS&runtime=...` | Yes. GFS MOS from 2003-12-16. NBS from 2018-11-07. NBE from 2020-07-23. MEX and LAV from 2020-07-12. | Free. Public domain. No stated limits. | FREE-LIKELY (page read, API not run) |
| NDFD | https://registry.opendata.aws/noaa-ndfd/ (bucket `noaa-ndfd-pds`) ; https://www.ncei.noaa.gov/thredds/catalog/model/ndfd.html | Unknown. Neither page states a start date. | Free. No AWS account. GRIB2 grids. Heavy to process. | FREE-LIKELY, depth UNKNOWN |
| NBM | https://registry.opendata.aws/noaa-nbm (bucket `noaa-nbm-grib2-pds`) ; text at `https://noaa-nbm-grib2-pds.s3.amazonaws.com/blend.YYYYMMDD/HH/text/` per https://vlab.noaa.gov/web/mdl/nbm-text-archives | Likely. The MDL page says "through at least May 2020", wording unclear. | Free. No AWS account. | FREE-LIKELY, depth UNKNOWN |

Caveats:
- The Open-Meteo Historical Forecast API stitches the first hours of each run. It is close to an analysis. It is not a day-ahead forecast. Use the Previous Runs API or MOS for a true lead-time forecast.
- MOS and NBM text give a station max temperature forecast at fixed lead times. That is the closest match to what a trader saw. Check that KNYC, KPHL, KEWR, KTTN, KDCA and KBOS are in the MOS station list.
- Best pick for a 2023-onward baseline: IEM GFS MOS and NBS. Second: Open-Meteo Previous Runs (GFS).

---

## 5. Gridded temperature for validation

| Product | Resolution | Period | Access | Status |
|---|---|---|---|---|
| PRISM daily | 4 km free. 800 m time series free since 2025-03-27. | Daily from 1981 | https://prism.oregonstate.edu/ ; bulk info https://prism.oregonstate.edu/downloads ; directory https://data.prism.oregonstate.edu ; Data Explorer takes up to 500 points per request. Terms: https://prism.oregonstate.edu/terms (not read). | FREE-LIKELY |
| nClimGrid-Daily | 1/24 degree (about 5 km) | 1951 to present. Preliminary after 2 to 3 days. | https://www.ncei.noaa.gov/products/land-based-station/nclimgrid-daily ; files https://www.ncei.noaa.gov/data/nclimgrid-daily/ ; monthly NetCDF. DOI 10.25921/c4gt-r169. An AWS copy was not confirmed. | FREE-LIKELY |
| Daymet V4 R1 | 1 km | 1980 to 2023 per the user guide. Later years not checked. One release per year. | https://daac.ornl.gov/DAYMET/guides/Daymet_Daily_V4R1.html ; ORNL DAAC. Earthdata login may be needed (not confirmed). | FREE-LIKELY |

Caveats:
- All three are interpolated from station data. nClimGrid-Daily and Daymet use GHCN-Daily. PRISM ingests many station networks.
- They are not independent of the project's stations. Agreement is partly built in.
- For a real test, hold stations out and predict them.
- Day definitions differ. From memory, the PRISM day ends at 1200 UTC. nClimGrid-Daily mixes morning and midnight observers. The Kalshi CLI day is midnight to midnight local standard time.
- Grid cells smooth the urban heat island and coastal gradients. A Central Park or Newark cell value is not the sensor value.

---

## Summary table

| Resource | Needed for | Status | How to get | Fallback |
|---|---|---|---|---|
| Kalshi series and market rules | Settlement station and source | FREE-CONFIRMED | `/series/{ticker}`, `/markets?series_ticker=` | GLOBALTEMPERATURE.pdf, help center |
| Kalshi historical markets | Event list, strikes, results | FREE-CONFIRMED | `/historical/markets?event_ticker=` ; NYC from 2021-08-06, Philadelphia from 2024-11-20 | Hugging Face TrevorJS/kalshi-trades |
| Kalshi hourly candlesticks | Real bid and ask | FREE-CONFIRMED (one 2023 market) | `/historical/markets/{ticker}/candlesticks`, period 1, 60 or 1440 | Trade prints from `/historical/trades` or Hugging Face |
| Kalshi research licence | Right to store and share data | UNKNOWN | Read the Developer Agreement. Email Kalshi. | Share code and derived results only |
| Newark and Trenton markets | NJ contracts | FREE-CONFIRMED, short history (from 2026-08-26) | Same endpoints | Use NYC and Philadelphia as proxies |
| NWS CLI daily highs | Ground truth for settlement | FREE-CONFIRMED | IEM `json/cli.py?station=KNYC&year=YYYY` | GHCN-Daily TMAX for the same station |
| GHCN-Daily TMAX | About 300 stations, 2015-2025 | FREE-LIKELY | NCEI by_station CSV, stations and inventory files | AWS `noaa-ghcn-pds`, BigQuery `ghcn_d`, ACIS, IEM daily |
| Station count | Scope claim | Rough: about 300 (tallied) | awk command in section 2 | ACIS StnMeta |
| CBP and ZBP 2023 | Business weights | FREE-CONFIRMED (docs), free key required | `api.census.gov/data/2023/cbp`, `ESTAB` by NAICS 722, 713, 23, 44-45 | CBP flat files on census.gov, county level only |
| Sector sensitivity evidence | Justify weights | FREE-CONFIRMED (two sources), gap for restaurants | Lazo et al. 2011, Roth Tran 2022 | Sensitivity test over weight choices |
| IEM MOS (GFS, NBS) | Forecast baseline from 2023 | FREE-LIKELY | `/api/1/mos.json` | Open-Meteo Previous Runs (GFS) |
| Open-Meteo | Second baseline | FREE-LIKELY, non-commercial | Historical Forecast and Previous Runs APIs | NBM text on AWS |
| NDFD and NBM grids | Official forecast archive | FREE-LIKELY, depth UNKNOWN | AWS `noaa-ndfd-pds`, `noaa-nbm-grib2-pds` | IEM MOS |
| PRISM, nClimGrid-Daily, Daymet | Spatial sanity check | FREE-LIKELY | URLs in section 5 | Leave-one-station-out test |

## Not verified, in one place

- Station names behind CLIPHL, CLIDCA, CLIBOS.
- Why GLOBALTEMPERATURE.pdf shows NWS while the API shows The Weather Company.
- What weather.com/kalshi reports and from which sensor.
- HTTP code behind the failed Kalshi calls.
- Earliest KXHIGHTDC and KXHIGHTBOS events. The HIGHNY to KXHIGHNY change date.
- GHCN by_station file naming, AWS prefixes, BigQuery table freshness.
- IEM daily.py parameter names.
- CBP 2024 availability.
- NDFD and NBM archive start dates.
- PRISM day definition and terms text. Daymet years after 2023 and login need.
- All tallied station counts.
