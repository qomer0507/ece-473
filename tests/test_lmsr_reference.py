"""Tests of the Python LMSR reference (sim/lmsr.py). No chain involved."""
import math
import random

import pytest

from sim import lmsr

N = lmsr.n_brackets()


def naive_cost(q, b):
    return b * math.log(sum(math.exp(x / b) for x in q))


def test_ladder_is_exhaustive_and_has_a_boundary_at_90():
    labels = lmsr.bracket_labels()
    assert N == 12 and len(labels) == 12
    assert labels[0] == "<80" and labels[6] == "90-91" and labels[-1] == ">=100"
    assert lmsr.strike_index() == 6
    seen = [lmsr.bracket_of(t) for t in range(-80, 141)]
    assert seen == sorted(seen) and set(seen) == set(range(12))
    assert lmsr.bracket_of(89) == 5 and lmsr.bracket_of(90) == 6
    assert lmsr.bracket_of(79) == 0 and lmsr.bracket_of(80) == 1
    assert lmsr.bracket_of(99) == 10 and lmsr.bracket_of(100) == 11
    # a basket share pays exactly when T >= 90
    for t in range(60, 121):
        assert (lmsr.bracket_of(t) >= lmsr.strike_index()) == (t >= 90)


def test_bad_ladders_are_rejected():
    with pytest.raises(ValueError):
        lmsr.strike_index([80, 85, 95], 90)
    with pytest.raises(ValueError):
        lmsr.check_bounds([80, 80])
    with pytest.raises(ValueError):
        lmsr.Market(100, [90, 80])


def test_cost_matches_the_naive_formula_where_that_is_safe():
    rng = random.Random(1)
    for _ in range(200):
        b = rng.choice([50, 200, 1000, 5000])
        q = [rng.uniform(0, 5 * b) for _ in range(N)]
        assert lmsr.cost(q, b) == pytest.approx(naive_cost(q, b), rel=1e-12)


def test_cost_is_stable_where_the_naive_formula_overflows():
    q = [0.0] * N
    q[3] = 1e9
    with pytest.raises(OverflowError):
        naive_cost(q, 1.0)
    assert lmsr.cost(q, 1.0) == pytest.approx(1e9)
    assert lmsr.prices(q, 1.0)[3] == 1.0


def test_prices_sum_to_one_and_start_uniform():
    rng = random.Random(2)
    assert lmsr.prices([0.0] * N, 200) == pytest.approx([1 / N] * N)
    for _ in range(200):
        b = rng.choice([1, 50, 200, 5000])
        q = [rng.uniform(0, 30 * b) for _ in range(N)]
        p = lmsr.prices(q, b)
        assert sum(p) == pytest.approx(1.0, abs=1e-12)
        assert all(0.0 <= x <= 1.0 for x in p)


def test_price_is_the_derivative_of_cost():
    rng = random.Random(3)
    b = 200.0
    q = [rng.uniform(0, 400) for _ in range(N)]
    p = lmsr.prices(q, b)
    for j in range(N):
        h = 1e-4
        assert lmsr.quote_buy(q, b, j, h) / h == pytest.approx(p[j], rel=1e-5)


def test_buying_raises_that_price_and_lowers_the_others():
    rng = random.Random(4)
    m = lmsr.Market(200)
    for _ in range(100):
        j = rng.randrange(N)
        before = m.prices()
        m.buy(j, rng.randint(1, 300))
        after = m.prices()
        assert after[j] > before[j]
        assert all(after[i] <= before[i] for i in range(N) if i != j)


def test_cost_is_path_independent():
    rng = random.Random(5)
    trades = [(rng.randrange(N), rng.randint(1, 500)) for _ in range(30)]
    totals = []
    for order in (trades, trades[::-1], sorted(trades)):
        m = lmsr.Market(200)
        for j, s in order:
            m.buy(j, s)
        totals.append(m.revenue)
    assert totals[1] == pytest.approx(totals[0], rel=1e-12)
    assert totals[2] == pytest.approx(totals[0], rel=1e-12)


def test_basket_equals_sequential_single_buys():
    for b in (50, 200, 1000, 5000):
        for size in (10, 100, 1000):
            a, c = lmsr.Market(b), lmsr.Market(b)
            paid = a.buy_basket(size)
            seq = sum(c.buy(j, size) for j in range(c.k, c.n))
            assert paid == pytest.approx(seq, rel=1e-12)
            assert a.q == c.q
            assert paid == pytest.approx(lmsr.quote_basket([0.0] * N, b, size), rel=1e-12)


def test_basket_average_price_is_between_pre_and_post_trade_price():
    for b in (50, 200, 1000, 5000):
        for size in (10, 100, 1000):
            m = lmsr.Market(b)
            pre = m.price_at_or_above()
            avg = m.buy_basket(size) / size
            assert pre < avg < m.price_at_or_above() <= 1.0


def test_buying_every_bracket_costs_exactly_one_per_unit():
    m = lmsr.Market(200)
    m.buy(3, 77)
    assert lmsr.quote_range(m.q, m.b, 0, N - 1, 50) == pytest.approx(50.0, rel=1e-12)


def test_sponsor_loss_never_exceeds_b_ln_n_over_random_sequences():
    rng = random.Random(473)
    worst_share = 0.0
    for _ in range(2000):
        b = rng.choice([1, 50, 200, 1000, 5000])
        m = lmsr.Market(b)
        bound = lmsr.worst_case_loss(b, N)
        assert m.funding == pytest.approx(bound)
        for _ in range(rng.randint(1, 30)):
            size = 1 + int(rng.random() ** 3 * 20 * b)
            if rng.random() < 0.25:
                m.buy_basket(size)
            else:
                m.buy(rng.randrange(N), size)
            assert m.worst_pnl() >= -bound * (1 + 1e-12)
        worst_share = max(worst_share, -m.worst_pnl() / bound)
    assert 0.9 < worst_share <= 1.0 + 1e-12


def test_seed_reproduces_the_prior_and_its_worst_case_loss():
    prior = [0.30, 0.10, 0.08, 0.10, 0.10, 0.08, 0.08, 0.06, 0.04, 0.03, 0.02, 0.01]
    b = 1000.0
    exact = lmsr.seed_from_prior(prior, b, integer=False)
    assert min(exact) == 0.0
    assert lmsr.prices(exact, b) == pytest.approx(prior, rel=1e-12)
    assert lmsr.seeded_worst_case_loss(exact, b) == pytest.approx(b * math.log(1 / min(prior)), rel=1e-12)
    whole = lmsr.seed_from_prior(prior, b)
    assert all(x == int(x) for x in whole)
    assert lmsr.prices(whole, b) == pytest.approx(prior, rel=2e-3)
    # a non-uniform start always needs more funding than a uniform one
    assert lmsr.seeded_worst_case_loss(exact, b) > lmsr.worst_case_loss(b, N)
    with pytest.raises(ValueError):
        lmsr.seed_from_prior([0.5, 0.5, 0.0], b)


def test_seeded_sponsor_loss_never_exceeds_its_bound():
    rng = random.Random(7)
    for _ in range(500):
        b = rng.choice([50, 200, 1000])
        raw = [rng.random() + 0.01 for _ in range(N)]
        prior = [x / sum(raw) for x in raw]
        m = lmsr.Market(b, q0=lmsr.seed_from_prior(prior, b))
        for _ in range(rng.randint(1, 20)):
            m.buy(rng.randrange(N), 1 + int(rng.random() ** 2 * 15 * b))
            assert m.worst_pnl() >= -m.funding * (1 + 1e-12)


def test_move_to_reaches_the_target_prices_with_buys_only():
    m = lmsr.Market(200)
    m.buy(2, 50)
    before = list(m.q)
    target = [0.02, 0.03, 0.05, 0.10, 0.20, 0.25, 0.15, 0.10, 0.05, 0.03, 0.01, 0.01]
    paid = m.move_to(target)
    assert paid > 0
    assert m.prices() == pytest.approx(target, rel=1e-9)
    assert all(a >= c for a, c in zip(m.q, before))


def test_exact_wei_cost_agrees_with_the_float_cost():
    rng = random.Random(8)
    unit = 10 ** 12
    for _ in range(100):
        b = rng.choice([50, 200, 1000, 5000])
        q = [rng.randrange(0, 20 * b) for _ in range(N)]
        assert lmsr.cost_wei(q, b, unit) == pytest.approx(lmsr.cost(q, b) * unit, rel=1e-12)
    assert lmsr.cost_wei([0] * N, 200, unit) == int(200 * math.log(12) * unit)
    # telescoping: a basket quote equals the six single quotes in sequence, exactly
    q = [0] * N
    seq = 0
    for j in range(6, 12):
        seq += lmsr.quote_wei(q, 200, unit, j, j, 100)
        q[j] += 100
    assert seq == lmsr.quote_wei([0] * N, 200, unit, 6, 11, 100)
    assert sum(lmsr.prices_1e18(q, 200)) == pytest.approx(10 ** 18, abs=N)


def test_climatology_helpers():
    counts = lmsr.bracket_counts([70, 79, 80, 89, 90, 90, 101])
    assert counts == [2, 1, 0, 0, 0, 1, 2, 0, 0, 0, 0, 1]
    prior = lmsr.prior_from_counts(counts)
    assert sum(prior) == pytest.approx(1.0)
    assert min(prior) == pytest.approx(1 / (7 + 12))
