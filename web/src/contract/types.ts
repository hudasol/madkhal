// Generated from madkhal.contract.models by `madkhal docs build`. Do not edit by hand.
// Evidence: real satellite history from the Nadhir hindcast.
// Plant, drone and consequences: hypothetical, synthetic parameters.

/** Advisory action, ordered from most to least permissive. */
export type ActionKind = "GO" | "DERATE" | "PARK" | "NO_SAFE_OPTION_ESCALATE";
export const ActionKindValues = ["GO", "DERATE", "PARK", "NO_SAFE_OPTION_ESCALATE"] as const;

/** Latent bloom state of the estimator. */
export type BloomState = "clear" | "developing" | "at_intake";
export const BloomStateValues = ["clear", "developing", "at_intake"] as const;

/** Whether the satellite saw the watch zone on a day. */
export type CoverageState = "clear" | "nodata";
export const CoverageStateValues = ["clear", "nodata"] as const;

/** Which frozen Nadhir detector produced the evidence. */
export type Dataset = "olci_v1" | "modis_v1";
export const DatasetValues = ["olci_v1", "modis_v1"] as const;

/** Daily state reported by the frozen Nadhir detector. */
export type DetectorState = "NODATA" | "QUIET" | "EXCEED" | "ALERT";
export const DetectorStateValues = ["NODATA", "QUIET", "EXCEED", "ALERT"] as const;

/** How far a parameter or decision can be trusted (from Dhill). */
export type EvidenceLevel = "L0" | "L1" | "L2" | "L3";
export const EvidenceLevelValues = ["L0", "L1", "L2", "L3"] as const;

/** Where a parameter value comes from. */
export type ParamSource = "assumption" | "literature" | "nadhir" | "field_calibrated" | "validated";
export const ParamSourceValues = ["assumption", "literature", "nadhir", "field_calibrated", "validated"] as const;

/** Coarse class of a Nadhir evidence status, used for labels. */
export type StatusClass = "VERIFIED-PRIMARY" | "VERIFIED-SECONDARY" | "UNVERIFIED";
export const StatusClassValues = ["VERIFIED-PRIMARY", "VERIFIED-SECONDARY", "UNVERIFIED"] as const;

/** An advisory for one site and time. It is advice, never a control action. */
export interface Advisory {
  /** Identifier: the inputs hash. */
  id: string;
  /** Site identifier. */
  site: string;
  /** Time the advisory applies to (UTC). */
  issued_for: string;
  /** Advised action. */
  action: ActionKind;
  /** Advised flow scale q. */
  scale: number;
  /** Reasons in plain language. */
  reasons: Array<string>;
  /** Binding constraint. */
  binding_constraint?: string | null;
  /** P(fouling limit reached within the horizon at full scale). */
  p_breach_full_scale: number;
  /** Hours until the limit at full scale at the 95 percent risk quantile (absent if beyond the horizon). */
  time_to_limit_hours?: number | null;
  /** How close each constraint is. */
  constraints: Array<ConstraintStatus>;
  /** Evidence level of the advisory. */
  evidence_level: EvidenceLevel;
  /** Share of plant parameters that are assumptions. */
  assumption_share: number;
  /** INSPECT advisory (task a survey drone). */
  inspect: boolean;
  /** Reasons for or against INSPECT. */
  inspect_reasons: Array<string>;
  /** Structured explanation (required). */
  explanation: Explanation;
  /** Plain language rendering. */
  text: PlainText;
  /** SHA-256 of the canonical inputs. */
  inputs_hash: string;
  /** Seed used. */
  seed: number;
  /** Context label, for example the replay label. */
  label?: string;
}

/** A detector or transition parameter used by the estimator, with its posterior. */
export interface BeliefParameter {
  /** Parameter key. */
  key: string;
  /** Plain language name. */
  label: string;
  /** Posterior summary over draws. */
  value: Interval;
  /** Where the value comes from. */
  source: ParamSource;
  /** Counts or reasoning behind the value. */
  provenance: string;
}

/** The estimator's belief for one site and day. */
export interface BloomBelief {
  /** Site identifier. */
  site: string;
  /** Day of the belief (end of day, UTC). */
  date: string;
  /** P(clear). */
  p_clear: Interval;
  /** P(developing in the watch zone, not at the intake). */
  p_developing: Interval;
  /** P(bloom at the intake). */
  p_at_intake: Interval;
  /** P(developing or at the intake). */
  p_any_bloom: Interval;
  /** P(at_intake within 1, 3 and 7 days). */
  within: Array<HorizonProbability>;
  /** Days since the last clear satellite observation (absent if none yet). */
  staleness_days?: number | null;
  /** Coverage on this day. */
  observation: CoverageState;
  /** Detector alert on this day. */
  alert: boolean;
  /** Posterior parameter draws used. */
  n_draws: number;
  /** Seed of the parameter draws. */
  seed: number;
  /** Parameters used, with posteriors. */
  parameters: Array<BeliefParameter>;
}

/** Risk of one candidate action over the horizon. */
export interface CandidateEvaluation {
  /** Candidate action. */
  action: ActionKind;
  /** Flow scale q. */
  scale: number;
  /** P(fouling index reaches the limit). */
  p_fouling_breach: number;
  /** P(unserved water above the allowance). */
  p_water_breach: number;
  /** Expected unserved water. */
  expected_unserved_m3: number;
  /** Both risks within budget. */
  feasible: boolean;
}

/** How close a constraint is to its budget for the chosen action. */
export interface ConstraintStatus {
  /** Constraint name. */
  name: "fouling" | "water_security" | "dwell";
  /** Current value (probability or hours). */
  value: number;
  /** Budget or limit. */
  budget: number;
  /** Share of the budget used, capped at 100. */
  used_percent: number;
}

/** Hypothetical survey drone. */
export interface DroneProfile {
  /** Endurance. */
  endurance_min?: number;
  /** Cruise speed. */
  cruise_speed_ms?: number;
  /** Battery reserve kept back. */
  reserve_fraction?: number;
  /** Wind speed above which the drone does not fly. */
  wind_limit_ms?: number;
  /** Survey altitude. */
  altitude_m?: number;
}

/** A documented bloom related event, with its Nadhir evidence status kept verbatim. */
export interface Event {
  /** Nadhir event identifier. */
  id: string;
  /** Neutral label: place, year and kind. Names no operator. */
  label: string;
  /** Site identifier of the nearest evidence zone. */
  site: string;
  /** Detector that can score the event. */
  dataset: Dataset;
  /** Latitude (estimated). */
  lat: number;
  /** Longitude (estimated). */
  lon: number;
  /** Coordinate status from Nadhir. */
  coord_status: string;
  /** Precision of the documented date. */
  date_precision: string;
  /** Reference date (usually a report date, an upper bound on onset). */
  t_ref?: string | null;
  /** Earliest date consistent with the sources. */
  t_ref_earliest?: string | null;
  /** Start of a documented period, for period events. */
  period_start?: string | null;
  /** End of a documented period, for period events. */
  period_end?: string | null;
  /** How Nadhir scored the event. */
  evaluation: string;
  /** Evidence status copied verbatim from Nadhir. */
  evidence_status: string;
  /** Coarse class of the evidence status. */
  status_class: StatusClass;
  /** Short status label shown with the event; it says UNVERIFIED whenever any part is unverified. */
  status_badge: string;
  /** Species as stated by Nadhir, if any. */
  species?: string | null;
  /** Snapshot file the event came from. */
  source_file: string;
  /** Position of the event in the source file (1 based). */
  source_index: number;
}

/** One day of satellite evidence for one site and watch zone radius. */
export interface EvidenceDay {
  /** Calendar day (UTC). */
  date: string;
  /** Site identifier. */
  site: string;
  /** Watch zone radius. */
  radius_km: number;
  /** clear when the satellite had a usable view of the zone, nodata otherwise. */
  coverage: CoverageState;
  /** Whether the frozen detector was in alert. */
  alert: boolean;
  /** Detector state as written by Nadhir. */
  detector_state: DetectorState;
  /** Share of observed pixels that were anomalous, if observed. */
  anomaly_fraction?: number | null;
  /** Snapshot file the row came from. */
  source_file: string;
  /** Data row number in the source file (1 based). */
  source_row: number;
}

/** Structured explanation; the plain language text is rendered from it. */
export interface Explanation {
  /** Belief quantities used. */
  belief_summary: Record<string, number>;
  /** Plant state used. */
  plant_state: PlantState;
  /** Limits and budgets used. */
  limits: Limits;
  /** Every candidate with its risks. */
  candidates: Array<CandidateEvaluation>;
  /** Action before the dwell rule. */
  unconstrained_action: ActionKind;
  /** Scale before the dwell rule. */
  unconstrained_scale: number;
  /** Whether the dwell rule held a more restrictive action. */
  dwell_held: boolean;
  /** Constraint that stops a more permissive action. */
  binding_constraint?: string | null;
  /** Evidence level of the plant profile. */
  evidence_level: EvidenceLevel;
  /** Share of plant parameters that are assumptions. */
  assumption_share: number;
  /** Monte Carlo samples (posterior draws). */
  n_samples: number;
  /** Survey value assessment, if computed. */
  inspect?: InspectAssessment | null;
  /** Conditions that would change the advisory. */
  what_would_change: Array<string>;
}

/** Held out false alarm counts for one site, copied from Nadhir. */
export interface FalseAlarmRow {
  /** Site identifier. */
  site: string;
  /** Detector used. */
  dataset: Dataset;
  /** Watch zone radius. */
  radius_km: number;
  /** Alert days over clear quiet days in held out years. */
  alert_days: RateWithCounts;
  /** Alert episodes started in held out quiet days. */
  episodes: number;
  /** Calendar days in the held out quiet set. */
  quiet_days: number;
  /** Alert episodes per 365 days (an upper bound on false alarms). */
  episodes_per_year: number;
  /** Source file. */
  source_file: string;
  /** Data row in the source file (1 based). */
  source_row: number;
}

/** P(at_intake at any time within the horizon). */
export interface HorizonProbability {
  /** Forecast horizon. */
  horizon_days: number;
  /** Probability with interval. */
  p_at_intake: Interval;
}

/** Pre posterior value of a drone survey against its cost. */
export interface InspectAssessment {
  /** Expected reduction in loss from one survey, in cost units (hypothetical). */
  value_cu: number;
  /** Cost of one sortie (hypothetical). */
  sortie_cost_cu: number;
  /** Sortie cost at which the survey just pays. */
  break_even_cost_cu: number;
  /** Probability that weather allows the sortie. */
  availability: number;
  /** Whether some survey outcome changes the best action. */
  decision_could_change: boolean;
  /** INSPECT advisory set. */
  inspect: boolean;
  /** Reasons in plain language. */
  reasons: Array<string>;
}

/** Posterior median with an equal tailed credible interval. */
export interface Interval {
  /** Posterior median. */
  median: number;
  /** Lower bound of the credible interval. */
  lo: number;
  /** Upper bound of the credible interval. */
  hi: number;
  /** Credible level, for example 0.9. */
  level: number;
}

/** Hard limits and risk budgets of the decision. */
export interface Limits {
  /** Fouling index hard limit. */
  fouling_limit?: number;
  /** Largest allowed P(fouling breach) over the horizon. */
  fouling_risk_budget?: number;
  /** Unserved water allowed over the horizon before it counts as a breach. */
  water_allowance_m3?: number;
  /** Largest allowed P(unserved water above the allowance). */
  water_risk_budget?: number;
  /** Decision horizon. */
  horizon_hours?: number;
  /** Minimum time before a less restrictive change. */
  dwell_hours?: number;
}

/** Mean of a metric over seeds with a 95 percent interval. */
export interface MetricSummary {
  /** Mean over seeds. */
  mean: number;
  /** Lower 95 percent bound of the mean. */
  lo: number;
  /** Upper 95 percent bound of the mean. */
  hi: number;
  /** Unit. */
  unit: string;
  /** Number of seeds. */
  n: number;
}

/** A survey mission. For simulation and review only. */
export interface Mission {
  /** Identifier: the inputs hash. */
  id: string;
  /** Site identifier. */
  site: string;
  /** Survey radius offshore of the intake. */
  radius_m: number;
  /** Spacing of survey lines. */
  line_spacing_m: number;
  /** Drone profile. */
  drone: DroneProfile;
  /** Waypoints in order, starting and ending at home. */
  waypoints: Array<Waypoint>;
  /** Total path length. */
  distance_m: number;
  /** Flight time at cruise speed. */
  flight_time_s: number;
  /** Endurance less reserve. */
  usable_time_s: number;
  /** Whether the mission fits the profile. */
  feasible: boolean;
  /** Why a mission was refused. */
  refused_reason?: string | null;
  /** Simulation only statement (always present). */
  notice: "For simulation and review only. Real flights need the operator's own safety case and the regulator's approval.";
}

/** A model parameter with provenance. The evidence level is required. */
export interface Parameter {
  /** Parameter key. */
  key: string;
  /** Plain language name. */
  label: string;
  /** Nominal value. */
  value: number;
  /** Unit of the value. */
  unit: string;
  /** Evidence level of this parameter. */
  evidence_level: EvidenceLevel;
  /** Where the value comes from. */
  source: ParamSource;
  /** Reasoning or citation behind the value. */
  provenance: string;
  /** Relative spread (one standard deviation on the log scale). */
  rel_spread: number;
  /** Direction in which the parameter makes outcomes worse. */
  adverse: "up" | "down";
}

/** Three sentences rendered from the explanation. */
export interface PlainText {
  /** What to do. */
  what: string;
  /** Why. */
  why: string;
  /** What would change this. */
  change: string;
}

/** A hypothetical plant. Every parameter carries an evidence level and provenance. */
export interface PlantProfile {
  /** Profile identifier. */
  id: string;
  /** Profile name. */
  name: string;
  /** Always true: no real plant is modelled. */
  hypothetical: true;
  /** What the profile represents. */
  description: string;
  /** All parameters. */
  parameters: Array<Parameter>;
}

/** Current state of the hypothetical plant. */
export interface PlantState {
  /** Current fouling index (1 is the hard limit). */
  fouling_index?: number;
  /** Product water in storage, in hours of demand. */
  storage_hours?: number;
  /** Action in force. */
  current_action?: ActionKind;
  /** Flow scale in force. */
  current_scale?: number;
  /** Hours since the action in force began. */
  hours_in_action?: number;
}

/** Results of one policy on one generator. */
export interface PolicyResult {
  /** Policy identifier. */
  policy: string;
  /** Scenario generator. */
  generator: "G1" | "G2";
  /** Seeds run. */
  n_seeds: number;
  /** Every metric, never collapsed. */
  metrics: Record<string, MetricSummary>;
}

/** A rate that always travels with its counts. */
export interface RateWithCounts {
  /** Numerator count. */
  k: number;
  /** Denominator count. */
  n: number;
  /** k / n, absent when n is zero. */
  rate?: number | null;
  /** What the counts mean. */
  note?: string;
}

/** A user bloom scenario for the Scenario Lab (synthetic). */
export interface Scenario {
  /** Site whose seasonality and coverage are used. */
  site: string;
  /** First day. */
  start_date: string;
  /** Scenario length. */
  days: number;
  /** Day the bloom enters the watch zone (absent for none). */
  onset_day?: number | null;
  /** Days from watch zone to intake. */
  days_to_intake?: number;
  /** Days the bloom stays at the intake. */
  duration_days?: number;
  /** Bloom load added at the intake, relative to the design load. */
  intensity?: number;
  /** Share of days with a clear satellite view. */
  detector_availability?: number;
  /** Whether the bloom is visible to the broadband detector. */
  detector_visible?: boolean;
  /** Seed. */
  seed?: number;
}

/** A place with satellite evidence. Coordinates are estimated, never surveyed. */
export interface Site {
  /** Site identifier used by Nadhir. */
  id: string;
  /** Place name in English. */
  name: string;
  /** Place name in Arabic. */
  name_ar: string;
  /** Frozen detector that covers this site. */
  dataset: Dataset;
  /** Latitude of the estimated intake position. */
  lat: number;
  /** Longitude of the estimated intake position. */
  lon: number;
  /** Status of the coordinates (ESTIMATED in every case). */
  coord_status: string;
  /** Assumed bearing from the intake towards open water, used only to draw survey missions. */
  offshore_bearing_deg: number;
  /** First day of evidence. */
  first_date: string;
  /** Last day of evidence. */
  last_date: string;
  /** Watch zone radii available. */
  radii_km: Array<number>;
  /** Watch zone radius used by default. */
  primary_radius_km: number;
}

/** Detector track record, small sample shown as small. */
export interface TrackRecord {
  /** Dated disruptions scored by Nadhir. */
  n_dated: number;
  /** Of those, how many were observable. */
  n_observable: number;
  /** Of the observable, how many were detected. */
  n_detected: number;
  /** Observable but missed. */
  n_missed: number;
  /** Not observable (satellite blind). */
  n_not_observable: number;
  /** Detected over observable. */
  hit_rate: RateWithCounts;
  /** Rule used to call an event observable. */
  observable_rule: string;
  /** One row per dated event. */
  rows: Array<TrackRow>;
  /** Held out false alarm rows. */
  false_alarms: Array<FalseAlarmRow>;
  /** The documented species level blind spot. */
  blind_spot_note: string;
}

/** Outcome of the detector for one dated event, cited to its source row. */
export interface TrackRow {
  /** Event identifier. */
  event_id: string;
  /** Neutral event label. */
  label: string;
  /** Detector used. */
  dataset: Dataset;
  /** Detected, missed, or not observable (too few clear days before the reference date). */
  outcome: "DETECTED" | "MISSED" | "NOT_OBSERVABLE";
  /** Outcome string written by Nadhir. */
  nadhir_outcome: string;
  /** Clear days in the lookback window. */
  clear_days_in_lookback: number;
  /** Days in the lookback window. */
  days_in_lookback: number;
  /** Days from first alert to the reference date. */
  lead_alert_days?: number | null;
  /** Lead time against the earliest date. */
  lead_alert_min_days?: number | null;
  /** Evidence status (verbatim). */
  evidence_status: string;
  /** Coarse class of the evidence status. */
  status_class: StatusClass;
  /** Source file. */
  source_file: string;
  /** Data row in the source file (1 based). */
  source_row: number;
}

/** A mission waypoint. */
export interface Waypoint {
  /** Latitude. */
  lat: number;
  /** Longitude. */
  lon: number;
  /** Altitude above the take off point. */
  alt_m: number;
}

export const SIMULATION_NOTICE = "For simulation and review only. Real flights need the operator's own safety case and the regulator's approval.";
export const BANNER_EVIDENCE = "Evidence: real satellite history from the Nadhir hindcast.";
export const BANNER_HYPOTHETICAL = "Plant, drone and consequences: hypothetical, synthetic parameters.";
export const REPLAY_LABEL = "REPLAY: real satellite evidence, hypothetical plant";
export const ADVISORY_SCOPE = "Advisory software for planning and learning. It controls nothing and has no connection to any plant system.";
