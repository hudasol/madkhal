from __future__ import annotations

import re
import shutil
from pathlib import Path

import pytest
import yaml

from madkhal.contract import CoverageState, Dataset, StatusClass
from madkhal.core import paths
from madkhal.core.errors import SnapshotError, UnknownSiteError
from madkhal.evidence import (
    MAX_SNAPSHOT_BYTES,
    PINNED_COMMIT,
    NadhirSnapshot,
    calendar,
    monthly_clear_share,
)

ROOT = paths.repo_root()
SNAP = paths.snapshot_dir()

# Operator and utility names that must never appear in labels exposed by the adapter.
OPERATOR_WORDS = [
    "SEWA",
    "SMN",
    "Nama",
    "ACWA",
    "Veolia",
    "TAQA",
    "EWEC",
    "DEWA",
    "ADWEA",
    "IWPP",
    "Power",
]


@pytest.fixture(scope="module")
def snap() -> NadhirSnapshot:
    return NadhirSnapshot()


@pytest.fixture
def copy(tmp_path: Path) -> Path:
    dst = tmp_path / "snap"
    shutil.copytree(SNAP, dst)
    return dst


# ---------------------------------------------------------------- manifest
@pytest.mark.req("MK-L1-001")
def test_manifest_matches_every_file(snap: NadhirSnapshot) -> None:
    assert snap.manifest["source_commit"] == PINNED_COMMIT
    assert len(snap.manifest["files"]) == 41


@pytest.mark.req("MK-L1-001")
def test_events_file_matches_hash_recorded_by_nadhir(snap: NadhirSnapshot) -> None:
    # Nadhir wrote the SHA-256 of the events file it scored into its provenance file.
    events_entry = next(f for f in snap.manifest["files"] if f["path"] == "events.yaml")
    for dataset in (Dataset.olci_v1, Dataset.modis_v1):
        assert snap.provenance(dataset)["events_sha256"] == events_entry["sha256"]


@pytest.mark.req("MK-L1-001")
def test_has_reference_resolves_rows(snap: NadhirSnapshot) -> None:
    assert snap.has_reference("olci_v1/event_lead_times.csv#row=1")
    assert not snap.has_reference("olci_v1/event_lead_times.csv#row=99")
    assert not snap.has_reference("olci_v1/missing.csv")


@pytest.mark.req("MK-L1-001")
def test_altered_byte_fails_hash_check(copy: Path) -> None:
    target = copy / "olci_v1" / "false_alarms.csv"
    data = bytearray(target.read_bytes())
    data[-3] = ord("9") if data[-3] != ord("9") else ord("8")
    target.write_bytes(bytes(data))
    with pytest.raises(SnapshotError, match="olci_v1/false_alarms.csv.*SHA-256"):
        NadhirSnapshot(copy)


@pytest.mark.req("MK-L1-001")
def test_unlisted_file_fails(copy: Path) -> None:
    (copy / "olci_v1" / "extra.csv").write_text("a\n", encoding="utf-8")
    with pytest.raises(SnapshotError, match="extra.csv.*not listed"):
        NadhirSnapshot(copy)


@pytest.mark.req("MK-L1-009")
def test_snapshot_is_under_10_mb(snap: NadhirSnapshot) -> None:
    total = sum(int(f["bytes"]) for f in snap.manifest["files"])
    assert total == snap.manifest["total_bytes"]
    assert total < MAX_SNAPSHOT_BYTES


# ---------------------------------------------------------------- loud failures
def _rewrite(path: Path, old: str, new: str, count: int = 1) -> None:
    text = path.read_bytes().decode("utf-8")
    assert old in text
    path.write_bytes(text.replace(old, new, count).encode("utf-8"))


@pytest.mark.req("MK-L1-002")
def test_renamed_column_names_file_and_column(copy: Path) -> None:
    _rewrite(copy / "olci_v1" / "zone_daily_r50.csv", "anom_frac", "anomaly_frac")
    s = NadhirSnapshot(copy, verify=False)
    with pytest.raises(SnapshotError) as exc:
        s.evidence_days("kalba")
    msg = str(exc.value)
    assert "olci_v1/zone_daily_r50.csv" in msg
    assert "anom_frac" in msg or "anomaly_frac" in msg


@pytest.mark.req("MK-L1-002")
def test_extra_column_is_rejected(copy: Path) -> None:
    _rewrite(
        copy / "olci_v1" / "false_alarms.csv",
        "episodes_per_100_observed_days",
        "episodes_per_100_observed_days,surprise",
    )
    s = NadhirSnapshot(copy, verify=False)
    with pytest.raises(
        SnapshotError, match="false_alarms.csv column 'surprise': unexpected column"
    ):
        s.false_alarms(Dataset.olci_v1)


@pytest.mark.req("MK-L1-002")
def test_bad_value_names_file_row_and_column(copy: Path) -> None:
    _rewrite(copy / "olci_v1" / "zone_daily_r50.csv", ",QUIET,50\n", ",SUNNY,50\n")
    s = NadhirSnapshot(copy, verify=False)
    with pytest.raises(SnapshotError, match=r"zone_daily_r50.csv row \d+ column 'state'"):
        s.evidence_days("kalba")


@pytest.mark.req("MK-L1-002")
def test_inconsistent_observed_flag_is_rejected(copy: Path) -> None:
    _rewrite(copy / "olci_v1" / "zone_daily_r50.csv", "False,,NODATA,50", "True,,NODATA,50")
    s = NadhirSnapshot(copy, verify=False)
    with pytest.raises(SnapshotError, match="column 'state'"):
        s.evidence_days("kalba")


@pytest.mark.req("MK-L1-002")
def test_missing_event_key_is_named(copy: Path) -> None:
    _rewrite(copy / "events.yaml", "    evidence_status: UNVERIFIED\n", "    status: UNVERIFIED\n")
    s = NadhirSnapshot(copy, verify=False)
    with pytest.raises(SnapshotError, match="events.yaml row \\d+ column 'evidence_status'"):
        s.events()


@pytest.mark.req("MK-L1-002")
def test_unknown_site_is_an_input_error(snap: NadhirSnapshot) -> None:
    with pytest.raises(UnknownSiteError):
        snap.evidence_days("atlantis")
    with pytest.raises(UnknownSiteError):
        snap.evidence_days("fujairah", Dataset.olci_v1)


# ---------------------------------------------------------------- calendar
@pytest.mark.req("MK-L1-003")
def test_calendar_has_one_cell_per_day(snap: NadhirSnapshot) -> None:
    for site in ("kalba", "barka", "alraha"):
        days = snap.evidence_days(site)
        assert len(days) == 2137
        assert days[0].date.isoformat() == "2018-01-01"
        assert days[-1].date.isoformat() == "2023-11-07"
        cells = calendar(days)
        assert {c.state for c in cells} == {"clear", "nodata", "alert"}
        for d, c in zip(days, cells, strict=True):
            if d.coverage == CoverageState.nodata:
                assert c.state == "nodata" and not d.alert and d.anomaly_fraction is None


@pytest.mark.req("MK-L1-003")
def test_calendar_counts_match_nadhir_coverage_file(snap: NadhirSnapshot) -> None:
    for site in ("kalba", "barka", "alraha"):
        days = snap.evidence_days(site)
        for cy in snap.coverage_years(site):
            clear = sum(
                1 for d in days if d.date.year == cy.year and d.coverage == CoverageState.clear
            )
            assert clear == cy.observed_days, (site, cy.year)


@pytest.mark.req("MK-L1-003")
def test_alert_total_matches_detector_state_counts(snap: NadhirSnapshot) -> None:
    alerts = sum(sum(d.alert for d in snap.evidence_days(s)) for s in ("kalba", "barka", "alraha"))
    assert alerts == 106  # ALERT rows in olci_v1/zone_daily_r50.csv


@pytest.mark.req("MK-L1-003")
def test_monthly_clear_share_carries_counts(snap: NadhirSnapshot) -> None:
    share = monthly_clear_share(snap.evidence_days("kalba"))
    assert sum(r.n for r in share.values()) == 2137
    assert all(r.rate is not None and r.k <= r.n for r in share.values())


# ---------------------------------------------------------------- track record
@pytest.mark.req("MK-L1-004")
def test_track_record_small_sample(snap: NadhirSnapshot) -> None:
    tr = snap.track_record()
    assert (tr.n_dated, tr.n_observable, tr.n_detected) == (5, 3, 1)
    assert (tr.n_missed, tr.n_not_observable) == (2, 2)
    outcomes = {r.event_id: r.outcome for r in tr.rows}
    assert outcomes == {
        "E2018-KALBA": "DETECTED",
        "E2018-BARKA": "MISSED",
        "E2023-BARKA": "MISSED",
        "E2008-RAK": "NOT_OBSERVABLE",
        "E2008-DIBBA": "NOT_OBSERVABLE",
    }


@pytest.mark.req("MK-L1-004")
def test_track_rows_cite_source_rows(snap: NadhirSnapshot) -> None:
    import csv

    for row in snap.track_record().rows:
        with (SNAP / row.source_file).open(encoding="utf-8", newline="") as fh:
            data = list(csv.reader(fh))
        assert data[row.source_row][0] == row.event_id


@pytest.mark.req("MK-L1-004")
def test_lead_time_anchor_is_n_equals_one(snap: NadhirSnapshot) -> None:
    a = snap.lead_time_anchor()
    assert (a.event_id, a.lead_alert_days, a.lead_alert_min_days, a.n) == (
        "E2018-KALBA",
        8.0,
        -6.0,
        1,
    )


@pytest.mark.req("MK-L1-008")
def test_rates_travel_with_counts(snap: NadhirSnapshot) -> None:
    tr = snap.track_record()
    assert (tr.hit_rate.k, tr.hit_rate.n) == (1, 3)
    fa = {(r.dataset.value, r.site): r for r in tr.false_alarms}
    kalba = fa[("olci_v1", "kalba")]
    assert (kalba.alert_days.k, kalba.alert_days.n, kalba.episodes) == (19, 426, 5)
    assert len(fa) == 7


@pytest.mark.req("MK-L1-004")
def test_quiet_set_reproduces_nadhir_counts(snap: NadhirSnapshot) -> None:
    for dataset in (Dataset.olci_v1, Dataset.modis_v1):
        for row in snap.false_alarms(dataset):
            quiet = snap.quiet_dates(row.site, dataset)
            assert len(quiet) == row.quiet_days, (dataset, row.site)
            observed = [
                d
                for d in snap.evidence_days(row.site, dataset)
                if d.date in quiet and d.coverage == CoverageState.clear
            ]
            assert len(observed) == row.alert_days.n
            assert sum(d.alert for d in observed) == row.alert_days.k


# ---------------------------------------------------------------- events and labels
@pytest.mark.req("MK-L1-005")
def test_every_event_keeps_its_status_verbatim(snap: NadhirSnapshot) -> None:
    raw = yaml.safe_load((SNAP / "events.yaml").read_text(encoding="utf-8"))["events"]
    events = {e.id: e for e in snap.events()}
    assert len(events) == len(raw) == 8
    for r in raw:
        assert events[r["id"]].evidence_status == r["evidence_status"]


@pytest.mark.req("MK-L1-005")
def test_unverified_events_are_always_labelled(snap: NadhirSnapshot) -> None:
    for e in snap.events():
        if "UNVERIFIED" in e.evidence_status:
            assert "UNVERIFIED" in e.status_badge
        if e.status_class == StatusClass.UNVERIFIED:
            assert e.status_badge == "UNVERIFIED"
    for row in snap.track_record().rows:
        if "UNVERIFIED" in row.evidence_status:
            assert row.status_class == StatusClass.UNVERIFIED or "UNVERIFIED" in row.evidence_status


@pytest.mark.req("MK-L1-010")
def test_labels_name_no_operator(snap: NadhirSnapshot) -> None:
    texts = [e.label for e in snap.events()] + [s.name for s in snap.sites()]
    texts += [s.name for s in snap.sites(Dataset.modis_v1)]
    texts += [snap.track_record().blind_spot_note]
    for t in texts:
        for w in OPERATOR_WORDS:
            assert not re.search(rf"\b{w}\b", t), (w, t)


# ---------------------------------------------------------------- MODIS and layering
@pytest.mark.req("MK-L1-007")
def test_modis_sites_are_a_separate_dataset(snap: NadhirSnapshot) -> None:
    modis = snap.sites(Dataset.modis_v1)
    assert [s.id for s in modis] == ["kalba", "fujairah", "rak", "dibba"]
    assert all(s.dataset == Dataset.modis_v1 for s in modis)
    assert modis[0].first_date.year == 2003 and modis[0].last_date.year == 2014
    olci = snap.sites()
    assert all(s.dataset == Dataset.olci_v1 and s.first_date.year == 2018 for s in olci)


@pytest.mark.req("MK-L1-006")
def test_only_the_evidence_layer_touches_the_snapshot() -> None:
    offenders = []
    for path in (ROOT / "src" / "madkhal").rglob("*.py"):
        rel = path.relative_to(ROOT / "src" / "madkhal").as_posix()
        if rel.startswith("evidence/") or rel == "core/paths.py":
            continue
        text = path.read_text(encoding="utf-8")
        if "nadhir_snapshot" in text or "snapshot_dir" in text:
            offenders.append(rel)
    assert offenders == []
