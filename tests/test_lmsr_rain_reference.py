"""Tests of the count-bucket part of the Python LMSR reference (sim/lmsr.py). No chain involved."""
import math
import random
from decimal import Decimal

import pytest

from sim import lmsr

N = lmsr.N_COUNT_BUCKETS
EDGES = lmsr.EXAMPLE_EDGES


def naive_cost(q, b):
    return b * math.log(sum(math.exp(x / b) for x in q))


def test_buckets_cover_every_count_once_with_inclusive_upper_edges():
    assert N == 6 and lmsr.count_bucket_labels() == ["0-2", "3-4", "5-6", "7-8", "9-10", "11+"]
    want = {0: 0, 2: 0, 3: 1, 4: 1, 5: 2, 6: 2, 7: 3, 8: 3, 9: 4, 10: 4, 11: 5, 102: 5}
    for count, bucket in want.items():
        assert lmsr.count_bucket_of(count) == bucket
    seen = [lmsr.count_bucket_of(c) for c in range(0, 110)]
    assert seen == sorted(seen) and set(seen) == set(range(6))
    assert lmsr.count_bucket_labels([0, 1, 3, 7, 20]) == ["0", "1", "2-3", "4-7", "8-20", "21+"]
    with pytest.raises(ValueError):
        lmsr.count_bucket_of(-1)


def test_bad_edges_are_rejected_like_in_the_contract():
    for bad in ([2, 4, 6, 8], [2, 4, 6, 8, 10, 12], [2, 2, 6, 8, 10], [2, 4, 6, 10, 8], [-1, 4, 6, 8, 10]):
        with pytest.raises(ValueError):
            lmsr.check_edges(bad)
    with pytest.raises(ValueError):
        lmsr.check_edges([2, 4, 6, 8, 102], season_days=102)
    lmsr.check_edges([2, 4, 6, 8, 101], season_days=102)


def test_vector_quote_matches_the_naive_formula_and_the_sum_of_its_legs():
    rng = random.Random(3)
    for _ in range(200):
        b = rng.choice([50, 200, 1000, 5000])
        q = [rng.uniform(0, 3 * b) for _ in range(N)]
        a = [rng.choice([0, rng.uniform(0, 2 * b)]) for _ in range(N)]
        direct = lmsr.quote_vector(q, b, a)
        assert direct == pytest.approx(naive_cost([x + y for x, y in zip(q, a)], b) - naive_cost(q, b), rel=1e-9, abs=1e-9)
        # buying the legs one after the other costs the same (path independence)
        total, state = 0.0, list(q)
        for j in rng.sample(range(N), N):
            total += lmsr.quote_buy(state, b, j, a[j])
            state[j] += a[j]
        assert total == pytest.approx(direct, rel=1e-9, abs=1e-9)


def test_vector_quote_in_wei_is_exactly_additive_over_legs():
    rng = random.Random(4)
    for _ in range(100):
        b, unit = rng.choice([(50, 10**12), (200, 10**12), (7, 10**9), (100, 10**14)])
        q = [rng.randrange(0, 3 * b) for _ in range(N)]
        a = [rng.choice([0, 1, rng.randrange(1, 4 * b)]) for _ in range(N)]
        total, state = 0, list(q)
        for j in range(N):
            leg = [0] * N
            leg[j] = a[j]
            total += lmsr.quote_vector_wei(state, b, unit, leg)
            state[j] += a[j]
        assert total == lmsr.quote_vector_wei(q, b, unit, a)


def test_vector_quote_rejects_wrong_length_and_negative_amounts():
    with pytest.raises(ValueError):
        lmsr.quote_vector([0.0] * 6, 100, [1, 2, 3])
    with pytest.raises(ValueError):
        lmsr.quote_vector([0.0] * 6, 100, [1, 0, 0, 0, 0, -1])
    with pytest.raises(ValueError):
        lmsr.quote_vector_wei([0] * 6, 100, 10**12, [1, 0, 0, 0, 0, -1])


def test_funding_is_b_ln6_and_the_safe_amount_is_slightly_more():
    ln6 = Decimal(6).ln()
    for b, unit in [(50, 10**12), (100, 10**14), (1, 10**9), (10**12, 10**18)]:
        need = lmsr.required_funding_wei(b, unit)
        assert need == int(ln6 * b * unit)  # floor
        assert need < lmsr.safe_funding_wei(b, unit) <= need + b * unit // 2**56 + 2
    assert lmsr.required_funding_wei(100, 10**14) == 17917594692280550  # the review's example
    assert lmsr.worst_case_loss(200, 6) == pytest.approx(200 * math.log(6))


def test_stepped_vector_and_payout_for_every_count():
    v = lmsr.stepped_vector()
    assert v == [0, 0, 0, 1, 2, 3]
    assert lmsr.stepped_vector(4) == [0, 0, 0, 0, 1, 2] and lmsr.stepped_vector(0) == [1, 2, 3, 4, 5, 6]
    with pytest.raises(ValueError):
        lmsr.stepped_vector(6)
    for count in range(0, 103):
        want = 0 if count <= 6 else 1 if count <= 8 else 2 if count <= 10 else 3
        assert lmsr.payout(v, count) == want
    probs = [0.1, 0.2, 0.3, 0.2, 0.1, 0.1]
    assert lmsr.expected_payout(v, probs) == pytest.approx(0.2 + 0.2 + 0.3)


def test_count_market_uniform_start_closed_form_and_loss_bound():
    for b in (50, 200, 1000):
        m = lmsr.CountMarket(b)
        assert m.prices() == pytest.approx([1 / 6] * 6)
        assert m.funding == pytest.approx(b * math.log(6))
        s = 100
        paid = m.buy_vector([0, 0, 0, s, 2 * s, 3 * s])
        closed = b * math.log((3 + math.exp(s / b) + math.exp(2 * s / b) + math.exp(3 * s / b)) / 6)
        assert paid == pytest.approx(closed, rel=1e-12)
        assert m.revenue == pytest.approx(paid)
        assert m.sponsor_pnl(0) == pytest.approx(paid)             # nothing to pay
        assert m.sponsor_pnl(12) == pytest.approx(paid - 3 * s)    # top bucket wins
        assert m.worst_pnl() >= -m.funding * (1 + 1e-12)


def test_loss_bound_holds_for_random_vector_trades():
    rng = random.Random(5)
    for _ in range(300):
        b = rng.choice([1, 5, 50, 200, 1000])
        m = lmsr.CountMarket(b)
        for _ in range(rng.randint(1, 25)):
            m.buy_vector([rng.choice([0, rng.uniform(0, 60 * b) * rng.random() ** 3]) for _ in range(6)])
            assert m.worst_pnl() >= -m.funding * (1 + 1e-9) - 1e-9


def test_move_to_reaches_the_target_prices_by_buying_only():
    target = [0.24, 0.18, 0.29, 0.13, 0.03, 0.13]
    m = lmsr.CountMarket(200)
    before = list(m.q)
    paid = m.move_to(target)
    assert paid > 0 and all(a >= b0 for a, b0 in zip(m.q, before))
    assert m.prices() == pytest.approx(target, rel=1e-9)
    assert min(m.q) == pytest.approx(0.0, abs=1e-9)  # the smallest possible buy
    with pytest.raises(ValueError):
        m.move_to([0.5, 0.5, 0, 0, 0, 0])


def test_placeholder_distribution_is_a_distribution_with_the_stated_mean():
    pmf = lmsr.placeholder_count_pmf()
    assert len(pmf) == 103 and sum(pmf) == pytest.approx(1.0)
    assert sum(k * p for k, p in enumerate(pmf)) == pytest.approx(5.3, rel=1e-6)
    probs = lmsr.bucket_probs_from_pmf(pmf)
    assert sum(probs) == pytest.approx(1.0) and min(probs) > 0


def test_bucket_probs_from_counts_and_csv_reader(tmp_path):
    probs = lmsr.bucket_probs_from_counts([2, 6, 6, 4, 12], alpha=0.5)
    assert probs == pytest.approx([1.5 / 8, 1.5 / 8, 2.5 / 8, 0.5 / 8, 0.5 / 8, 1.5 / 8])
    f = tmp_path / "season_counts_XXX.csv"
    f.write_text(
        "station,season,calendar,days,loss_days,season_usable\n"
        "XXX,1998,all_days,109,4,False\n"
        "XXX,1999,all_days,102,2,True\n"
        "XXX,1999,weekend_holiday,32,1,True\n"
        "XXX,2000,all_days,102,6,True\n"
        "XXX,2015,all_days,109,9,True\n")
    rows = lmsr.read_season_counts(str(f), range(1998, 2015))
    assert rows == [{"season": 1999, "loss_days": 2, "days": 102}, {"season": 2000, "loss_days": 6, "days": 102}]
    assert [r["loss_days"] for r in lmsr.read_season_counts(str(f))] == [2, 6, 9]
    assert [r["loss_days"] for r in lmsr.read_season_counts(str(f), calendar="weekend_holiday")] == [1]
    bad = tmp_path / "bad.csv"
    bad.write_text("year,n\n1999,2\n")
    with pytest.raises(ValueError):
        lmsr.read_season_counts(str(bad))


def test_funding_command_line(capsys):
    lmsr._main(["funding", "--b", "100", "--unit-wei", "100000000000000"])
    out = capsys.readouterr().out
    assert "17917594692280550 wei" in out
    with pytest.raises(SystemExit):
        lmsr._main(["funding", "--b", "100", "--unit-wei", "1"])
