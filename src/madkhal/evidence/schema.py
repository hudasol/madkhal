"""Expected schema of every Nadhir snapshot file (documented in ADR 0002).

The adapter compares the header of each file with these lists exactly: a missing or
an unexpected column is an error that names the file and the column.
"""

from __future__ import annotations

ZONE_DAILY = [
    "intake",
    "date",
    "n_obs",
    "n_anom",
    "max_z",
    "median_logchl",
    "month",
    "n_clim",
    "coverage",
    "observed",
    "anom_frac",
    "state",
    "radius_km",
]

EPISODES = ["first_exceed", "first_alert", "last_exceed", "closed_on", "intake", "radius_km"]

COVERAGE = [
    "intake",
    "radius_km",
    "year",
    "days",
    "observed_days",
    "observed_frac",
    "median_gap_days",
    "p90_gap_days",
    "max_gap_days",
]

FALSE_ALARMS = [
    "intake",
    "radius_km",
    "f_threshold",
    "set",
    "quiet_days",
    "quiet_observed_days",
    "alert_days",
    "alert_day_rate_of_observed",
    "alert_episodes_started",
    "episodes_per_365_days",
    "episodes_per_100_observed_days",
]

LEAD_TIMES_BASE = [
    "event",
    "evaluation",
    "intake",
    "radius_km",
    "f_threshold",
    "date_precision",
    "evidence_status",
    "t_ref",
    "t_ref_earliest",
    "lookback_start",
    "days_in_lookback",
    "obs_days_in_lookback",
    "outcome",
]
# The OLCI file carries extra lead time columns because one event was detected.
LEAD_TIMES_OLCI = [
    *LEAD_TIMES_BASE,
    "first_exceed",
    "first_alert",
    "last_exceed",
    "lead_alert_days",
    "lead_alert_min_days",
    "lead_first_exceed_days",
    "last_quiet_before",
    "lead_max_days",
    "censored_at_data_start",
]

PERIOD_ACTIVITY = [
    "event",
    "evaluation",
    "intake",
    "radius_km",
    "f_threshold",
    "period",
    "days",
    "observed_days",
    "exceed_or_alert_days",
    "alert_days",
    "max_anom_frac",
    "median_anom_frac",
    "alert_episodes_started",
    "first_alert_in_period",
    "first_exceed_in_period",
    "evidence_status",
]

DETECTOR_STATES = ("NODATA", "QUIET", "EXCEED", "ALERT")

EVENT_KEYS_REQUIRED = (
    "id",
    "intake_key",
    "dataset",
    "lat",
    "lon",
    "coord_status",
    "date_precision",
    "evidence_status",
    "evaluation",
)
