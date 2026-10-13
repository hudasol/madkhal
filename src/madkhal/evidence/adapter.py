"""The Nadhir adapter: the only code in Madkhal that reads the snapshot files.

Everything it returns is an L0 contract model or a plain typed record with the source
file and row cited. Any surprise in a file (a missing or extra column, a value of the
wrong type, an inconsistent row, a hash that differs from the manifest) raises
``SnapshotError`` naming the file and, where known, the row and column.
"""

from __future__ import annotations

import csv
import datetime as dt
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from madkhal.contract import (
    CoverageState,
    Dataset,
    DetectorState,
    Event,
    EvidenceDay,
    FalseAlarmRow,
    RateWithCounts,
    Site,
    StatusClass,
    TrackRecord,
    TrackRow,
)
from madkhal.core import paths
from madkhal.core.errors import SnapshotError, UnknownSiteError
from madkhal.core.jsonio import read_json

from . import manifest, schema
from .csvread import Row, read_rows

RADII = (25, 50, 100)
PRIMARY_RADIUS = 50

# Minimum clear days in the 121 day lookback for an event to count as observable.
# Observed values: 33, 20 and 66 for the scored OLCI events; 1 and 0 for the two MODIS
# events Nadhir reports as not observable. Any threshold from 2 to 20 gives the same split.
OBSERVABLE_MIN_CLEAR_DAYS = 5

PLACES: dict[str, tuple[str, str]] = {
    "kalba": ("Kalba", "كلباء"),
    "barka": ("Barka", "بركاء"),
    "alraha": ("Al Raha", "الراحة"),
    "fujairah": ("Fujairah", "الفجيرة"),
    "rak": ("Ras Al Khaimah", "رأس الخيمة"),
    "dibba": ("Dibba", "دبا"),
}

# ASSUMPTION: rough bearing from the estimated intake towards open water, read from the
# general shape of the coast. Used only to draw schematic survey missions.
OFFSHORE_BEARING_DEG: dict[str, float] = {
    "kalba": 90.0,
    "barka": 20.0,
    "alraha": 330.0,
    "fujairah": 90.0,
    "rak": 300.0,
    "dibba": 70.0,
}

# Neutral event labels: place, year and kind only. No operator is named.
EVENT_LABELS: dict[str, str] = {
    "E2008-FUJ": "Fujairah 2008 to 2009, bloom period with reported desalination losses",
    "E2008-RAK": "Ras Al Khaimah 2008, desalination closure report",
    "E2008-DIBBA": "Dibba 2008, first public sighting of discoloured water (not a shutdown)",
    "E2013-KALBA": "Kalba 2013, desalination shutdown report (year only)",
    "E2018-BARKA": "Barka 2018, desalination disruption report",
    "E2018-KALBA": "Kalba 2018, desalination disruption report",
    "E2023-BARKA": "Barka 2023, desalination disruption report",
    "E2023-ALRAHA": "Al Raha 2023, documented diatom bloom (not an intake; known miss case)",
}

DATASET_DIRS = {Dataset.olci_v1: "olci_v1", Dataset.modis_v1: "modis_v1"}
DATASET_SITES = {
    Dataset.olci_v1: ("kalba", "barka", "alraha"),
    Dataset.modis_v1: ("kalba", "fujairah", "rak", "dibba"),
}
PROFILE_KEYS = {Dataset.olci_v1: None, Dataset.modis_v1: "modis_v1"}


def status_class(status: str) -> StatusClass:
    s = status.strip()
    if s.startswith("VERIFIED-PRIMARY"):
        return StatusClass.VERIFIED_PRIMARY
    if s.startswith("VERIFIED-SECONDARY"):
        return StatusClass.VERIFIED_SECONDARY
    return StatusClass.UNVERIFIED


def status_badge(status: str) -> str:
    cls = status_class(status)
    if cls == StatusClass.UNVERIFIED:
        return "UNVERIFIED"
    if "UNVERIFIED" in status:
        return f"{cls.value}, dates UNVERIFIED"
    return cls.value


@dataclass(frozen=True)
class Episode:
    site: str
    radius_km: int
    first_exceed: dt.date
    first_alert: dt.date
    last_exceed: dt.date
    closed_on: dt.date
    source_file: str
    source_row: int


@dataclass(frozen=True)
class CoverageYear:
    site: str
    radius_km: int
    year: int
    days: int
    observed_days: int
    observed_frac: float
    max_gap_days: int
    source_file: str
    source_row: int


@dataclass(frozen=True)
class LeadTimeAnchor:
    event_id: str
    lead_alert_days: float
    lead_alert_min_days: float
    n: int
    source_file: str
    source_row: int


class NadhirSnapshot:
    """Read only access to the pinned Nadhir snapshot."""

    def __init__(self, root: Path | None = None, *, verify: bool = True) -> None:
        self.root = root or paths.snapshot_dir()
        self.manifest = manifest.verify(self.root) if verify else manifest.load_manifest(self.root)
        self._days: dict[tuple[Dataset, str, int], list[EvidenceDay]] = {}
        self._events: list[Event] | None = None
        self._config: dict[str, Any] | None = None
        self._raw_events: list[dict[str, Any]] | None = None

    # ------------------------------------------------------------ helpers
    def _path(self, rel: str) -> Path:
        return self.root / rel

    def _yaml(self, rel: str) -> Any:
        path = self._path(rel)
        if not path.is_file():
            raise SnapshotError(rel, "file is missing")
        try:
            return yaml.safe_load(path.read_text(encoding="utf-8"))
        except yaml.YAMLError as exc:
            raise SnapshotError(rel, f"invalid YAML: {exc}") from None

    def config(self) -> dict[str, Any]:
        if self._config is None:
            data = self._yaml("config/nadhir.yaml")
            if not isinstance(data, dict) or "intakes" not in data or "periods" not in data:
                raise SnapshotError("config/nadhir.yaml", "expected keys intakes and periods")
            self._config = data
        return self._config

    def _profile(self, dataset: Dataset) -> dict[str, Any]:
        cfg = self.config()
        if dataset == Dataset.olci_v1:
            return {"intakes": cfg["intakes"], "periods": cfg["periods"]}
        prof = cfg.get("profiles", {}).get("modis_v1")
        if not isinstance(prof, dict):
            raise SnapshotError("config/nadhir.yaml", "missing profiles.modis_v1")
        return {"intakes": prof["intakes"], "periods": prof["periods"]}

    @staticmethod
    def _check_site(dataset: Dataset, site: str) -> None:
        if site not in DATASET_SITES[dataset]:
            raise UnknownSiteError(f"unknown site {site!r} for dataset {dataset.value}")

    # ------------------------------------------------------------ sites
    def sites(self, dataset: Dataset = Dataset.olci_v1) -> list[Site]:
        prof = self._profile(dataset)
        out = []
        for sid in DATASET_SITES[dataset]:
            intake = prof["intakes"].get(sid)
            if not isinstance(intake, dict):
                raise SnapshotError("config/nadhir.yaml", f"missing intake {sid}")
            days = self.evidence_days(sid, dataset)
            name, name_ar = PLACES[sid]
            out.append(
                Site(
                    id=sid,
                    name=name,
                    name_ar=name_ar,
                    dataset=dataset,
                    lat=float(intake["lat"]),
                    lon=float(intake["lon"]),
                    coord_status=str(intake["coord_status"]),
                    offshore_bearing_deg=OFFSHORE_BEARING_DEG[sid],
                    first_date=days[0].date,
                    last_date=days[-1].date,
                    radii_km=list(RADII),
                    primary_radius_km=PRIMARY_RADIUS,
                )
            )
        return out

    def site(self, site: str, dataset: Dataset = Dataset.olci_v1) -> Site:
        self._check_site(dataset, site)
        return next(s for s in self.sites(dataset) if s.id == site)

    # ------------------------------------------------------------ daily evidence
    def _load_zone_daily(self, dataset: Dataset, radius: int) -> None:
        rel = f"{DATASET_DIRS[dataset]}/zone_daily_r{radius}.csv"
        per_site: dict[str, list[EvidenceDay]] = {s: [] for s in DATASET_SITES[dataset]}
        for row in read_rows(self._path(rel), rel, schema.ZONE_DAILY):
            sid = row.text("intake", DATASET_SITES[dataset])
            day = self._zone_row(row, rel, sid, radius)
            seq = per_site[sid]
            if seq and day.date != seq[-1].date + dt.timedelta(days=1):
                raise SnapshotError(rel, "dates are not consecutive", row=row.index, column="date")
            seq.append(day)
        for sid, seq in per_site.items():
            if not seq:
                raise SnapshotError(rel, f"no rows for site {sid}", column="intake")
            self._days[(dataset, sid, radius)] = seq

    @staticmethod
    def _zone_row(row: Row, rel: str, sid: str, radius: int) -> EvidenceDay:
        d = row.date("date")
        if row.integer("month", 1, 12) != d.month:
            raise SnapshotError(rel, "month does not match date", row=row.index, column="month")
        if row.integer("radius_km") != radius:
            raise SnapshotError(
                rel, "radius does not match the file", row=row.index, column="radius_km"
            )
        n_obs = row.integer("n_obs", 0)
        if row.integer("n_anom", 0) > n_obs:
            raise SnapshotError(rel, "n_anom exceeds n_obs", row=row.index, column="n_anom")
        row.integer("n_clim", 0)
        row.number("coverage", 0.0, 1.0)
        row.number_or_none("max_z")
        row.number_or_none("median_logchl")
        observed = row.boolean("observed")
        state = DetectorState(row.text("state", schema.DETECTOR_STATES))
        frac = row.number_or_none("anom_frac", 0.0, 1.0)
        if observed == (state == DetectorState.NODATA):
            raise SnapshotError(rel, "observed and state disagree", row=row.index, column="state")
        if observed != (frac is not None):
            raise SnapshotError(
                rel,
                "anom_frac must be present exactly on observed days",
                row=row.index,
                column="anom_frac",
            )
        return EvidenceDay(
            date=d,
            site=sid,
            radius_km=radius,
            coverage=CoverageState.clear if observed else CoverageState.nodata,
            alert=state == DetectorState.ALERT,
            detector_state=state,
            anomaly_fraction=frac,
            source_file=rel,
            source_row=row.index,
        )

    def evidence_days(
        self, site: str, dataset: Dataset = Dataset.olci_v1, radius: int = PRIMARY_RADIUS
    ) -> list[EvidenceDay]:
        """Daily evidence for a site, oldest first, one row per calendar day."""
        self._check_site(dataset, site)
        if radius not in RADII:
            raise UnknownSiteError(f"radius must be one of {RADII}")
        key = (dataset, site, radius)
        if key not in self._days:
            self._load_zone_daily(dataset, radius)
        return list(self._days[key])

    # ------------------------------------------------------------ events
    def _events_raw(self) -> list[dict[str, Any]]:
        if self._raw_events is None:
            data = self._yaml("events.yaml")
            if not isinstance(data, dict) or not isinstance(data.get("events"), list):
                raise SnapshotError("events.yaml", "expected a top level 'events' list")
            for i, e in enumerate(data["events"], start=1):
                for key in schema.EVENT_KEYS_REQUIRED:
                    if key not in e:
                        raise SnapshotError(
                            "events.yaml", "event key is missing", row=i, column=key
                        )
            self._raw_events = list(data["events"])
        return self._raw_events

    def events(self) -> list[Event]:
        if self._events is None:
            out = []
            for i, e in enumerate(self._events_raw(), start=1):
                eid = str(e["id"])
                if eid not in EVENT_LABELS:
                    raise SnapshotError(
                        "events.yaml", f"event {eid} has no neutral label", row=i, column="id"
                    )
                status = str(e["evidence_status"])
                out.append(
                    Event(
                        id=eid,
                        label=EVENT_LABELS[eid],
                        site=str(e["intake_key"]),
                        dataset=Dataset(str(e["dataset"])),
                        lat=float(e["lat"]),
                        lon=float(e["lon"]),
                        coord_status=str(e["coord_status"]),
                        date_precision=str(e["date_precision"]),
                        t_ref=_date(e.get("t_ref"), i, "t_ref"),
                        t_ref_earliest=_date(e.get("t_ref_earliest"), i, "t_ref_earliest"),
                        period_start=_date(e.get("bloom_period_start"), i, "bloom_period_start"),
                        period_end=_date(e.get("bloom_period_end"), i, "bloom_period_end"),
                        evaluation=str(e["evaluation"]),
                        evidence_status=status,
                        status_class=status_class(status),
                        status_badge=status_badge(status),
                        species=str(e["species"]) if e.get("species") else None,
                        source_file="events.yaml",
                        source_index=i,
                    )
                )
            self._events = out
        return list(self._events)

    def event(self, event_id: str) -> Event:
        for e in self.events():
            if e.id == event_id:
                return e
        raise UnknownSiteError(f"unknown event {event_id!r}")

    # ------------------------------------------------------------ result files
    def lead_time_rows(self, dataset: Dataset) -> list[Row]:
        rel = f"{DATASET_DIRS[dataset]}/event_lead_times.csv"
        cols = schema.LEAD_TIMES_OLCI if dataset == Dataset.olci_v1 else schema.LEAD_TIMES_BASE
        rows = list(read_rows(self._path(rel), rel, cols))
        for r in rows:
            r.text("outcome", ("DETECTED", "MISS", "NO-DATA"))
            r.integer("radius_km")
            r.integer("days_in_lookback", 0)
            r.integer("obs_days_in_lookback", 0)
            r.date("t_ref")
        return rows

    def track_record(self, radius: int = PRIMARY_RADIUS) -> TrackRecord:
        """Detector track record over the dated events, cited to Nadhir rows."""
        rows: list[TrackRow] = []
        for dataset in (Dataset.olci_v1, Dataset.modis_v1):
            for r in self.lead_time_rows(dataset):
                if r.integer("radius_km") != radius:
                    continue
                # Only dated disruptions count; the Al Raha limitation test is reported apart.
                if r.text("evaluation", ("EVALUATED", "LIMITATION-TEST")) != "EVALUATED":
                    continue
                eid = r.text("event")
                event = self.event(eid)
                clear = r.integer("obs_days_in_lookback", 0)
                nadhir = r.text("outcome")
                observable = clear >= OBSERVABLE_MIN_CLEAR_DAYS
                if not observable:
                    outcome = "NOT_OBSERVABLE"
                elif nadhir == "DETECTED":
                    outcome = "DETECTED"
                else:
                    outcome = "MISSED"
                lead = (
                    r.number_or_none("lead_alert_days") if "lead_alert_days" in r.values else None
                )
                lead_min = (
                    r.number_or_none("lead_alert_min_days")
                    if "lead_alert_min_days" in r.values
                    else None
                )
                status = r.text("evidence_status")
                rows.append(
                    TrackRow(
                        event_id=eid,
                        label=event.label,
                        dataset=dataset,
                        outcome=outcome,
                        nadhir_outcome=nadhir,
                        clear_days_in_lookback=clear,
                        days_in_lookback=r.integer("days_in_lookback", 0),
                        lead_alert_days=lead,
                        lead_alert_min_days=lead_min,
                        evidence_status=status,
                        status_class=status_class(status),
                        source_file=r.file,
                        source_row=r.index,
                    )
                )
        n_obs = sum(1 for t in rows if t.outcome != "NOT_OBSERVABLE")
        n_det = sum(1 for t in rows if t.outcome == "DETECTED")
        return TrackRecord(
            n_dated=len(rows),
            n_observable=n_obs,
            n_detected=n_det,
            n_missed=n_obs - n_det,
            n_not_observable=len(rows) - n_obs,
            hit_rate=RateWithCounts(
                k=n_det,
                n=n_obs,
                rate=n_det / n_obs if n_obs else None,
                note="dated events detected, of those observable",
            ),
            observable_rule=(
                f"An event is observable when the {radius} km watch zone had at least "
                f"{OBSERVABLE_MIN_CLEAR_DAYS} clear satellite days in the 121 day lookback before "
                "its reference date."
            ),
            rows=rows,
            false_alarms=[
                fa
                for d in (Dataset.olci_v1, Dataset.modis_v1)
                for fa in self.false_alarms(d, radius)
            ],
            blind_spot_note=(
                "Al Raha, April 2023: a bloom documented as Pseudo-nitzschia multistriata "
                "produced no broadband chlorophyll anomaly in daily OLCI (Nadhir "
                "period_activity.csv). Absence of an alert cannot rule out such a bloom."
            ),
        )

    def false_alarms(
        self, dataset: Dataset, radius: int = PRIMARY_RADIUS, subset: str = "heldout_quiet"
    ) -> list[FalseAlarmRow]:
        rel = f"{DATASET_DIRS[dataset]}/false_alarms.csv"
        out = []
        for r in read_rows(self._path(rel), rel, schema.FALSE_ALARMS):
            sid = r.text("intake", DATASET_SITES[dataset])
            if r.integer("radius_km") != radius or r.text("set") != subset:
                continue
            k = r.integer("alert_days", 0)
            n = r.integer("quiet_observed_days", 0)
            if k > n:
                raise SnapshotError(
                    rel, "alert_days exceeds quiet_observed_days", row=r.index, column="alert_days"
                )
            out.append(
                FalseAlarmRow(
                    site=sid,
                    dataset=dataset,
                    radius_km=radius,
                    alert_days=RateWithCounts(
                        k=k, n=n, rate=k / n if n else None, note="alert days of clear quiet days"
                    ),
                    episodes=r.integer("alert_episodes_started", 0),
                    quiet_days=r.integer("quiet_days", 0),
                    episodes_per_year=r.number("episodes_per_365_days", 0.0),
                    source_file=rel,
                    source_row=r.index,
                )
            )
        return out

    def lead_time_anchor(self) -> LeadTimeAnchor:
        """The single detected event's lead time range (n = 1)."""
        for r in self.lead_time_rows(Dataset.olci_v1):
            if r.text("outcome") == "DETECTED" and r.integer("radius_km") == PRIMARY_RADIUS:
                return LeadTimeAnchor(
                    event_id=r.text("event"),
                    lead_alert_days=r.number("lead_alert_days"),
                    lead_alert_min_days=r.number("lead_alert_min_days"),
                    n=1,
                    source_file=r.file,
                    source_row=r.index,
                )
        raise SnapshotError(
            "olci_v1/event_lead_times.csv", "no detected event at the primary radius"
        )

    def episodes(
        self, site: str, dataset: Dataset = Dataset.olci_v1, radius: int = PRIMARY_RADIUS
    ) -> list[Episode]:
        self._check_site(dataset, site)
        rel = f"{DATASET_DIRS[dataset]}/episodes_{site}_r{radius}.csv"
        out = []
        for r in read_rows(self._path(rel), rel, schema.EPISODES):
            r.text("intake", (site,))
            if r.integer("radius_km") != radius:
                raise SnapshotError(
                    rel, "radius does not match the file", row=r.index, column="radius_km"
                )
            ep = Episode(
                site=site,
                radius_km=radius,
                first_exceed=r.date("first_exceed"),
                first_alert=r.date("first_alert"),
                last_exceed=r.date("last_exceed"),
                closed_on=r.date("closed_on"),
                source_file=rel,
                source_row=r.index,
            )
            if not ep.first_exceed <= ep.first_alert <= ep.closed_on:
                raise SnapshotError(
                    rel, "episode dates out of order", row=r.index, column="first_alert"
                )
            out.append(ep)
        return out

    def coverage_years(
        self, site: str, dataset: Dataset = Dataset.olci_v1, radius: int = PRIMARY_RADIUS
    ) -> list[CoverageYear]:
        self._check_site(dataset, site)
        rel = f"{DATASET_DIRS[dataset]}/coverage.csv"
        out = []
        for r in read_rows(self._path(rel), rel, schema.COVERAGE):
            sid = r.text("intake", DATASET_SITES[dataset])
            if sid != site or r.integer("radius_km") != radius:
                continue
            days = r.integer("days", 1, 366)
            obs = r.integer("observed_days", 0, days)
            out.append(
                CoverageYear(
                    site=sid,
                    radius_km=radius,
                    year=r.integer("year", 2000, 2100),
                    days=days,
                    observed_days=obs,
                    observed_frac=r.number("observed_frac", 0.0, 1.0),
                    max_gap_days=r.integer("max_gap_days", 0),
                    source_file=rel,
                    source_row=r.index,
                )
            )
        return out

    def period_activity_rows(self, dataset: Dataset) -> list[Row]:
        rel = f"{DATASET_DIRS[dataset]}/period_activity.csv"
        rows = list(read_rows(self._path(rel), rel, schema.PERIOD_ACTIVITY))
        for r in rows:
            r.integer("observed_days", 0)
            r.integer("alert_days", 0)
            r.number_or_none("median_anom_frac", 0.0, 1.0)
        return rows

    def provenance(self, dataset: Dataset) -> dict[str, Any]:
        rel = f"{DATASET_DIRS[dataset]}/provenance.json"
        path = self._path(rel)
        if not path.is_file():
            raise SnapshotError(rel, "file is missing")
        data: dict[str, Any] = read_json(path)
        for key in ("detector", "tag_commit", "data"):
            if key not in data:
                raise SnapshotError(rel, "key is missing", column=key)
        return data

    def has_reference(self, ref: str) -> bool:
        """Whether ``<file>`` or ``<file>#row=<n>`` names a snapshot file (and data row)."""
        rel, _, frag = ref.partition("#")
        listed = {str(f["path"]) for f in self.manifest["files"]}
        if rel not in listed:
            return False
        if not frag:
            return True
        if not frag.startswith("row="):
            return False
        n = int(frag[4:])
        with self._path(rel).open(encoding="utf-8", newline="") as fh:
            count = sum(1 for _ in csv.reader(fh)) - 1
        return 1 <= n <= count

    # ------------------------------------------------------------ quiet periods
    def quiet_dates(self, site: str, dataset: Dataset = Dataset.olci_v1) -> set[dt.date]:
        """Nadhir's held out quiet set for a site (same rule as Nadhir's evaluate.quiet_mask)."""
        self._check_site(dataset, site)
        per = self._profile(dataset)["periods"]
        lo, hi = (dt.date.fromisoformat(str(x)) for x in per["heldout_quiet"])
        excl_years = {int(y) for y in (per.get("quiet_exclude") or {}).get(site, [])}
        years = {int(y) for y in per.get("extra_quiet_years", [])} - excl_years
        days = [d.date for d in self.evidence_days(site, dataset)]
        keep = {d for d in days if lo <= d <= hi or d.year in years}
        return keep - self.event_window_dates(site, dataset)

    def event_window_dates(self, site: str, dataset: Dataset = Dataset.olci_v1) -> set[dt.date]:
        """Days within [t_ref - before, t_ref + after] of any dated event at the site."""
        per = self._profile(dataset)["periods"]
        before = int(per["event_exclusion_before_days"])
        after = int(per["event_exclusion_after_days"])
        out: set[dt.date] = set()
        for e in self._events_raw():
            if e.get("intake_key") != site or not e.get("t_ref"):
                continue
            t = dt.date.fromisoformat(str(e["t_ref"]))
            for k in range(-before, after + 1):
                out.add(t + dt.timedelta(days=k))
        return out

    def excluded_years(self, site: str, dataset: Dataset = Dataset.olci_v1) -> set[int]:
        per = self._profile(dataset)["periods"]
        return {int(y) for y in (per.get("quiet_exclude") or {}).get(site, [])}

    def calibration_period(self, dataset: Dataset = Dataset.olci_v1) -> tuple[dt.date, dt.date]:
        per = self._profile(dataset)["periods"]
        lo, hi = (dt.date.fromisoformat(str(x)) for x in per["calibration"])
        return lo, hi


def _date(value: Any, row: int, column: str) -> dt.date | None:
    if value is None or value == "":
        return None
    if isinstance(value, dt.date):
        return value
    try:
        return dt.date.fromisoformat(str(value))
    except ValueError:
        raise SnapshotError(
            "events.yaml", f"expected an ISO date, got {value!r}", row=row, column=column
        ) from None
