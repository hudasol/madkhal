from __future__ import annotations

import math

import numpy as np
import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from madkhal.estimator import (
    AT_I,
    AT_V,
    CLEAR,
    DEV_I,
    DEV_V,
    HORIZONS,
    Draws,
    PriorSpec,
    alert_means_bloom,
    belief_parameters,
    burn_in,
    draw_parameters,
    persistence,
    propagate,
    run_filter,
    season_shape,
    seasonal_prior,
    update,
)
from madkhal.estimator.sensitivity import blind_spot_runs

SPEC = PriorSpec(site="test", alpha_alert_days=19, alpha_clear_days=426, alpha_episodes=5)
DR = draw_parameters(SPEC, 60, 11)


@st.composite
def histories(
    draw: st.DrawFn, min_len: int = 2, max_len: int = 30
) -> tuple[list[bool], list[bool], list[int]]:
    n = draw(st.integers(min_len, max_len))
    clear = draw(st.lists(st.booleans(), min_size=n, max_size=n))
    alert_raw = draw(st.lists(st.booleans(), min_size=n, max_size=n))
    alert = [c and a for c, a in zip(clear, alert_raw, strict=True)]
    start = draw(st.integers(1, 365))
    doy = [(start - 1 + k) % 365 + 1 for k in range(n)]
    return clear, alert, doy


# ---------------------------------------------------------------- structure
@pytest.mark.req("MK-L2-001")
def test_three_reported_states_sum_to_one() -> None:
    res = run_filter([True, False, True], [False, False, True], [100, 101, 102], DR)
    m = res.marginals()
    total = m["clear"] + m["developing"] + m["at_intake"]
    assert np.allclose(total, 1.0)
    assert res.posterior.shape == (3, DR.n, 5)


@pytest.mark.req("MK-L2-002")
def test_season_has_late_summer_and_winter_peaks() -> None:
    shape = season_shape(np.array([258, 32, 135]), SPEC)  # mid September, 1 February, mid May
    assert shape[0] > shape[2] and shape[1] > shape[2]
    days = season_shape(np.arange(1, 366), SPEC)
    assert math.isclose(float(days.mean()), 1.0, rel_tol=1e-9)


@pytest.mark.req("MK-L2-002")
def test_transition_parameters_are_labelled_assumptions() -> None:
    rows = {p.key: p for p in belief_parameters(DR)}
    for key in ("onset_rate", "p_dev_to_at", "p_dev_to_clear", "p_at_to_clear", "blind_spot"):
        assert rows[key].source.value == "assumption"
        assert rows[key].provenance.startswith("ASSUMPTION")


# ---------------------------------------------------------------- nodata
@pytest.mark.req("MK-L2-003")
@settings(max_examples=40, deadline=None)
@given(histories())
def test_nodata_day_equals_prior_propagation(h: tuple[list[bool], list[bool], list[int]]) -> None:
    clear, alert, doy = h
    clear[-1] = alert[-1] = False
    res = run_filter(clear, alert, doy, DR)
    before = res.posterior[-2]
    assert np.array_equal(res.posterior[-1], propagate(before, doy[-1], DR))
    assert update(before, False, False, DR) is before


@pytest.mark.req("MK-L2-008")
def test_no_data_belief_equals_seasonal_prior() -> None:
    doy = [(200 + k) % 365 + 1 for k in range(400)]
    res = run_filter([False] * 400, [False] * 400, doy, DR)
    prior = seasonal_prior(doy, DR)
    assert np.array_equal(res.posterior, prior.posterior)
    # and it is the pure propagation of the burn in belief
    b = burn_in(doy[0], DR)
    for t, d in enumerate(doy):
        b = propagate(b, d, DR)
        assert np.allclose(res.posterior[t], b)


@pytest.mark.req("MK-L2-009")
@settings(max_examples=60, deadline=None)
@given(histories(min_len=3))
def test_nodata_never_moves_belief_away_from_seasonal_prior(
    h: tuple[list[bool], list[bool], list[int]],
) -> None:
    clear, alert, doy = h
    clear[-1] = alert[-1] = False
    res = run_filter(clear, alert, doy, DR)
    prior = seasonal_prior(doy, DR)
    tv_before = 0.5 * np.abs(res.posterior[-2] - prior.posterior[-2]).sum(axis=1)
    tv_after = 0.5 * np.abs(res.posterior[-1] - prior.posterior[-1]).sum(axis=1)
    assert np.all(tv_after <= tv_before + 1e-12)


@pytest.mark.req("MK-L2-009")
def test_literal_interval_reading_does_not_hold_documented() -> None:
    """Documents D-008: a quiet clear day can give a wider interval than a nodata day,
    because draws that assume different detector visibility react differently."""
    rng = np.random.default_rng(1)

    def width(res_post: np.ndarray) -> float:
        lo, hi = np.quantile(1.0 - res_post[:, CLEAR], [0.05, 0.95])
        return float(hi - lo)

    found = False
    for _ in range(200):
        n = 20
        clear = list(rng.random(n) < 0.5)
        alert = [c and a for c, a in zip(clear, rng.random(n) < 0.3, strict=True)]
        doy = [(150 + k) % 365 + 1 for k in range(n)]
        c_nd = clear[:-1] + [False]
        c_q = clear[:-1] + [True]
        a_x = alert[:-1] + [False]
        w_nd = width(run_filter(c_nd, a_x, doy, DR).posterior[-1])
        w_q = width(run_filter(c_q, a_x, doy, DR).posterior[-1])
        if w_q > w_nd + 1e-9:
            found = True
            break
    assert found


# ---------------------------------------------------------------- alerts
@pytest.mark.req("MK-L2-010")
@settings(max_examples=80, deadline=None)
@given(histories())
def test_alert_never_lowers_p_any_bloom_on_the_day(
    h: tuple[list[bool], list[bool], list[int]],
) -> None:
    clear, alert, doy = h
    clear[-1] = True
    quiet = run_filter(clear, alert[:-1] + [False], doy, DR)
    alarm = run_filter(clear, alert[:-1] + [True], doy, DR)
    p_q = 1.0 - quiet.posterior[-1][:, CLEAR]
    p_a = 1.0 - alarm.posterior[-1][:, CLEAR]
    assert np.all(p_a >= p_q - 1e-12)
    assert np.median(p_a) >= np.median(p_q) - 1e-12


@pytest.mark.req("MK-L2-010")
@settings(max_examples=40, deadline=None)
@given(histories(), st.integers(0, 29))
def test_more_alerts_never_lower_p_any_on_the_latest_day(
    h: tuple[list[bool], list[bool], list[int]], k: int
) -> None:
    clear, alert, doy = h
    t = k % len(doy)
    clear[t] = True
    more = list(alert)
    more[t] = True
    if more == alert:
        return
    # compare at day t, the day the extra alert arrives
    base = run_filter(clear[: t + 1], alert[: t + 1], doy[: t + 1], DR)
    extra = run_filter(clear[: t + 1], more[: t + 1], doy[: t + 1], DR)
    assert np.all(1.0 - extra.posterior[-1][:, CLEAR] >= 1.0 - base.posterior[-1][:, CLEAR] - 1e-12)


@pytest.mark.req("MK-L2-010")
def test_later_day_effect_of_an_alert_is_documented() -> None:
    """Documents D-009: an alert followed by quiet clear days can leave a lower P(any bloom)
    than no alert, because the alert marks the bloom as visible and quiet days refute it."""
    rng = np.random.default_rng(1)
    found = False
    for _ in range(200):
        n = 20
        clear = list(rng.random(n) < 0.6)
        alert = [c and a for c, a in zip(clear, rng.random(n) < 0.3, strict=True)]
        doy = [(240 + k) % 365 + 1 for k in range(n)]
        t = 5
        clear[t] = True
        base = alert[:t] + [False] + alert[t + 1 :]
        extra = alert[:t] + [True] + alert[t + 1 :]
        p_base = np.median(1.0 - run_filter(clear, base, doy, DR).posterior[:, :, CLEAR], axis=1)
        p_extra = np.median(1.0 - run_filter(clear, extra, doy, DR).posterior[:, :, CLEAR], axis=1)
        assert p_extra[t] >= p_base[t] - 1e-12  # on the day itself it never falls
        if (p_extra[t + 1 :] < p_base[t + 1 :] - 1e-6).any():
            found = True
            break
    assert found


# ---------------------------------------------------------------- posteriors
@pytest.mark.req("MK-L2-004")
def test_alpha_posterior_uses_jeffreys_prior_and_counts() -> None:
    no_cluster = PriorSpec(
        site="t",
        alpha_alert_days=19,
        alpha_clear_days=426,
        alpha_episodes=5,
        cluster_correction=False,
    )
    assert no_cluster.alpha_beta_params() == (19.5, 407.5)
    a, b = SPEC.alpha_beta_params()  # 5 episodes of 3.8 days: effective 5 of 112.1 days
    assert math.isclose(a, 5.5) and math.isclose(b, 0.5 + 426 / 3.8 - 5)
    dr = draw_parameters(SPEC, 4000, 1)
    assert math.isclose(float(dr.alpha.mean()), a / (a + b), rel_tol=0.03)


@pytest.mark.req("MK-L2-005")
def test_hit_rate_posterior_is_wide() -> None:
    assert SPEC.hit_beta_params() == (1.5, 2.5)
    dr = draw_parameters(SPEC, 4000, 1)
    lo, hi = np.quantile(dr.hit, [0.05, 0.95])
    assert lo < 0.1 and hi > 0.7  # one detection of three keeps it wide
    assert np.all(dr.visible_share <= dr.hit + 1e-12)


@pytest.mark.req("MK-L2-005")
def test_blind_spot_sensitivity_run() -> None:
    n = 120
    doy = [(1 + k) % 365 + 1 for k in range(n)]
    clear = [k % 2 == 0 for k in range(n)]
    alert = [False] * n
    rows = blind_spot_runs(SPEC, clear, alert, doy, n_draws=200, seed=3)
    assert [r["setting"] for r in rows][0] == "none"
    quiet = [float(r["mean_p_any_quiet_days"]) for r in rows]
    # a larger invisible share means quiet days rule out less: belief stays higher
    assert quiet[0] < quiet[1] < quiet[2]


@pytest.mark.req("MK-L2-006")
def test_horizon_outputs_and_default_draw_count() -> None:
    dr = draw_parameters(SPEC, seed=5)
    assert dr.n >= 400
    res = run_filter(
        [True, False, True, True], [False, False, True, True], [250, 251, 252, 253], dr
    )
    assert res.horizons == HORIZONS == (1, 3, 7)
    w1, w3, w7 = res.within
    assert np.all(w1 <= w3 + 1e-12) and np.all(w3 <= w7 + 1e-12)
    at_now = res.posterior[:, :, AT_V] + res.posterior[:, :, AT_I]
    assert np.all(w1 >= at_now - 1e-12)
    assert list(res.staleness) == [0, 1, 0, 0]


@pytest.mark.req("MK-L2-006")
def test_staleness_is_absent_before_any_clear_day() -> None:
    res = run_filter([False, False, True, False], [False] * 4, [10, 11, 12, 13], DR)
    assert list(res.staleness) == [-1, -1, 0, 1]


@pytest.mark.req("MK-L2-007")
def test_baselines() -> None:
    alert = [False, True, False, False, False, False, False, False, False]
    assert list(alert_means_bloom(alert)) == [0, 1, 0, 0, 0, 0, 0, 0, 0]
    assert list(persistence(alert, 7)) == [0, 1, 1, 1, 1, 1, 1, 1, 0]
    with pytest.raises(ValueError):
        persistence(alert, 0)


# ---------------------------------------------------------------- worked example
def _single_draw() -> Draws:
    one = np.array
    return Draws(
        spec=SPEC,
        seed=0,
        alpha=one([0.05]),
        hit=one([0.5]),
        blind=one([0.2]),
        visible_share=one([0.4]),
        beta_at=one([0.8]),
        beta_dev=one([0.6]),
        onset_rate=one([1.0]),
        p_da=one([0.2]),
        p_dc=one([0.1]),
        p_ac=one([0.05]),
    )


@pytest.mark.req("MK-L2-011")
def test_worked_example_by_hand() -> None:
    dr = _single_draw()
    doy1, doy2 = 258, 259
    lam1 = 1 - math.exp(-1.0 * float(season_shape(np.array([doy1]), SPEC)[0]) / 365)
    lam2 = 1 - math.exp(-1.0 * float(season_shape(np.array([doy2]), SPEC)[0]) / 365)
    v = 0.4
    # day 1: start all clear, propagate, observe a quiet clear day
    p = [1 - lam1, lam1 * v, lam1 * (1 - v), 0.0, 0.0]
    lik_quiet = [0.95, 0.4, 0.95, 0.2, 0.95]
    q = [p[i] * lik_quiet[i] for i in range(5)]
    z = sum(q)
    b1 = [x / z for x in q]
    # day 2: propagate by hand, observe an alert
    c, dv, di, av, ai = b1
    p2 = [
        c * (1 - lam2) + (dv + di) * 0.1 + (av + ai) * 0.05,
        c * lam2 * v + dv * (1 - 0.2 - 0.1),
        c * lam2 * (1 - v) + di * (1 - 0.2 - 0.1),
        dv * 0.2 + av * (1 - 0.05),
        di * 0.2 + ai * (1 - 0.05),
    ]
    lik_alert = [0.05, 0.6, 0.05, 0.8, 0.05]
    q2 = [p2[i] * lik_alert[i] for i in range(5)]
    z2 = sum(q2)
    b2 = [x / z2 for x in q2]
    init = np.array([[1.0, 0, 0, 0, 0]])
    res = run_filter([True, True], [False, True], [doy1, doy2], dr, horizons=(1,), init=init)
    assert np.allclose(res.posterior[0, 0], b1, atol=1e-12)
    assert np.allclose(res.posterior[1, 0], b2, atol=1e-12)
    # P(at the intake within 1 day) on day 2, by hand
    lam3 = 1 - math.exp(-1.0 * float(season_shape(np.array([260]), SPEC)[0]) / 365)
    assert lam3 > 0
    at_now = b2[AT_V] + b2[AT_I]
    enter = b2[DEV_V] * 0.2 + b2[DEV_I] * 0.2
    assert math.isclose(float(res.within[0, 1, 0]), at_now + enter, rel_tol=1e-12)
    assert b2[CLEAR] < b1[CLEAR]


# ---------------------------------------------------------------- determinism and lead time
@pytest.mark.req("MK-X-004")
def test_same_seed_same_belief() -> None:
    a = draw_parameters(SPEC, 100, 9)
    b = draw_parameters(SPEC, 100, 9)
    ra = run_filter([True, False, True], [True, False, False], [5, 6, 7], a)
    rb = run_filter([True, False, True], [True, False, False], [5, 6, 7], b)
    assert np.array_equal(ra.posterior, rb.posterior)
    assert not np.array_equal(draw_parameters(SPEC, 100, 10).alpha, a.alpha)


@pytest.mark.req("MK-L2-012")
def test_lead_time_anchor_is_labelled_n_equals_one() -> None:
    rows = {p.key: p for p in belief_parameters(DR)}
    prov = rows["p_dev_to_at"].provenance
    assert "n = 1" in prov and "minus 6 to plus 8" in prov
