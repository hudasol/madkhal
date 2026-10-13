from __future__ import annotations

import json

import numpy as np
import pytest
from typer.testing import CliRunner

from madkhal.cli import app
from madkhal.contract import REPLAY_LABEL
from madkhal.estimator import belief_series, draw_parameters
from madkhal.lab.inputs import prior_spec, snapshot
from madkhal.lab.replay import belief_at_events, event_points

runner = CliRunner()


@pytest.mark.req("MK-L2-014")
def test_e1_smoke_runs_from_the_cli() -> None:
    res = runner.invoke(app, ["eval", "--smoke", "--seed", "2"])
    assert res.exit_code == 0, res.output
    out = json.loads(res.stdout)
    assert out["label"].startswith("SYNTHETIC")
    assert set(out["brier"]) == {"madkhal", "alert_means_bloom", "persistence"}


@pytest.mark.req("MK-L2-006")
def test_belief_command_prints_a_bloom_belief() -> None:
    res = runner.invoke(app, ["belief", "--site", "kalba", "--date", "2018-09-08", "--draws", "50"])
    assert res.exit_code == 0, res.output
    out = json.loads(res.stdout)
    assert [w["horizon_days"] for w in out["within"]] == [1, 3, 7]
    assert out["alert"] is True and out["observation"] == "clear"


@pytest.mark.req("MK-L5-008")
def test_replay_is_deterministic() -> None:
    a = belief_at_events("kalba", n_draws=50, seed=3)
    b = belief_at_events("kalba", n_draws=50, seed=3)
    assert a == b
    assert a["label"] == REPLAY_LABEL


@pytest.mark.req("MK-L5-009")
def test_replay_never_uses_information_after_the_replay_date() -> None:
    snap = snapshot()
    days = snap.evidence_days("barka")
    dr = draw_parameters(prior_spec("barka"), 50, 4)
    full = belief_series("barka", days, dr)
    cut = 400
    part = belief_series("barka", days[:cut], dr)
    for name in ("any_bloom", "within_3", "within_7"):
        assert np.array_equal(full.quantiles[name][:cut], part.quantiles[name])


@pytest.mark.req("MK-L5-007")
def test_replay_points_cover_every_olci_event_with_status() -> None:
    ids = {p.event_id for s in ("kalba", "barka", "alraha") for p in event_points(s)}
    assert ids == {"E2018-KALBA", "E2018-BARKA", "E2023-BARKA", "E2023-ALRAHA"}
    for p in event_points("barka"):
        assert p.status_badge == "UNVERIFIED"
        assert p.days_before in (14, 7, 3)
