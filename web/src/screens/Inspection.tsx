import { useMemo, useState } from "react";
import { useTranslation } from "react-i18next";
import { MODE } from "../api/client";
import { useMission, useSites } from "../api/hooks";
import { ActionGlyph } from "../components/ActionBadge";
import { SiteMap } from "../components/SiteMap";
import { SiteSelect } from "../components/SiteSelect";
import { ErrorView, Loading } from "../components/StateView";
import { formatNumber, formatPercent } from "../format";
import { useSettings } from "../settings";

function download(name: string, text: string, type: string) {
  const url = URL.createObjectURL(new Blob([text], { type }));
  const a = document.createElement("a");
  a.href = url;
  a.download = name;
  a.click();
  URL.revokeObjectURL(url);
}

export function InspectionScreen() {
  const { t } = useTranslation();
  const s = useSettings();
  const sites = useSites();
  const [site, setSite] = useState("kalba");
  const [date, setDate] = useState("2018-09-08");
  const [radius, setRadius] = useState(3000);
  const [spacing, setSpacing] = useState(800);
  const q = useMission(site, { date, radius_m: radius, spacing_m: spacing });
  const info = sites.data?.find((x) => x.id === site);
  const path = useMemo<Array<[number, number]>>(
    () => (q.data ? q.data.mission.waypoints.map((w) => [w.lon, w.lat] as [number, number]) : []),
    [q.data],
  );
  const n = (x: number, d = 0) => formatNumber(x, s, d);
  return (
    <div className="stack">
      <h1>{t("inspection.title")}</h1>
      <p className="notice" role="note">
        <ActionGlyph action="INSPECT" /> <strong>{t("inspection.notice")}</strong>
      </p>
      <p>{t("inspection.intro")}</p>
      <div className="row">
        <SiteSelect value={site} onChange={setSite} />
        {MODE === "live" ? (
          <>
            <label className="row" style={{ gap: "0.3rem" }}>
              <span>{t("common.date")}</span>
              <input
                type="date"
                value={date}
                min="2018-01-01"
                max="2023-11-07"
                onChange={(e) => setDate(e.target.value)}
              />
            </label>
            <label className="row" style={{ gap: "0.3rem" }}>
              <span>{t("inspection.radius")}</span>
              <input
                type="number"
                min={500}
                max={20000}
                step={500}
                value={radius}
                onChange={(e) => setRadius(Number(e.target.value))}
              />
            </label>
            <label className="row" style={{ gap: "0.3rem" }}>
              <span>{t("inspection.spacing")}</span>
              <input
                type="number"
                min={100}
                max={5000}
                step={100}
                value={spacing}
                onChange={(e) => setSpacing(Number(e.target.value))}
              />
            </label>
          </>
        ) : (
          <span className="muted">{t("mode.staticNote")}</span>
        )}
      </div>
      {q.isLoading ? (
        <Loading />
      ) : q.isError || !q.data ? (
        <ErrorView error={q.error} onRetry={() => void q.refetch()} />
      ) : (
        <>
          <div className="grid two">
            <section className="card stack" aria-labelledby="map-h">
              <h2 id="map-h">{t("inspection.map")}</h2>
              {info ? (
                <SiteMap
                  lat={info.lat}
                  lon={info.lon}
                  path={path}
                  label={t("inspection.intakeEstimated")}
                />
              ) : null}
            </section>
            <section className="card stack" aria-labelledby="flight-h">
              <h2 id="flight-h">{t("inspection.flight")}</h2>
              {q.data.mission.feasible ? null : (
                <p className="state" role="alert">
                  <strong>{t("inspection.refused")}</strong>:{" "}
                  <span lang="en" dir="ltr">
                    {q.data.mission.refused_reason}
                  </span>
                </p>
              )}
              <dl className="facts">
                <div>
                  <dt>{t("inspection.distance")}</dt>
                  <dd className="num">{n(q.data.mission.distance_m / 1000, 1)} km</dd>
                </div>
                <div>
                  <dt>{t("inspection.flight")}</dt>
                  <dd className="num">
                    {t("inspection.minutes", {
                      count: Number((q.data.mission.flight_time_s / 60).toFixed(1)),
                    })}{" "}
                    /{" "}
                    {t("inspection.minutes", {
                      count: Number((q.data.mission.usable_time_s / 60).toFixed(1)),
                    })}
                  </dd>
                </div>
              </dl>
              <svg
                viewBox="0 0 100 10"
                preserveAspectRatio="none"
                role="img"
                aria-label={`${t("inspection.flight")}: ${n(q.data.mission.flight_time_s / 60, 1)} / ${n(q.data.mission.usable_time_s / 60, 1)} min`}
                style={{ width: "100%", height: 22 }}
              >
                <rect x="0" y="2" width="100" height="6" fill="var(--clear)" />
                <rect
                  x="0"
                  y="1"
                  width={Math.min(
                    100,
                    (100 * q.data.mission.flight_time_s) / q.data.mission.usable_time_s,
                  )}
                  height="8"
                  fill={q.data.mission.feasible ? "var(--band-fill)" : "var(--nosafe)"}
                  stroke="var(--band)"
                  strokeWidth="0.6"
                />
              </svg>
              <h3>{t("inspection.value")}</h3>
              <p>{t("inspection.voiExplain")}</p>
              <p className="num">
                <strong>{n(q.data.inspection.value_cu)} CU</strong> vs{" "}
                {n(q.data.inspection.sortie_cost_cu)} CU ·{" "}
                {q.data.inspection.inspect ? t("advisory.inspect") : t("advisory.noInspect")}
              </p>
              <ul>
                {q.data.inspection.reasons.map((r) => (
                  <li key={r} lang="en" dir="ltr">
                    {r}
                  </li>
                ))}
              </ul>
              <h3>{t("inspection.download")}</h3>
              <div className="row">
                <button
                  type="button"
                  className="btn"
                  onClick={() =>
                    download(
                      `madkhal-${site}.geojson`,
                      JSON.stringify(q.data.exports.geojson, null, 2),
                      "application/geo+json",
                    )
                  }
                >
                  {t("inspection.geojson")}
                </button>
                <button
                  type="button"
                  className="btn"
                  onClick={() =>
                    download(
                      `madkhal-${site}.kml`,
                      q.data.exports.kml,
                      "application/vnd.google-earth.kml+xml",
                    )
                  }
                >
                  {t("inspection.kml")}
                </button>
                <button
                  type="button"
                  className="btn"
                  onClick={() =>
                    download(
                      `madkhal-${site}.plan`,
                      JSON.stringify(q.data.exports.plan, null, 2),
                      "application/json",
                    )
                  }
                >
                  {t("inspection.plan")}
                </button>
              </div>
              {q.data.plan_valid ? <p className="muted">{t("inspection.planValid")}</p> : null}
            </section>
          </div>
          <section className="card stack" aria-labelledby="wind-h">
            <h2 id="wind-h">{t("inspection.wind")}</h2>
            <p className="muted">
              {t("inspection.windNote")} {formatPercent(q.data.availability, s)}
            </p>
            <div className="table-wrap" tabIndex={0}>
              <table>
                <tbody>
                  <tr>
                    {q.data.wind.map((h) => (
                      <td
                        key={h.hour_local}
                        className={`wind ${h.available ? "ok" : "no"}`}
                        title={`${h.hour_local}:00`}
                      >
                        <span className="num">{n(h.hour_local)}</span>
                        <br />
                        <span className="num">{n(h.wind_ms, 1)}</span>
                        <br />
                        <span>
                          {h.available ? t("inspection.available") : t("inspection.unavailable")}
                        </span>
                      </td>
                    ))}
                  </tr>
                </tbody>
              </table>
            </div>
          </section>
        </>
      )}
    </div>
  );
}
