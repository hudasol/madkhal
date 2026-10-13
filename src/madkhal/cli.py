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
    for c in claimslib.load_claims(root / "docs" / "claims.yaml"):
        reason = claimslib.resolve(c, root, opened, parameter_exists)
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


def main() -> None:
    app()


if __name__ == "__main__":
    main()
