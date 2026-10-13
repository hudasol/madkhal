// SYNTHETIC TEST FIXTURES: small hand made responses for component tests. Not data.
import type { BeliefSeries, EvidenceResponse, Site, TrackRecordResponse } from "../api/types";

const dates = ["2020-01-01", "2020-01-02", "2020-01-03"];
const band = (m: number) => ({
  lo: [m / 2, m / 2, m / 2],
  median: [m, m, m],
  hi: [m * 2, m * 2, m * 2],
});

export const sites: Site[] = ["kalba", "barka", "alraha"].map((id, i) => ({
  id,
  name: ["Kalba", "Barka", "Al Raha"][i]!,
  name_ar: ["كلباء", "بركاء", "الراحة"][i]!,
  dataset: "olci_v1",
  lat: 25,
  lon: 56,
  coord_status: "ESTIMATED",
  offshore_bearing_deg: 90,
  first_date: dates[0]!,
  last_date: dates[2]!,
  radii_km: [25, 50, 100],
  primary_radius_km: 50,
}));

export function series(site: string): BeliefSeries {
  return {
    site,
    start: dates[0]!,
    end: dates[2]!,
    level: 0.9,
    n_draws: 400,
    seed: 7,
    dates,
    clear: [true, false, true],
    alert: [false, false, true],
    staleness_days: [0, 1, 0],
    p_any_bloom: band(0.2),
    p_at_intake: band(0.05),
    within_1: band(0.06),
    within_3: band(0.1),
    within_7: band(0.2),
  };
}

export function evidence(site: string): EvidenceResponse {
  return {
    site,
    radius_km: 50,
    dataset: "olci_v1",
    first_date: dates[0]!,
    last_date: dates[2]!,
    dates,
    state: ["clear", "nodata", "alert"],
    anomaly_fraction: [0, null, 0.6],
    years: { "2020": { days: 3, clear: 2, alert: 1, nodata: 1 } },
    monthly_clear: {},
    events: [
      {
        id: "E-TEST",
        label: "Test place 2020, synthetic event",
        site,
        dataset: "olci_v1",
        lat: 25,
        lon: 56,
        coord_status: "ESTIMATED",
        date_precision: "day",
        t_ref: "2020-01-03",
        t_ref_earliest: "2020-01-01",
        evaluation: "EVALUATED",
        evidence_status: "UNVERIFIED",
        status_class: "UNVERIFIED",
        status_badge: "UNVERIFIED",
        source_file: "events.yaml",
        source_index: 1,
      },
    ],
    source_file: "olci_v1/zone_daily_r50.csv",
  };
}

export const trackRecord: TrackRecordResponse = {
  n_dated: 5,
  n_observable: 3,
  n_detected: 1,
  n_missed: 2,
  n_not_observable: 2,
  hit_rate: { k: 1, n: 3, rate: 1 / 3, note: "" },
  observable_rule: "rule",
  rows: [
    {
      event_id: "E-TEST",
      label: "Test place 2020, synthetic event",
      dataset: "olci_v1",
      outcome: "DETECTED",
      nadhir_outcome: "DETECTED",
      clear_days_in_lookback: 33,
      days_in_lookback: 121,
      lead_alert_days: 8,
      lead_alert_min_days: -6,
      evidence_status: "UNVERIFIED",
      status_class: "UNVERIFIED",
      source_file: "f.csv",
      source_row: 1,
    },
  ],
  false_alarms: [
    {
      site: "kalba",
      dataset: "olci_v1",
      radius_km: 50,
      alert_days: { k: 19, n: 426, rate: 19 / 426, note: "" },
      episodes: 5,
      quiet_days: 830,
      episodes_per_year: 2.2,
      source_file: "f.csv",
      source_row: 1,
    },
  ],
  blind_spot_note: "note",
  lead_time: {
    event_id: "E-TEST",
    lead_alert_days: 8,
    lead_alert_min_days: -6,
    n: 1,
    note: "",
    source: "f.csv row 1",
  },
  events: [],
};

export function route(url: string): unknown {
  const path = url
    .replace(/^.*?(\/v1\/)/, "/v1/")
    .replace(/\.json$/, "")
    .split("?")[0]!;
  if (path === "/v1/sites") return sites;
  if (path === "/v1/track-record") return trackRecord;
  const m = path.match(/^\/v1\/belief\/([a-z]+)\/series$/);
  if (m) return series(m[1]!);
  const e = path.match(/^\/v1\/evidence\/([a-z]+)$/);
  if (e) return evidence(e[1]!);
  if (path === "/v1/health") return { status: "ok" };
  return null;
}
