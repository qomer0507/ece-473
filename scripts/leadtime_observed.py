"""Observed decision-time table (task 1): data/processed/leadtime/observed_by_decision_time.csv. No network."""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.leadtime.observed import observed_table  # noqa: E402

REPO = Path(__file__).resolve().parents[1]
QUOTES = REPO / "data" / "raw" / "kalshi" / "rain" / "quote_table.csv"
OUT = REPO / "data" / "processed" / "leadtime" / "observed_by_decision_time.csv"


def main() -> None:
    q = pd.read_csv(QUOTES)
    t = observed_table(q)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    t.to_csv(OUT, index=False, float_format="%.4f")
    cols = ["group", "hours_before_close", "market_days", "usable_ask_share", "premium_per_payout",
            "premium_fee_per_payout", "rain_no_offer_share", "brier_mid", "n_two_sided", "mean_ask_rain", "mean_ask_dry"]
    print(t[cols].to_string(index=False))


if __name__ == "__main__":
    main()
