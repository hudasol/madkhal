# ADR 0009: A second, structurally different generator (G2)

**Status:** accepted (P6).

## Context

A policy tuned and evaluated on a world built from its own assumptions will look good for
circular reasons. Generator G1 is exactly that world: the estimator's model at its posterior
means, with Kalba's real clear sky shares. It is useful to check that the machinery works, and
it flatters the method.

## Decision

Every policy is also evaluated on G2, which changes the structure rather than the parameters:

| Assumption of the method | How G2 breaks it |
|---|---|
| Bloom load has the profile's Pareto tail | Tail index multiplied by 0.6 (heavier tail) |
| Detector misses are independent from day to day | After a miss in a bloom, the next clear day misses with probability 0.8 |
| Coverage follows Kalba's real monthly clear shares | June to September clear shares multiplied by 0.4 (longer blind season) |
| Invisible blooms come only from the blind spot share | An extra stream of species events at 0.5 per year that the satellite never sees |
| False alarms are independent | False alarms cluster into episodes with about the same marginal rate |

No policy setting is tuned on G2, and none is changed after seeing G2 results. The
preregistration predicts in advance that Madkhal degrades on G2 and that the simple seasonal
rule beats it there (PR-E3-2, PR-E3-3).

## Consequences

The G1 to G2 contrast is reported beside every result. Where Madkhal loses, the policy
comparison screen says so plainly.
