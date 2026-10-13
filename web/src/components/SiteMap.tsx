import { useEffect, useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import "maplibre-gl/dist/maplibre-gl.css";

// Schematic site map: MapLibre with local GeoJSON only. No tile service, no glyph server and
// no other network request; labels are HTML markers, not map text layers.

export interface MapProps {
  lat: number;
  lon: number;
  path: Array<[number, number]>; // [lon, lat]
  label: string;
}

function circle(lat: number, lon: number, km: number, n = 72): Array<[number, number]> {
  const out: Array<[number, number]> = [];
  for (let i = 0; i <= n; i += 1) {
    const a = (2 * Math.PI * i) / n;
    const dLat = (km / 111.32) * Math.cos(a);
    const dLon = (km / (111.32 * Math.cos((lat * Math.PI) / 180))) * Math.sin(a);
    out.push([lon + dLon, lat + dLat]);
  }
  return out;
}

function cssVar(name: string, fallback: string): string {
  const v = getComputedStyle(document.documentElement).getPropertyValue(name).trim();
  return v || fallback;
}

export function SiteMap({ lat, lon, path, label }: MapProps) {
  const { t } = useTranslation();
  const ref = useRef<HTMLDivElement | null>(null);
  const [failed, setFailed] = useState(false);
  const mapRef = useRef<{ flyTo: (o: { center: [number, number]; zoom: number }) => void } | null>(
    null,
  );
  const [close, setClose] = useState(false);
  useEffect(() => {
    let map: { remove: () => void } | null = null;
    let cancelled = false;
    void (async () => {
      try {
        const maplibre = (await import("maplibre-gl")).default;
        if (cancelled || !ref.current) return;
        const base = import.meta.env.BASE_URL.endsWith("/")
          ? import.meta.env.BASE_URL
          : `${import.meta.env.BASE_URL}/`;
        const coast = new URL(`${base}geo/coastline.geojson`, window.location.href).toString();
        const zones = {
          type: "FeatureCollection" as const,
          features: [25, 50, 100].map((km) => ({
            type: "Feature" as const,
            properties: { km },
            geometry: { type: "LineString" as const, coordinates: circle(lat, lon, km) },
          })),
        };
        const m = new maplibre.Map({
          container: ref.current,
          center: [lon, lat],
          zoom: 7,
          attributionControl: false,
          style: {
            version: 8,
            sources: {
              coast: { type: "geojson", data: coast },
              zones: { type: "geojson", data: zones },
              mission: {
                type: "geojson",
                data: {
                  type: "Feature",
                  properties: {},
                  geometry: { type: "LineString", coordinates: path },
                },
              },
            },
            layers: [
              {
                id: "bg",
                type: "background",
                paint: { "background-color": cssVar("--surface-2", "#fffdfb") },
              },
              {
                id: "coast",
                type: "line",
                source: "coast",
                paint: { "line-color": cssVar("--ink", "#5b3a4a"), "line-width": 1.5 },
              },
              {
                id: "zones",
                type: "line",
                source: "zones",
                paint: {
                  "line-color": cssVar("--band", "#d9728f"),
                  "line-width": 2,
                  "line-dasharray": [3, 2],
                },
              },
              {
                id: "mission",
                type: "line",
                source: "mission",
                paint: { "line-color": cssVar("--inspect", "#24507a"), "line-width": 2.5 },
              },
            ],
          },
        });
        m.addControl(
          new maplibre.AttributionControl({
            compact: true,
            customAttribution: "Coastline: Natural Earth (public domain)",
          }),
        );
        m.addControl(new maplibre.NavigationControl({ showCompass: false }));
        const el = document.createElement("div");
        el.className = "map-label";
        el.textContent = label;
        new maplibre.Marker({ element: el, anchor: "bottom", offset: [0, -14] })
          .setLngLat([lon, lat])
          .addTo(m);
        map = m;
        mapRef.current = m;
      } catch {
        if (!cancelled) setFailed(true);
      }
    })();
    return () => {
      cancelled = true;
      map?.remove();
    };
  }, [lat, lon, path, label]);
  return (
    <figure className="chart" aria-label={t("inspection.mapDesc")}>
      <figcaption>
        <strong>{t("inspection.map")}</strong>. {t("inspection.mapDesc")}
      </figcaption>
      <button
        type="button"
        className="btn"
        aria-pressed={close}
        onClick={() => {
          const next = !close;
          setClose(next);
          const mid = path[Math.floor(path.length / 2)] ?? [lon, lat];
          mapRef.current?.flyTo(
            next
              ? { center: [(lon + mid[0]) / 2, (lat + mid[1]) / 2], zoom: 11.5 }
              : { center: [lon, lat], zoom: 7 },
          );
        }}
      >
        {close ? t("inspection.zoomZones") : t("inspection.zoomSurvey")}
      </button>
      {failed ? (
        <p className="state" role="status">
          {t("state.partial")}
        </p>
      ) : (
        <div
          ref={ref}
          className="site-map"
          role="region"
          aria-label={`${t("inspection.map")}. ${t("inspection.mapDesc")}`}
        />
      )}
    </figure>
  );
}
