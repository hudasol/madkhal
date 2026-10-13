# Pilot path (proposal)

This is a proposal for how Madkhal could be calibrated with an operator's own data. Nothing
here has been agreed with, requested by or shared with any operator. Madkhal is advisory
software for planning and learning; any pilot would be read only and would connect to no
plant control system.

## What would move the plant model from L0 to L2

Every plant parameter is an assumption today (evidence level L0). Field calibration (L2)
needs the following, as time series with timestamps in UTC:

| Data | Used for | Parameters it would calibrate |
|---|---|---|
| Intake logs: flow, open and close times, derating decisions | the actions actually taken | design flow, demand share, restart time |
| Turbidity and organic load at the intake and after pretreatment (or SDI, UV254, chlorophyll probes) | the load index L and breakthrough | background load, bloom load lower bound and tail, pretreatment capacity, coagulant boost |
| Fouling sensor series: pretreatment differential pressure, RO normalised differential pressure and permeability | the fouling index F | fouling rate per unit breakthrough, fouling after cleaning |
| Shutdown and cleaning logs with start and end times and causes | forced shutdowns and their duration | cleaning hours, restart hours, planned cleaning threshold |
| Product water storage levels and demand | water security | storage capacity, demand share |
| Dates of past bloom related disruptions from operator records | replacing news report dates | the event reference dates (today UNVERIFIED upper bounds) and the detector hit rate |

## Data sharing checklist (proposal)

* A written data sharing agreement that names the purpose (research and learning), the
  retention period and deletion at the end.
* Read only exports (CSV or parquet) delivered offline; no network connection to plant systems.
* No personal data: equipment series and logs only; operator names removed from free text.
* Site identity may be withheld; coordinates can be offset if the operator prefers.
* Results shared back with the operator before any publication; the operator decides whether a
  site may be named.

## What would change in the model

1. Each calibrated parameter's source changes from `assumption` to `field_calibrated`, its
   spread shrinks to the calibration uncertainty, and the profile's evidence level moves to L2.
   Because the decision samples uncertain parameters towards their adverse side (ADR 0007),
   smaller spreads directly relax over conservative advice.
2. Operator disruption dates replace news report dates, which tightens the lead time and the hit
   rate posteriors.
3. The fouling model would be compared with the recorded pressure series before use; if its
   structure does not fit, it would be replaced rather than tuned.
4. Validation would follow `docs/VALIDATION_PROTOCOL.md`: freeze, then score on held out
   periods, with predictions written first.
