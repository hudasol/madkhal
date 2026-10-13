# ADR 0005: Parameter posteriors from tiny samples are kept wide

**Status:** accepted (P3).

## Context

The detector parameters rest on very few events: one detection among three observable dated
events, one detected episode for the in bloom alert rate, and a few hundred clear quiet days
for the false alarm rate, with alerts that cluster into episodes.

## Decision

| Parameter | Data (Nadhir snapshot) | Posterior |
|---|---|---|
| alpha, false alarm rate per clear day (per site) | held out quiet alert days k of clear quiet days n, and the number of episodes e (`false_alarms.csv`, 50 km) | Jeffreys prior. Because alert days come in episodes, k and n are divided by the mean episode length k / e before the update: Beta(0.5 + e, 0.5 + n e / k - e). For Kalba: 19 of 426 days in 5 episodes gives Beta(5.5, 107.6). The uncorrected Beta(19.5, 407.5) is kept as a sensitivity option. |
| hit rate, event level | 1 detected of 3 observable dated events (`event_lead_times.csv`) | Jeffreys prior: Beta(1.5, 2.5), deliberately wide (a test asserts its 90 percent interval reaches below 0.1 and above 0.7). |
| species blind spot | one documented species level miss (Al Raha 2023) | ASSUMPTION: an extra invisible share Beta(1, 4) (mean 0.2). Visible share = hit rate times (1 minus blind spot). A sensitivity run compares none, Beta(1, 4) and Beta(2, 3). |
| beta_at, alert rate per clear day for a visible bloom at the intake | 6 alert days of 7 clear days in the one detected episode (Kalba 2018, first to last exceedance) | Weighted as 4 pseudo observations because it is one event: Beta(3.93, 1.07). |
| beta_dev | none | ASSUMPTION: beta_at times U(0.5, 1). |

## Consequences

Intervals on the belief are wide, as they should be. The posteriors must be revisited when
operator logs or more detected events become available (see `docs/PILOT.md`).
