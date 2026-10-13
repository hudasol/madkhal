"""Requirement traceability: requirements in docs/requirements.yaml, tests that name them.

A test links itself to a requirement with ``@pytest.mark.req("MK-L2-001")``. The
matrix is built by parsing the test files (no test execution needed), so the fast
check can fail when a MUST requirement has no test.
"""

from __future__ import annotations

import ast
import re
from dataclasses import dataclass, field
from pathlib import Path

import yaml

REQ_ID = re.compile(r"^MK-(L[0-8]|X)-\d{3}$")
REQ_IN_TEXT = re.compile(r"\b(MK-(?:L[0-8]|X)-\d{3})\b")
TIERS = ("MUST", "SHOULD", "MAY")
PHASES = tuple(f"P{i}" for i in range(11))


def phase_index(phase: str) -> int:
    return PHASES.index(phase)


@dataclass(frozen=True)
class Requirement:
    id: str
    tier: str
    layer: str
    text: str
    phase: str


@dataclass
class Matrix:
    requirements: list[Requirement]
    enforced_through: str = "P10"
    tests: dict[str, list[str]] = field(default_factory=dict)  # req id -> test node ids
    unknown_refs: dict[str, list[str]] = field(default_factory=dict)  # bad id -> tests

    def untested(self, tier: str = "MUST", *, enforced_only: bool = True) -> list[str]:
        limit = phase_index(self.enforced_through)
        return [
            r.id
            for r in self.requirements
            if r.tier == tier
            and not self.tests.get(r.id)
            and (not enforced_only or phase_index(r.phase) <= limit)
        ]


def enforced_through(path: Path) -> str:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    phase = str(data.get("enforced_through", "P10"))
    phase_index(phase)
    return phase


def load_requirements(path: Path) -> list[Requirement]:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    out: list[Requirement] = []
    seen: set[str] = set()
    for row in data["requirements"]:
        rid = str(row["id"])
        if not REQ_ID.match(rid):
            raise ValueError(f"{path.name}: malformed requirement id {rid!r}")
        if rid in seen:
            raise ValueError(f"{path.name}: duplicate requirement id {rid}")
        tier = str(row["tier"])
        if tier not in TIERS:
            raise ValueError(f"{path.name}: {rid} has tier {tier!r}, expected one of {TIERS}")
        phase = str(row["phase"])
        if phase not in PHASES:
            raise ValueError(f"{path.name}: {rid} has unknown phase {phase!r}")
        seen.add(rid)
        out.append(Requirement(rid, tier, rid.split("-")[1], str(row["text"]).strip(), phase))
    return out


def _req_ids_of(node: ast.AST) -> list[str]:
    ids: list[str] = []
    decos = getattr(node, "decorator_list", [])
    for d in decos:
        if isinstance(d, ast.Call) and isinstance(d.func, ast.Attribute) and d.func.attr == "req":
            for a in d.args:
                if isinstance(a, ast.Constant) and isinstance(a.value, str):
                    ids.append(a.value)
    return ids


def scan_tests(tests_dir: Path) -> dict[str, list[str]]:
    """Map requirement id -> list of ``file::test`` names that carry the marker."""
    found: dict[str, list[str]] = {}
    for path in sorted(tests_dir.rglob("test_*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        rel = path.relative_to(tests_dir.parent).as_posix()
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef):
                for rid in _req_ids_of(node):
                    found.setdefault(rid, []).append(f"{rel}::{node.name}")
    return found


WEB_TEST_SUFFIXES = (".test.ts", ".test.tsx", ".spec.ts")
WEB_TEST_TITLE = re.compile(r"""\b(?:it|test|describe)\s*\(\s*(["'`])(.*?)\1""")
# table driven tests: it.each(table)("MK-... title"); the table may span several lines
WEB_EACH_TITLE = re.compile(r"""\b(?:it|test|describe)\.each\b[\s\S]*?\)\s*\(\s*(["'`])(.*?)\1""")


def scan_web_tests(web_dir: Path) -> dict[str, list[str]]:
    """Web tests name requirement IDs inside their titles, for example ``it("MK-L8-002 ...")``."""
    found: dict[str, list[str]] = {}
    if not web_dir.is_dir():
        return found
    for sub in ("src", "e2e"):
        base = web_dir / sub
        if not base.is_dir():
            continue
        for path in sorted(base.rglob("*")):
            if not path.name.endswith(WEB_TEST_SUFFIXES) or "node_modules" in path.parts:
                continue
            rel = path.relative_to(web_dir.parent).as_posix()
            text = path.read_text(encoding="utf-8")
            matches = [*WEB_TEST_TITLE.finditer(text), *WEB_EACH_TITLE.finditer(text)]
            for m in matches:
                title = m.group(2)
                for rid in REQ_IN_TEXT.findall(title):
                    found.setdefault(rid, []).append(f"{rel}::{title[:60]}")
    return found


def build_matrix(requirements_path: Path, tests_dir: Path, web_dir: Path | None = None) -> Matrix:
    reqs = load_requirements(requirements_path)
    known = {r.id for r in reqs}
    scanned = scan_tests(tests_dir)
    if web_dir is not None:
        for rid, tests in scan_web_tests(web_dir).items():
            scanned.setdefault(rid, []).extend(tests)
    m = Matrix(requirements=reqs, enforced_through=enforced_through(requirements_path))
    for rid, tests in scanned.items():
        if rid in known:
            m.tests[rid] = sorted(tests)
        else:
            m.unknown_refs[rid] = sorted(tests)
    return m


def render_markdown(m: Matrix) -> str:
    lines = [
        "# Requirements traceability",
        "",
        "Generated by `madkhal docs build` from `docs/requirements.yaml` and the `@pytest.mark.req`",
        "markers in `tests/`. Do not edit by hand. The fast check fails when a MUST requirement",
        "has no test.",
        "",
    ]
    by_tier = {t: [r for r in m.requirements if r.tier == t] for t in TIERS}
    tested = {t: sum(1 for r in by_tier[t] if m.tests.get(r.id)) for t in TIERS}
    lines.append(f"Enforced through phase {m.enforced_through}.")
    lines.append("")
    lines.append("| Tier | Requirements | With at least one test |")
    lines.append("|---|---|---|")
    for t in TIERS:
        lines.append(f"| {t} | {len(by_tier[t])} | {tested[t]} |")
    lines.append("")
    layer = None
    for r in m.requirements:
        if r.layer != layer:
            layer = r.layer
            lines += [
                "",
                f"## Layer {layer}",
                "",
                "| ID | Tier | Requirement | Tests |",
                "|---|---|---|---|",
            ]
        tests = m.tests.get(r.id, [])
        cell = "<br>".join(f"`{t}`" for t in tests) if tests else "**none**"
        text = r.text.replace("|", "\\|").replace("\n", " ")
        lines.append(f"| {r.id} | {r.tier} | {text} | {cell} |")
    lines.append("")
    return "\n".join(lines)
