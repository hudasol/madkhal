import { useMutation, useQuery } from "@tanstack/react-query";
import { MODE, getJson } from "./client";
import type {
  AdvisoryResponse,
  BeliefSeries,
  ClaimsResponse,
  EvidenceResponse,
  Health,
  MethodResponse,
  MissionResponse,
  PlantProfileResponse,
  PoliciesResults,
  ReplayResponse,
  ScenarioRequest,
  ScenarioResponse,
  SensitivityResponse,
  Site,
  TimelineResponse,
  TrackRecordResponse,
} from "./types";

const forever = { staleTime: Infinity, gcTime: Infinity } as const;

export function useHealth() {
  return useQuery({
    queryKey: ["health"],
    queryFn: () => getJson<Health>("/v1/health"),
    ...forever,
  });
}

export function useSites() {
  return useQuery({ queryKey: ["sites"], queryFn: () => getJson<Site[]>("/v1/sites"), ...forever });
}

export function useSeries(site: string) {
  return useQuery({
    queryKey: ["series", site],
    queryFn: () => getJson<BeliefSeries>(`/v1/belief/${site}/series`),
    ...forever,
  });
}

export function useEvidence(site: string) {
  return useQuery({
    queryKey: ["evidence", site],
    queryFn: () => getJson<EvidenceResponse>(`/v1/evidence/${site}`),
    ...forever,
  });
}

export function useTrackRecord() {
  return useQuery({
    queryKey: ["track-record"],
    queryFn: () => getJson<TrackRecordResponse>("/v1/track-record"),
    ...forever,
  });
}

/** Advisory for a site. In static mode only the precomputed latest day exists. */
export function useAdvisory(site: string, date?: string) {
  const d = MODE === "static" ? undefined : date;
  return useQuery({
    queryKey: ["advisory", site, d ?? "latest"],
    queryFn: () => getJson<AdvisoryResponse>(`/v1/advisory/${site}`, { date: d }),
    ...forever,
  });
}

export function useTimeline(site: string, start?: string, end?: string) {
  const s = MODE === "static" ? undefined : start;
  const e = MODE === "static" ? undefined : end;
  return useQuery({
    queryKey: ["timeline", site, s ?? "", e ?? ""],
    queryFn: () => getJson<TimelineResponse>(`/v1/timeline/${site}`, { start: s, end: e }),
    ...forever,
  });
}

export function usePlantProfile() {
  return useQuery({
    queryKey: ["plant-profile"],
    queryFn: () => getJson<PlantProfileResponse>("/v1/plant/profile"),
    ...forever,
  });
}

export function useSensitivity() {
  return useQuery({
    queryKey: ["plant-sensitivity"],
    queryFn: () => getJson<SensitivityResponse>("/v1/plant/sensitivity"),
    ...forever,
  });
}

export function usePolicies() {
  return useQuery({
    queryKey: ["policies"],
    queryFn: () => getJson<PoliciesResults>("/v1/policies/results"),
    ...forever,
  });
}

export function useReplay(site: string) {
  return useQuery({
    queryKey: ["replay", site],
    queryFn: () => getJson<ReplayResponse>(`/v1/replay/${site}`),
    ...forever,
  });
}

export function useMethod() {
  return useQuery({
    queryKey: ["method"],
    queryFn: () => getJson<MethodResponse>("/v1/method"),
    ...forever,
  });
}

export function useClaims() {
  return useQuery({
    queryKey: ["claims"],
    queryFn: () => getJson<ClaimsResponse>("/v1/claims"),
    ...forever,
  });
}

export function useMission(site: string, params: Record<string, number | string | undefined>) {
  const p = MODE === "static" ? {} : params;
  return useQuery({
    queryKey: ["mission", site, JSON.stringify(p)],
    queryFn: () => getJson<MissionResponse>(`/v1/missions/${site}`, p),
    ...forever,
  });
}

/** Precomputed scenario presets (used in static mode, where POST is not available). */
export function usePreset(name: string, enabled: boolean) {
  return useQuery({
    queryKey: ["preset", name],
    queryFn: () => getJson<ScenarioResponse>(`/v1/scenario/presets/${name}`, undefined, "static"),
    ...forever,
    enabled,
  });
}

export function useScenario() {
  return useMutation({
    mutationFn: async (body: ScenarioRequest): Promise<ScenarioResponse> => {
      const res = await fetch("/v1/scenario/advise", {
        method: "POST",
        headers: { "content-type": "application/json", accept: "application/json" },
        body: JSON.stringify(body),
      });
      if (!res.ok) {
        const p = (await res.json().catch(() => ({}))) as { title?: string; detail?: string };
        throw new Error(`${p.title ?? res.status}: ${p.detail ?? ""}`);
      }
      return (await res.json()) as ScenarioResponse;
    },
  });
}
