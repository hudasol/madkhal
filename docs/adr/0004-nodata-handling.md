# ADR 0004: A nodata day is missing information, not evidence of calm

**Status:** accepted (P3).

## Context

On most days the satellite has no usable view of the watch zone (OLCI: 30 to 70 percent of
days are observable; MODIS: 16 to 29 percent, per Nadhir `outputs/RESULTS.md` and the
snapshot's `coverage.csv`). A tool that treats "no alert" on a blind day
as "quiet" would grow falsely confident exactly when it knows least.

## Decision

On a nodata day the observation update is skipped: the belief is the propagated prior, bit
for bit (test `test_nodata_day_equals_prior_propagation`). The staleness (days since the last
clear view) is reported beside every belief. With no data at all the belief equals the
seasonal prior (test `test_no_data_belief_equals_seasonal_prior`).

## What this guarantees, and what it does not

* Guaranteed: a nodata day never moves the belief further from the seasonal prior. Both are
  propagated by the same Markov kernel, and a Markov kernel cannot increase the total
  variation distance between two distributions (property test over random histories).
* Not guaranteed, and not desirable: that a nodata day never narrows the credible interval.
  After alerts, a run of blind days lets the belief relax back toward the seasonal prior, so
  the spread across draws can shrink; and a quiet clear day can give a wider interval than a
  nodata day because draws with different detector visibility react differently to it. A test
  demonstrates the second case. See `docs/DECISIONS.md` D-008.
