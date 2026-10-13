"""Estimator parameters: detector posteriors from Nadhir counts, transitions as assumptions.

Hidden states (internal): 0 clear, 1 developing and visible, 2 developing and invisible,
3 at the intake and visible, 4 at the intake and invisible. "Visible" means the broadband
detector can see the bloom; an invisible bloom (for example a species level blind spot, as
at Al Raha in April 2023) produces alerts only at the false alarm rate. The three reported
states are clear, developing (1 + 2) and at_intake (3 + 4).

Every parameter is drawn per posterior draw so that parameter uncertainty is carried into
every output. See ADR 0003 and ADR 0004.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

import numpy as np

from madkhal.core.determinism import substream

N_STATES = 5
CLEAR, DEV_V, DEV_I, AT_V, AT_I = range(N_STATES)
DEFAULT_DRAWS = 400

# Seasonal shape of the bloom onset hazard (ASSUMPTION). Peaks are placed on the two
# seasons named in Nadhir's results: late summer (the 2008 bloom began in late August and
# the Kalba 2018 report was in mid September) and the winter bloom season (the Barka
# February 2018 disruption). Magnitudes are assumptions.
SUMMER_PEAK_DOY = 258  # 15 September
WINTER_PEAK_DOY = 32  # 1 February


@dataclass(frozen=True)
class PriorSpec:
    """Counts from Nadhir and assumption settings that define the parameter priors."""

    site: str
    # Held out quiet counts (Nadhir false_alarms.csv, 50 km): alert days of clear quiet
    # days, and the number of alert episodes they form.
    alpha_alert_days: int
    alpha_clear_days: int
    alpha_episodes: int
    # Dated events: detected of observable (Nadhir event_lead_times.csv).
    hit_k: int = 1
    hit_n: int = 3
    # Alert days of clear days inside the one detected episode (n = 1 event).
    vis_alert_k: int = 6
    vis_alert_n: int = 7
    citations: dict[str, str] = field(default_factory=dict)
    # ---- assumptions (ASSUMPTION provenance, documented in docs/PARAMETERS.md)
    cluster_correction: bool = True  # deflate alert day counts by mean episode length
    vis_pseudo_count: float = 4.0  # weight of the single detected episode
    blind_spot_a: float = 1.0  # species blind spot share ~ Beta(a, b); mean 0.2
    blind_spot_b: float = 4.0
    onset_rate_per_year: float = 1.0  # median onsets per year in the watch zone
    onset_sigma: float = 0.5  # lognormal spread of the onset rate
    season_base: float = 0.3
    season_summer: float = 1.0
    season_winter: float = 0.8
    season_summer_width: float = 25.0
    season_winter_width: float = 35.0
    p_dev_to_at: float = 0.2  # daily; mean 5 days from watch zone to intake
    p_dev_to_clear: float = 0.1  # daily; a third of developing blooms never reach the intake
    p_at_to_clear: float = 1.0 / 14.0  # daily; mean 14 days at the intake
    transition_sigma: float = 0.4  # lognormal spread of the transition rates
    dev_alert_ratio_lo: float = 0.5  # developing alert rate relative to at_intake
    dev_alert_ratio_hi: float = 1.0

    def alpha_beta_params(self) -> tuple[float, float]:
        """Beta posterior (Jeffreys prior) for the daily false alarm rate alpha."""
        k, n = float(self.alpha_alert_days), float(self.alpha_clear_days)
        if self.cluster_correction and self.alpha_episodes > 0 and k > 0:
            cluster = k / self.alpha_episodes  # mean alert days per episode
            k, n = k / cluster, n / cluster
        return 0.5 + k, 0.5 + (n - k)

    def hit_beta_params(self) -> tuple[float, float]:
        """Beta posterior (Jeffreys prior) for the event level hit rate."""
        return 0.5 + self.hit_k, 0.5 + (self.hit_n - self.hit_k)

    def vis_beta_params(self) -> tuple[float, float]:
        """Beta prior for the daily alert rate of a visible bloom at the intake."""
        m = self.vis_alert_k / self.vis_alert_n
        c = self.vis_pseudo_count
        return 0.5 + c * m, 0.5 + c * (1.0 - m)


def season_shape(doy: np.ndarray, spec: PriorSpec) -> np.ndarray:
    """Relative onset hazard by day of year, normalised to mean 1 over the year."""
    days = np.arange(1, 367, dtype=float)

    def bump(d: np.ndarray, peak: float, width: float) -> np.ndarray:
        dist = np.abs(d - peak)
        dist = np.minimum(dist, 365.0 - dist)
        out: np.ndarray = np.exp(-0.5 * (dist / width) ** 2)
        return out

    def raw(d: np.ndarray) -> np.ndarray:
        out: np.ndarray = (
            spec.season_base
            + spec.season_summer * bump(d, SUMMER_PEAK_DOY, spec.season_summer_width)
            + spec.season_winter * bump(d, WINTER_PEAK_DOY, spec.season_winter_width)
        )
        return out

    norm = float(raw(days[:365]).mean())
    out: np.ndarray = raw(np.asarray(doy, dtype=float)) / norm
    return out


@dataclass(frozen=True)
class Draws:
    """Posterior parameter draws, each array has shape (D,)."""

    spec: PriorSpec
    seed: int
    alpha: np.ndarray
    hit: np.ndarray
    blind: np.ndarray
    visible_share: np.ndarray  # hit * (1 - blind)
    beta_at: np.ndarray
    beta_dev: np.ndarray
    onset_rate: np.ndarray  # per year
    p_da: np.ndarray
    p_dc: np.ndarray
    p_ac: np.ndarray

    def __post_init__(self) -> None:
        shape = season_shape(np.arange(0, 367), self.spec)  # index by day of year
        table = 1.0 - np.exp(-np.outer(shape, self.onset_rate) / 365.0)  # (367, D)
        object.__setattr__(self, "_hazard", table)

    @property
    def n(self) -> int:
        return int(self.alpha.size)

    def hazard(self, doy: int) -> np.ndarray:
        """Daily onset probability for each draw on a day of year (1 to 366)."""
        out: np.ndarray = self._hazard[doy]  # type: ignore[attr-defined]
        return out

    def subset(self, idx: np.ndarray) -> Draws:
        return Draws(
            spec=self.spec,
            seed=self.seed,
            alpha=self.alpha[idx],
            hit=self.hit[idx],
            blind=self.blind[idx],
            visible_share=self.visible_share[idx],
            beta_at=self.beta_at[idx],
            beta_dev=self.beta_dev[idx],
            onset_rate=self.onset_rate[idx],
            p_da=self.p_da[idx],
            p_dc=self.p_dc[idx],
            p_ac=self.p_ac[idx],
        )

    def posterior_mean(self) -> Draws:
        """A single draw holding the posterior means (used by generator G1)."""

        def m(x: np.ndarray) -> np.ndarray:
            return np.array([float(np.mean(x))])

        return Draws(
            spec=self.spec,
            seed=self.seed,
            alpha=m(self.alpha),
            hit=m(self.hit),
            blind=m(self.blind),
            visible_share=m(self.visible_share),
            beta_at=m(self.beta_at),
            beta_dev=m(self.beta_dev),
            onset_rate=m(self.onset_rate),
            p_da=m(self.p_da),
            p_dc=m(self.p_dc),
            p_ac=m(self.p_ac),
        )


def _lognormal(rng: np.random.Generator, median: float, sigma: float, n: int) -> np.ndarray:
    out: np.ndarray = median * np.exp(sigma * rng.standard_normal(n))
    return out


def draw_parameters(spec: PriorSpec, n_draws: int = DEFAULT_DRAWS, seed: int = 7) -> Draws:
    """Draw ``n_draws`` parameter sets. Same spec, count and seed give identical draws."""
    if n_draws < 1:
        raise ValueError("n_draws must be at least 1")
    rng = substream(seed, f"estimator.params.{spec.site}")
    a_a, a_b = spec.alpha_beta_params()
    alpha = rng.beta(a_a, a_b, n_draws)
    h_a, h_b = spec.hit_beta_params()
    hit = rng.beta(h_a, h_b, n_draws)
    blind = rng.beta(spec.blind_spot_a, spec.blind_spot_b, n_draws)
    v_a, v_b = spec.vis_beta_params()
    beta_at = rng.beta(v_a, v_b, n_draws)
    ratio = rng.uniform(spec.dev_alert_ratio_lo, spec.dev_alert_ratio_hi, n_draws)
    # An alert is never less likely under a visible bloom than under clear water.
    beta_at = np.maximum(beta_at, alpha)
    beta_dev = np.maximum(beta_at * ratio, alpha)
    onset = _lognormal(rng, spec.onset_rate_per_year, spec.onset_sigma, n_draws)
    p_da = np.clip(_lognormal(rng, spec.p_dev_to_at, spec.transition_sigma, n_draws), 1e-4, 0.6)
    p_dc = np.clip(_lognormal(rng, spec.p_dev_to_clear, spec.transition_sigma, n_draws), 1e-4, 0.35)
    p_ac = np.clip(_lognormal(rng, spec.p_at_to_clear, spec.transition_sigma, n_draws), 1e-4, 0.5)
    return Draws(
        spec=spec,
        seed=seed,
        alpha=alpha,
        hit=hit,
        blind=blind,
        visible_share=hit * (1.0 - blind),
        beta_at=beta_at,
        beta_dev=beta_dev,
        onset_rate=onset,
        p_da=p_da,
        p_dc=p_dc,
        p_ac=p_ac,
    )


def beta_mean_sd(a: float, b: float) -> tuple[float, float]:
    mean = a / (a + b)
    sd = math.sqrt(a * b / ((a + b) ** 2 * (a + b + 1.0)))
    return mean, sd
