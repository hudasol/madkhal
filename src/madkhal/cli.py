"""Madkhal command line interface (the single Python entry point).

Every command is non interactive and terminates. Advisory software for planning and
learning only: nothing here connects to or controls any plant.
"""

from __future__ import annotations

import os
import subprocess
import sys
import time
from pathlib import Path

import typer

from madkhal.contract import export as contract_export
from madkhal.core import claims as claimslib
from madkhal.core import paths
from madkhal.core import traceability as tr
from madkhal.evidence import NadhirSnapshot

app = typer.Typer(add_completion=False, no_args_is_help=True, help=__doc__)
docs_app = typer.Typer(add_completion=False, no_args_is_help=True, help="Documentation build.")
app.add_typer(docs_app, name="docs")

os.environ.setdefault("PYTHONUTF8", "1")


def _echo(msg: str) -> None:
    typer.echo(msg)


# ---------------------------------------------------------------- docs
def parameter_exists(key: str) -> bool:
    """Resolve a claims ``parameter`` pointer against the model registries."""
    return key in _parameter_keys()


def _parameter_keys() -> set[str]:
    keys: set[str] = set()
    return keys


def render_docs(root: Path) -> dict[Path, str]:
    """Return every generated document as {path: text}. Pure apart from reading inputs."""
    docs = root / "docs"
    out: dict[Path, str] = {}
    for rel, text in contract_export.artefacts().items():
        out[root / rel] = text
    m = tr.build_matrix(docs / "requirements.yaml", root / "tests", root / "web")
    out[docs / "TRACEABILITY.md"] = tr.render_markdown(m)
    cl = claimslib.load_claims(docs / "claims.yaml")
    out[docs / "CLAIMS.md"] = claimslib.render_markdown(cl)
    return out


@docs_app.command("build")
def docs_build() -> None:
    """Render generated documents (traceability, claims) from their sources."""
    root = paths.repo_root()
    for path, text in render_docs(root).items():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(text.encode("utf-8"))
        _echo(f"wrote {path.relative_to(root).as_posix()}")


# ---------------------------------------------------------------- check
def _run(label: str, cmd: list[str], root: Path) -> bool:
    t0 = time.perf_counter()
    env = dict(os.environ, PYTHONUTF8="1")
    proc = subprocess.run(
        cmd,
        cwd=root,
        env=env,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    ok = proc.returncode == 0
    dt = time.perf_counter() - t0
    _echo(f"[{'PASS' if ok else 'FAIL'}] {label} ({dt:.1f} s)")
    if not ok:
        _echo((proc.stdout + proc.stderr)[-4000:])
    return ok


def check_traceability(root: Path) -> list[str]:
    problems: list[str] = []
    m = tr.build_matrix(root / "docs" / "requirements.yaml", root / "tests", root / "web")
    for rid in m.untested("MUST"):
        problems.append(f"MUST requirement {rid} has no test")
    for rid, tests in m.unknown_refs.items():
        problems.append(f"tests reference unknown requirement {rid}: {tests[0]}")
    return problems


def check_claims(root: Path) -> list[str]:
    problems: list[str] = []
    opened = claimslib.load_opened_sources(root / "docs" / "sources_opened.yaml")
    snap = NadhirSnapshot()
    for c in claimslib.load_claims(root / "docs" / "claims.yaml"):
        reason = claimslib.resolve(c, root, opened, parameter_exists, snap.has_reference)
        if reason:
            problems.append(f"{c.id}: {reason}")
    return problems


def check_generated(root: Path) -> list[str]:
    stale = []
    for path, text in render_docs(root).items():
        if not path.is_file() or path.read_text(encoding="utf-8") != text:
            stale.append(f"{path.relative_to(root).as_posix()} is stale; run madkhal docs build")
    return stale


@app.command()
def check(
    skip_tests: bool = typer.Option(
        False, help="Skip the unit tests (lint, types, contracts only)."
    ),
) -> None:
    """Fast check: lint, types, import contracts, traceability, claims, unit tests."""
    root = paths.repo_root()
    py = sys.executable
    results = [
        _run("ruff lint", [py, "-m", "ruff", "check", "src", "tests"], root),
        _run("ruff format", [py, "-m", "ruff", "format", "--check", "src", "tests"], root),
        _run("mypy --strict src", [py, "-m", "mypy", "src"], root),
        _run("import contracts", [py, "-c", _LINT_IMPORTS], root),
    ]
    for label, fn in (
        ("traceability", check_traceability),
        ("claims register", check_claims),
        ("generated documents fresh", check_generated),
    ):
        problems = fn(root)
        _echo(f"[{'PASS' if not problems else 'FAIL'}] {label}")
        for p in problems[:20]:
            _echo(f"    {p}")
        results.append(not problems)
    if not skip_tests:
        results.append(
            _run(
                "unit tests",
                [py, "-m", "pytest", "-m", "not slow", "-q", "-x", "-p", "no:cacheprovider"],
                root,
            )
        )
    if not all(results):
        _echo("madkhal check: FAILED")
        raise typer.Exit(code=1)
    _echo("madkhal check: passed")


_LINT_IMPORTS = (
    "import sys; from importlinter.cli import lint_imports; "
    "sys.exit(lint_imports(config_filename='pyproject.toml', no_cache=True))"
)


def _print_json(obj: object) -> None:
    from madkhal.core.jsonio import dumps

    sys.stdout.buffer.write(dumps(obj).encode("utf-8"))


@app.command()
def evidence(site: str = typer.Option("kalba", help="OLCI site: kalba, barka or alraha.")) -> None:
    """Print the coverage counts per year and the detector track record."""
    from madkhal.evidence import yearly_counts
    from madkhal.lab.inputs import snapshot

    snap = snapshot()
    tr_ = snap.track_record()
    _print_json(
        {
            "site": site,
            "years": yearly_counts(snap.evidence_days(site)),
            "track_record": {
                "n_dated": tr_.n_dated,
                "n_observable": tr_.n_observable,
                "n_detected": tr_.n_detected,
                "rows": [r.model_dump(mode="json") for r in tr_.rows],
            },
        }
    )


@app.command()
def belief(
    site: str = typer.Option("kalba"),
    date: str = typer.Option("2018-09-08", help="ISO date within the evidence range."),
    draws: int = typer.Option(400, min=1, max=4000),
    seed: int = typer.Option(7, min=0),
) -> None:
    """Print the belief for one site and day (real evidence)."""
    import datetime as dt

    from madkhal.lab.replay import belief_replay

    bs = belief_replay(site, draws, seed)
    _print_json(bs.to_belief(bs.index_of(dt.date.fromisoformat(date))).model_dump(mode="json"))


@app.command()
def replay(
    site: str = typer.Option("kalba"),
    draws: int = typer.Option(400, min=1, max=4000),
    seed: int = typer.Option(7, min=0),
) -> None:
    """REPLAY: real satellite evidence, hypothetical plant. Belief before each event."""
    from madkhal.lab.replay import belief_at_events

    _print_json(belief_at_events(site, draws, seed))


@app.command("eval")
def eval_(
    smoke: bool = typer.Option(False, help="Run the quick E1 smoke check only."),
    seed: int = typer.Option(1, min=0),
) -> None:
    """Run the experiments (E1 to E7). With --smoke, one synthetic year of E1 only."""
    from madkhal.lab.smoke import e1_smoke

    if smoke:
        _print_json(e1_smoke(seed))
        return
    _echo("The full experiment suite is built in phase P6 and P7.")
    raise typer.Exit(code=2)


@app.command()
def snapshot(
    out: Path = typer.Option(Path("web/public/api"), help="Output folder for the static demo."),
) -> None:
    """Write every API response the web app needs as static JSON (static demo mode)."""
    from madkhal.api.static import build_static

    root = paths.repo_root()
    target = out if out.is_absolute() else root / out
    files = build_static(target)
    _echo(
        f"wrote {len(files)} files to {target.relative_to(root).as_posix() if target.is_relative_to(root) else target}"
    )


@app.command()
def serve(
    host: str = typer.Option("127.0.0.1"),
    port: int = typer.Option(8000, min=1, max=65535),
) -> None:
    """Start the live API (runs until stopped with Ctrl+C)."""
    import uvicorn

    uvicorn.run("madkhal.api.app:app", host=host, port=port, log_level="info")


def main() -> None:
    app()


if __name__ == "__main__":
    main()
