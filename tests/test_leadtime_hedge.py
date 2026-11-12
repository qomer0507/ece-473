"""Price clamp, fee, and a hand-checked HE example by lead (src/leadtime/hedge_by_lead.py)."""
import numpy as np
import pandas as pd
import pytest

from src.hedge_eval.metrics import hedge_effectiveness
from src.leadtime.hedge_by_lead import (choose_n, evaluate_lead, modelled_ask, modelled_day_cost,
                                        season_unit_table, split_60_40)


def test_modelled_ask_clamps_to_cent_grid():
    assert modelled_ask(0.30, 0.0851) == pytest.approx(0.39)       # 0.3851 -> 0.39
    assert modelled_ask(0.95, 0.0851) == 0.99                       # above 0.99 -> 0.99
    assert modelled_ask(0.0, 0.0) == 0.01                           # floor 0.01
    assert modelled_ask(0.0, 0.068) == pytest.approx(0.07)
    assert modelled_ask(0.5, 0.0851) >= modelled_ask(0.4, 0.0851)   # monotone
    with pytest.raises(ValueError):
        modelled_ask(1.2, 0.0)


def test_day_cost_fee_and_fill():
    prem, pay, ask = modelled_day_cost(0.30, rain=0, a=0.0851, u=0.0833)
    assert ask == pytest.approx(0.39)
    # fee = round_up_to_cent(0.07 * 0.39 * 0.61) = round_up(1.665 cents) = 2 cents
    assert prem == pytest.approx(0.41)
    assert pay == 0.0
    prem_r, pay_r, _ = modelled_day_cost(0.30, rain=1, a=0.0851, u=0.0833)
    assert prem_r == pytest.approx(0.41 * (1 - 0.0833))
    assert pay_r == pytest.approx(1 - 0.0833)
    # u = 0: full fill
    assert modelled_day_cost(0.30, 1, 0.0851, 0.0)[1] == 1.0


def test_season_unit_table_sums_per_season():
    days = pd.DataFrame({"season": [2010, 2010, 2011], "k_s": [1, 0, 0], "month": [6, 6, 6]})
    pop = np.array([0.9, 0.1, 0.1])
    t = season_unit_table(days, pop, a=0.0, u=0.0)
    # asks 0.90 (fee ceil(0.07*0.9*0.1*100=0.63)=1c) and 0.10 (fee ceil(0.63)=1c)
    assert t.loc[t["season"] == 2010, "premium"].iloc[0] == pytest.approx(0.91 + 0.11)
    assert t.loc[t["season"] == 2010, "payout"].iloc[0] == 1.0
    assert t.loc[t["season"] == 2011, "premium"].iloc[0] == pytest.approx(0.11)
    assert list(t["n_days"]) == [2, 1]


def test_choose_n_hand_example():
    # three TRAIN seasons: D_park 2, 6, 10 (reference 6); contract pays exactly D_park, premium 4 per season
    d = np.array([2.0, 6.0, 10.0])
    pay = d.copy()
    prem = np.array([4.0, 4.0, 4.0])
    # net(n) = d - n d + 4 n; season 3: 10 - 6n; above the reference 6 while n < 2/3 -> HE rises with n up to 1
    n, he = choose_n(d, pay, prem, 6.0)
    assert n == 1.0
    assert he == pytest.approx(1.0)       # at n = 1 every season costs exactly 4 < 6: SV = 0
    # a useless contract (never pays, costs money): every n gives HE <= 0 and ties go to the smallest n
    n2, he2 = choose_n(d, np.zeros(3), prem, 6.0)
    assert n2 == 0.05 and he2 < 0


def test_hand_checked_he_by_lead():
    """Two leads on the same seasons. A 'good forecast' lead prices rain days high and dry days low; a
    'climatology' lead prices every day the same. With a = 0 and u = 0 and no fee on these prices, the hand
    sums below are exact."""
    # TRAIN: two seasons of 4 days each; REPORT: two seasons of 4 days each
    def mk(season, ks):
        return pd.DataFrame({"date": pd.date_range(f"{season}-06-01", periods=len(ks)), "season": season,
                             "month": 6, "c_s": ks, "k_s": ks, "d_park": ks})
    train = pd.concat([mk(2001, [1, 0, 0, 0]), mk(2002, [1, 1, 1, 0])], ignore_index=True)
    report = pd.concat([mk(2011, [0, 0, 0, 0]), mk(2012, [1, 1, 1, 1])], ignore_index=True)
    # PoPs chosen so asks are 0.01 on dry days and 0.99 on rain days (fee = ceil(0.07*0.99*0.01*100 = 0.0693) = 1c)
    good = lambda d: np.where(d["k_s"].to_numpy() == 1, 0.99, 0.01)  # noqa: E731
    r = evaluate_lead(train, report, good(train), good(report), np.ones(len(train), bool), np.ones(len(report), bool),
                      a=0.0, worst_rule="worst3", label="good", u=0.0, n_draws=50, seed=1)
    # TRAIN: reference = mean D_park = (1 + 3) / 2 = 2.  Per contract per season: premium = rain*(1.00) + dry*(0.02)
    #   2001: 1.00 + 3*0.02 = 1.06, payout 1;  2002: 3.00 + 0.02 = 3.02, payout 3
    #   net(n) = D - n*pay + n*prem = D + n*0.06 (2001), D + n*0.02 (2002): both below/at the reference for n=...
    #   2002: 3 + 0.02 n > 2 for every n, so HE(n) = 1 - (1 + 0.02n)^2 / 1: largest at the smallest n
    assert r.n == 0.05
    assert r.reference == 2.0
    # REPORT at n = 0.05: 2012: D = 4, premium 0.05*4.00 = 0.2, payout 0.05*4 = 0.2 -> net 4.0; 2011: net 0 + 0.05*0.08 = 0.004
    #   SV(unhedged) = ((4-2)^2 + 0)/2 = 2 ; SV(hedged) = ((4.0 - 2)^2 + 0)/2 = 2 -> HE = 0
    assert r.metrics["he"] == pytest.approx(0.0, abs=1e-9)
    assert r.metrics["premium_per_payout"] == pytest.approx((0.05 * 4.0 + 0.05 * 0.08) / 0.2)
    assert r.report_seasons == [2011, 2012]
    # fixed n = 1 at the same prices: 2012 net = 4 - 4 + 4.0 = 4.0 (the forecast price takes the whole payout)
    r1 = evaluate_lead(train, report, good(train), good(report), np.ones(len(train), bool), np.ones(len(report), bool),
                       a=0.0, worst_rule="worst3", label="good", u=0.0, n_fixed=1.0, n_draws=50, seed=1)
    assert r1.metrics["he"] == pytest.approx(0.0, abs=1e-9)
    # climatology price 0.50 every day (fee ceil(0.07*0.25*100 = 1.75) = 2c): per day 0.52
    clim = lambda d: np.full(len(d), 0.50)  # noqa: E731
    rc = evaluate_lead(train, report, clim(train), clim(report), np.ones(len(train), bool), np.ones(len(report), bool),
                       a=0.0, worst_rule="worst3", label="clim", u=0.0, n_fixed=1.0, n_draws=50, seed=1)
    # REPORT n=1: 2012 net = 4 - 4 + 4*0.52 = 2.08; 2011 net = 0 - 0 + 2.08 = 2.08
    # SV(hedged) = (0.08^2 + 0.08^2)/2 = 0.0064 ; SV(unhedged) = 2 -> HE = 1 - 0.0032
    assert rc.metrics["he"] == pytest.approx(1 - 0.0064 / 2)
    assert rc.metrics["mean_net_cost"] == pytest.approx(2.08)
    # the same number by hand through the metric function
    assert hedge_effectiveness(np.array([2.08, 2.08]), np.array([0.0, 4.0]), 2.0) == pytest.approx(1 - 0.0064 / 2)


def test_split_60_40():
    assert split_60_40([2004, 2005, 2006, 2007, 2008]) == ([2004, 2005, 2006], [2007, 2008])
    assert split_60_40(list(range(2004, 2027))) == (list(range(2004, 2018)), list(range(2018, 2027)))
