import { useQuery } from "@tanstack/react-query";
import { getJson } from "./client";
import type { BeliefSeries, EvidenceResponse, Health, Site, TrackRecordResponse } from "./types";

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
