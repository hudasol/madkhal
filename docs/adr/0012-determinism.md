# ADR 0012: Determinism strategy

**Status:** accepted (P0, extended in P6 and P7).

## Context

Every advisory must be reproducible from its stored inputs and a seed, and every number in a
document must come from a file that code in the repository regenerates identically.

## Decision

1. **Explicit seeds.** Every stochastic step takes an integer seed. There is no global random
   state and no seed taken from the clock.
2. **Labelled sub streams.** `madkhal.core.determinism.substream(seed, label)` derives a numpy
   Generator from the SHA 256 of the seed and a text label, so adding a random step never
   shifts the numbers drawn by an existing one.
3. **Inputs hash identifiers.** Advisories and scenario results carry an id that is the
   SHA 256 of their canonical JSON inputs, so the same inputs give the same id.
4. **Stable serialisation.** JSON is written with sorted keys, UTF 8 with Arabic preserved,
   non finite numbers as null, and LF line endings on every platform (files are written as
   bytes, never through a text mode that would translate line endings on Windows).
5. **Parallel runs stay deterministic.** The experiment runner distributes seeds to worker
   processes and gathers results in task order (`Executor.map`), never by completion order.
   Each worker pins its numeric libraries to one thread (`OPENBLAS_NUM_THREADS=1` and related
   variables), which also avoids thread pools exhausting memory.
6. **Wall clock timings are kept apart.** `results/run.json` and `results/performance.json`
   record seconds and differ between runs; they are never used as inputs to any result.

## Consequences

Tests assert that replay, scenarios and advisories are identical across runs
(`tests/test_replay_cli.py`, `tests/test_api_decision.py`, `tests/test_decision.py`). Two full
runs of `madkhal eval` produced byte identical `results/e1.json` to `e7.json`
(`docs/PROGRESS.md`, P7).
