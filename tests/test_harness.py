"""Tests for the repository harness: layers, traceability, claims, writing rules."""

from __future__ import annotations

import subprocess

import pytest

from madkhal import cli
from madkhal.core import paths
from madkhal.core import traceability as tr

ROOT = paths.repo_root()
EM_DASH = chr(0x2014)


@pytest.mark.req("MK-X-001")
def test_import_contracts_hold() -> None:
    from importlinter.cli import lint_imports

    assert lint_imports(config_filename=str(ROOT / "pyproject.toml"), no_cache=True) == 0


@pytest.mark.req("MK-X-001")
def test_layer_order_is_declared_top_down() -> None:
    text = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    order = [
        "madkhal.cli",
        "madkhal.api",
        "madkhal.tasking",
        "madkhal.lab",
        "madkhal.decision",
        "madkhal.plant",
        "madkhal.estimator",
        "madkhal.evidence",
        "madkhal.contract",
        "madkhal.core",
    ]
    positions = [text.index(f'"{name}"') for name in order]
    assert positions == sorted(positions)


@pytest.mark.req("MK-X-002")
def test_every_enforced_must_requirement_has_a_test() -> None:
    assert cli.check_traceability(ROOT) == []


@pytest.mark.req("MK-X-002")
def test_traceability_matrix_detects_missing_tests(tmp_path) -> None:  # type: ignore[no-untyped-def]
    req = tmp_path / "requirements.yaml"
    req.write_text(
        "enforced_through: P1\nrequirements:\n"
        "  - {id: MK-L0-001, tier: MUST, phase: P1, text: a}\n"
        "  - {id: MK-L0-002, tier: MUST, phase: P5, text: b}\n",
        encoding="utf-8",
    )
    tests = tmp_path / "tests"
    tests.mkdir()
    (tests / "test_x.py").write_text(
        'import pytest\n@pytest.mark.req("MK-L9-001")\ndef test_a():\n    pass\n', encoding="utf-8"
    )
    m = tr.build_matrix(req, tests)
    assert m.untested() == ["MK-L0-001"]  # MK-L0-002 is not enforced before P5
    assert "MK-L9-001" in m.unknown_refs


@pytest.mark.req("MK-X-003")
def test_every_claim_pointer_resolves() -> None:
    assert cli.check_claims(ROOT) == []


@pytest.mark.req("MK-X-002")
@pytest.mark.req("MK-X-003")
def test_generated_documents_are_fresh() -> None:
    assert cli.check_generated(ROOT) == []


def _tracked_files() -> list[str]:
    out = subprocess.run(
        ["git", "ls-files", "--cached", "--others", "--exclude-standard"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=True,
        encoding="utf-8",
    )
    return [line for line in out.stdout.splitlines() if line.strip()]


@pytest.mark.req("MK-X-007")
def test_file_names_are_ascii() -> None:
    bad = [f for f in _tracked_files() if not f.isascii()]
    assert bad == []


@pytest.mark.req("MK-X-007")
def test_no_em_dashes_in_published_text() -> None:
    suffixes = (".md", ".yaml", ".py", ".ts", ".tsx", ".json", ".css", ".html")
    skip_prefixes = ("data/nadhir_snapshot/", "web/package-lock.json")
    offenders = []
    for f in _tracked_files():
        if not f.endswith(suffixes) or f.startswith(skip_prefixes):
            continue
        path = ROOT / f
        if path.is_file() and EM_DASH in path.read_text(encoding="utf-8", errors="ignore"):
            offenders.append(f)
    assert offenders == []
