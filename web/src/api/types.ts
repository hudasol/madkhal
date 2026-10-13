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
