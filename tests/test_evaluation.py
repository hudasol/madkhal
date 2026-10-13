"""Checks on the committed results and the rendered evaluation document."""

from __future__ import annotations

import re

import pytest

from madkhal import cli
from madkhal.core import paths
from madkhal.lab.evaluation_report import predictions, render

ROOT = paths.repo_root()
RESULTS = cli.load_results(ROOT)
needs_results = pytest.mark.skipif(not RESULTS, reason="results/*.json not generated yet")


@needs_results
@pytest.mark.req("MK-L5-011")
def test_results_cover_every_experiment_with_enough_seeds() -> None:
    for name in ("e1", "e2", "e3", "e4", "e5", "e6", "e7", "run"):
        assert name in RESULTS, f"results/{name}.json missing"
    assert len(RESULTS["run"]["seeds"]) >= 30  # type: ignore[arg-type]
    assert len(RESULTS["e4"]["seeds"]) >= 20  # type: ignore[arg-type]
    e2 = RESULTS["e2"]["policies"]  # type: ignore[index]
    for p in ("P0", "P1", "P2", "P3", "P4", "P5"):
        s = e2[p]["metrics"]["weighted_cost_cu"]
        assert s["n"] >= 30 and s["lo"] <= s["mean"] <= s["hi"]


@needs_results
@pytest.mark.req("MK-L5-012")
def test_every_preregistered_prediction_is_marked_hit_or_miss() -> None:
    prereg = (ROOT / "docs" / "PREREGISTRATION.md").read_text(encoding="utf-8")
    ids = sorted(set(re.findall(r"\bPR-E\d-\d\b", prereg)))
    marked = {p["id"]: p["result"] for p in predictions(RESULTS)}  # type: ignore[arg-type]
    assert sorted(marked) == ids
    assert set(marked.values()) <= {"HIT", "MISS"}
    doc = (ROOT / "docs" / "EVALUATION.md").read_text(encoding="utf-8")
    for pid, result in marked.items():
        assert re.search(rf"\| {pid} \|.*\| {result} \|", doc), pid


@needs_results
@pytest.mark.req("MK-X-006")
def test_evaluation_document_matches_results() -> None:
    doc = (ROOT / "docs" / "EVALUATION.md").read_text(encoding="utf-8")
    assert doc == render(RESULTS, cli.evaluation_notes(ROOT))  # type: ignore[arg-type]


@pytest.mark.req("MK-X-006")
def test_evaluation_notes_hold_no_numbers() -> None:
    # every number must come from results/*.json, so hand written notes may not add any
    for pid, text in cli.evaluation_notes(ROOT).items():
        assert re.fullmatch(r"PR-E\d-\d", pid)
        names_removed = re.sub(r"\b(?:PR-E\d-\d|[GPEL]\d)\b", "", text)  # G1, P3, E7 are names
        assert not re.search(r"\d", names_removed), pid


@needs_results
@pytest.mark.req("MK-L5-010")
def test_results_label_synthetic_and_replay() -> None:
    for name in ("e1", "e2", "e3", "e4", "e5", "e6"):
        assert RESULTS[name]["label"] == "SYNTHETIC"
    assert RESULTS["e7"]["label"] == "REPLAY: real satellite evidence, hypothetical plant"
