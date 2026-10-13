// Response shapes of endpoints that are not single contract models.
import type {
  BloomBelief,
  Event,
  Site,
  TrackRow,
  FalseAlarmRow,
  RateWithCounts,
} from "../contract/types";

export type { BloomBelief, Event, Site };

export interface Band {
  lo: number[];
  median: number[];
  hi: number[];
}

export interface BeliefSeries {
  site: string;
  start: string;
  end: string;
  level: number;
  n_draws: number;
  seed: number;
  dates: string[];
  clear: boolean[];
  alert: boolean[];
  staleness_days: Array<number | null>;
  p_any_bloom: Band;
  p_at_intake: Band;
  within_1: Band;
  within_3: Band;
  within_7: Band;
}

export type DayState = "clear" | "nodata" | "alert";

export interface EvidenceResponse {
  site: string;
  radius_km: number;
  dataset: string;
  first_date: string;
  last_date: string;
  dates: string[];
  state: DayState[];
  anomaly_fraction: Array<number | null>;
  years: Record<string, { days: number; clear: number; alert: number; nodata: number }>;
  monthly_clear: Record<string, RateWithCounts>;
  events: Event[];
  source_file: string;
}

export interface TrackRecordResponse {
  n_dated: number;
  n_observable: number;
  n_detected: number;
  n_missed: number;
  n_not_observable: number;
  hit_rate: RateWithCounts;
  observable_rule: string;
  rows: TrackRow[];
  false_alarms: FalseAlarmRow[];
  blind_spot_note: string;
  lead_time: {
    event_id: string;
    lead_alert_days: number;
    lead_alert_min_days: number;
    n: number;
    note: string;
    source: string;
  };
  events: Event[];
}

export interface Health {
  status: string;
  version: string;
  evidence_commit: string;
  banner: { evidence: string; hypothetical: string };
  scope: string;
}

// ---------------------------------------------------------------- decision, lab, tasking
import type { Advisory, Mission, Parameter, Scenario } from "../contract/types";

export type AdvisoryResponse = Advisory;
export type ScenarioRequest = Partial<Scenario> & Pick<Scenario, "site" | "start_date" | "days">;

export interface TimelineResponse {
  label: string;
  site: string;
  start: string;
  end: string;
  dates: string[];
  action: string[];
  scale: number[];
  p_fouling: number[];
  p_water: number[];
  p_breach_full: number[];
  binding: Array<string | null>;
  dwell_held: boolean[];
  inspect: boolean[];
  clear: boolean[];
  alert: boolean[];
  within_3: Band;
  p_any_bloom: Band;
}

export interface PlantProfileResponse {
  id: string;
  name: string;
  hypothetical: true;
  description: string;
  parameters: Parameter[];
  assumption_share: number;
  evidence_level: string;
}

export interface SensitivityRow {
  key: string;
  label: string;
  role: string;
  rel_spread: number;
  swing_fouling: number;
  swing_water: number;
  score: number;
  rank: number;
}

export interface SensitivityResponse {
  method: string;
  rows: SensitivityRow[];
  measure_first: string[];
}

export interface Summary {
  mean: number;
  lo: number;
  hi: number;
  n: number;
  unit: string;
}

export interface PolicyBlock {
  name: string;
  metrics: Record<string, Summary>;
  regret_cu: Summary;
  regret_per_seed: number[];
}

export interface Comparison {
  generator: string;
  seeds: number[];
  policies: Record<string, PolicyBlock>;
  weights: Record<string, number>;
  weight_sensitivity: Record<string, { mean_regret_cu: Record<string, number>; ranking: string[] }>;
}

export interface Prediction {
  id: string;
  prediction: string;
  observed: string;
  result: "HIT" | "MISS" | "NOT RUN";
}

export interface PoliciesResults {
  e1: {
    brier: Record<string, Summary>;
    log_score: Record<string, Summary>;
    coverage90: Summary;
  };
  e2: Comparison;
  e3: Comparison & {
    drop: Record<string, { regret_g1_cu: number; regret_g2_cu: number; regret_change_cu: number }>;
  };
  e4: {
    grid: Array<{
      availability: number;
      sortie_cost_cu: number;
      p4_minus_p3_cu: Summary;
      sorties_per_year: Summary;
    }>;
    break_even: { break_even_cost_cu: number | null; note: string };
  };
  e5: { one_at_a_time: Array<{ key: string; swing_cu: number }>; measure_first: string[] };
  e6: { policies: Record<string, { changes_per_30_days: Summary; dwell_compliance: Summary }> };
  predictions: Prediction[];
  run: { seeds: number[]; seconds_total: number };
}

export interface ReplayPoint {
  event_id: string;
  label: string;
  status_badge: string;
  anchor: string;
  anchor_date: string;
  days_before: number;
  date: string;
  action?: string;
  scale?: number;
  p_any_bloom?: number[];
  within_3?: number[];
  note?: string;
}

export interface ReplayResponse {
  label: string;
  draws: number;
  site: string;
  by_year: Record<
    string,
    { days: number; non_go: number; quiet_days: number; quiet_non_go: number }
  >;
  quiet_non_go_per_year: number | null;
  quiet_days: number;
  quiet_non_go_days: number;
  outside_windows_non_go_per_year: number | null;
  points: ReplayPoint[];
}

export interface MethodResponse {
  scope: string;
  method_markdown: string;
  limitations_markdown: string;
  pilot_markdown: string;
  predictions: Prediction[];
  arabic_note: string;
}

export interface ClaimsResponse {
  types: string[];
  claims: Array<{
    id: string;
    text: string;
    type: string;
    where: string[];
    pointer: { kind: string; ref: string };
  }>;
}

export interface MissionResponse {
  label: string;
  notice: string;
  site: string;
  date: string;
  mission: Mission;
  wind: Array<{ hour_local: number; wind_ms: number; available: boolean }>;
  wind_note: string;
  availability: number;
  inspection: {
    value_cu: number;
    sortie_cost_cu: number;
    break_even_cost_cu: number;
    availability: number;
    decision_could_change: boolean;
    inspect: boolean;
    reasons: string[];
  };
  exports: { geojson: unknown; kml: string; plan: unknown };
  plan_valid: boolean;
}

export interface ScenarioDay {
  date: string;
  truth: "clear" | "developing" | "at_intake";
  clear: boolean;
  alert: boolean;
  p_any_bloom: number[];
  within_3: number[];
  action: string;
  scale: number;
  binding: string | null;
  fouling_index: number;
  storage_hours: number;
  unserved_m3: number;
  forced_shutdowns: number;
}

export interface ScenarioResponse {
  label: string;
  scenario: Scenario;
  days: ScenarioDay[];
  last_advisory: Advisory;
  totals: { unserved_m3: number; forced_shutdowns: number; cleanings: number };
  preset?: string;
}
