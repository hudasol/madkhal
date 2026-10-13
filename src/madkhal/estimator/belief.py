"""Summaries of the filter output as contract models (median and 90 percent interval)."""

from __future__ import annotations

import datetime as dt
from collections.abc import Sequence
from dataclasses import dataclass

import numpy as np

from madkhal.contract import (
    BeliefParameter,
    BloomBelief,
    CoverageState,
    EvidenceDay,
    HorizonProbability,
    Interval,
    ParamSource,
)

from .filter import HORIZONS, FilterResult, run_filter
from .params import Draws

LEVEL = 0.9
Q_LO, Q_HI = 0.05, 0.95


def interval_of(x: np.ndarray, level: float = LEVEL) -> Interval:
    lo, med, hi = np.quantile(x, [(1 - level) / 2, 0.5, 1 - (1 - level) / 2])
    return Interval(median=float(med), lo=float(lo), hi=float(hi), level=level)


@dataclass(frozen=True)
class BeliefSeries:
    """Per day summaries for one site: arrays of shape (T,) unless noted."""

    site: str
    dates: list[dt.date]
    clear_obs: np.ndarray
    alert: np.ndarray
    staleness: np.ndarray
    quantiles: dict[str, np.ndarray]  # name -> (T, 3) with columns lo, median, hi
    result: FilterResult
    draws: Draws

    def index_of(self, day: dt.date) -> int:
        i = (day - self.dates[0]).days
        if not 0 <= i < len(self.dates):
            raise IndexError(f"{day} outside {self.dates[0]} to {self.dates[-1]}")
        return i

    def to_belief(self, i: int) -> BloomBelief:
        def iv(name: str) -> Interval:
            lo, med, hi = self.quantiles[name][i]
            return Interval(median=float(med), lo=float(lo), hi=float(hi), level=LEVEL)

        stale = int(self.staleness[i])
        return BloomBelief(
            site=self.site,
            date=self.dates[i],
            p_clear=iv("clear"),
            p_developing=iv("developing"),
            p_at_intake=iv("at_intake"),
            p_any_bloom=iv("any_bloom"),
            within=[
                HorizonProbability(horizon_days=h, p_at_intake=iv(f"within_{h}"))
                for h in self.result.horizons
            ],
            staleness_days=stale if stale >= 0 else None,
            observation=CoverageState.clear if self.clear_obs[i] else CoverageState.nodata,
            alert=bool(self.alert[i]),
            n_draws=self.draws.n,
            seed=self.draws.seed,
            parameters=belief_parameters(self.draws),
        )


def summarise(
    site: str,
    dates: Sequence[dt.date],
    clear: np.ndarray,
    alert: np.ndarray,
    res: FilterResult,
    dr: Draws,
) -> BeliefSeries:
    marg = res.marginals()
    named = dict(marg)
    for j, h in enumerate(res.horizons):
        named[f"within_{h}"] = res.within[j]
    quant = {k: np.quantile(v, [Q_LO, 0.5, Q_HI], axis=1).T.copy() for k, v in named.items()}
    return BeliefSeries(
        site=site,
        dates=list(dates),
        clear_obs=np.asarray(clear, dtype=bool),
        alert=np.asarray(alert, dtype=bool),
        staleness=res.staleness,
        quantiles=quant,
        result=res,
        draws=dr,
    )


def belief_series(
    site: str, days: Sequence[EvidenceDay], dr: Draws, horizons: Sequence[int] = HORIZONS
) -> BeliefSeries:
    """Run the filter over a site's evidence days (consecutive, oldest first)."""
    if not days:
        raise ValueError("no evidence days")
    for a, b in zip(days, days[1:], strict=False):
        if b.date != a.date + dt.timedelta(days=1):
            raise ValueError(f"evidence days must be consecutive: {a.date} then {b.date}")
    clear = np.array([d.coverage == CoverageState.clear for d in days])
    alert = np.array([d.alert for d in days])
    doy = [d.date.timetuple().tm_yday for d in days]
    res = run_filter(clear, alert, doy, dr, horizons)
    return summarise(site, [d.date for d in days], clear, alert, res, dr)


def belief_parameters(dr: Draws) -> list[BeliefParameter]:
    s = dr.spec
    a_a, a_b = s.alpha_beta_params()
    h_a, h_b = s.hit_beta_params()
    v_a, v_b = s.vis_beta_params()
    rows = [
        (
            "alpha",
            "False alarm rate per clear day",
            dr.alpha,
            ParamSource.nadhir,
            f"{s.alpha_alert_days} alert days of {s.alpha_clear_days} clear held out quiet days in "
            f"{s.alpha_episodes} episodes; Beta({a_a:.2f}, {a_b:.2f}) after a Jeffreys prior and a "
            "cluster correction (alert days counted per episode)",
        ),
        (
            "hit_rate",
            "Share of blooms the detector can see (event level)",
            dr.hit,
            ParamSource.nadhir,
            f"{s.hit_k} detected of {s.hit_n} observable dated events; Beta({h_a:.2f}, {h_b:.2f}). "
            "Wide because n is tiny.",
        ),
        (
            "blind_spot",
            "Extra share of blooms invisible to a broadband detector",
            dr.blind,
            ParamSource.assumption,
            f"ASSUMPTION: Beta({s.blind_spot_a:g}, {s.blind_spot_b:g}), motivated by the one "
            "documented species level miss (Al Raha 2023)",
        ),
        (
            "visible_share",
            "Share of blooms visible to the detector",
            dr.visible_share,
            ParamSource.assumption,
            "hit_rate times (1 minus blind_spot)",
        ),
        (
            "beta_at",
            "Alert rate per clear day, visible bloom at the intake",
            dr.beta_at,
            ParamSource.nadhir,
            f"{s.vis_alert_k} alert days of {s.vis_alert_n} clear days in the one detected episode "
            f"(n = 1 event), weighted as {s.vis_pseudo_count:g} pseudo observations: "
            f"Beta({v_a:.2f}, {v_b:.2f})",
        ),
        (
            "beta_dev",
            "Alert rate per clear day, visible bloom still developing",
            dr.beta_dev,
            ParamSource.assumption,
            f"ASSUMPTION: beta_at times U({s.dev_alert_ratio_lo:g}, {s.dev_alert_ratio_hi:g})",
        ),
        (
            "onset_rate",
            "Bloom onsets per year in the watch zone",
            dr.onset_rate,
            ParamSource.assumption,
            f"ASSUMPTION: lognormal, median {s.onset_rate_per_year:g} per year, sigma {s.onset_sigma:g}; "
            "seasonal peaks mid September and early February",
        ),
        (
            "p_dev_to_at",
            "Daily chance a developing bloom reaches the intake",
            dr.p_da,
            ParamSource.assumption,
            f"ASSUMPTION: median {s.p_dev_to_at:g}; the only anchor is the Kalba 2018 lead time "
            "range of minus 6 to plus 8 days (n = 1)",
        ),
        (
            "p_dev_to_clear",
            "Daily chance a developing bloom fades before the intake",
            dr.p_dc,
            ParamSource.assumption,
            f"ASSUMPTION: median {s.p_dev_to_clear:g}",
        ),
        (
            "p_at_to_clear",
            "Daily chance a bloom at the intake clears",
            dr.p_ac,
            ParamSource.assumption,
            f"ASSUMPTION: median {s.p_at_to_clear:.3f} (mean stay about 14 days)",
        ),
    ]
    return [
        BeliefParameter(key=k, label=lab, value=interval_of(x), source=src, provenance=prov)
        for k, lab, x, src, prov in rows
    ]
