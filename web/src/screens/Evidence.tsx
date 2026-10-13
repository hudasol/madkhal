import { useId, useMemo, useState } from "react";
import { useTranslation } from "react-i18next";
import { useEvidence, useSites, useTrackRecord } from "../api/hooks";
import type { DayState, EvidenceResponse, TrackRecordResponse } from "../api/types";
import { Abbr } from "../components/Abbr";
import { ErrorView, Loading } from "../components/StateView";
import { formatDay, formatNumber, formatPercent } from "../format";
import { useSettings } from "../settings";

const CELL = 3;
const ROW_H = 16;
const LABEL_W = 44;

function Swatch({ state, id }: { state: DayState; id: string }) {
  const fill =
    state === "alert"
      ? "var(--alert-cell)"
      : state === "clear"
        ? "var(--clear)"
        : `url(#${id}-hatch)`;
  return (
    <svg width="18" height="14" aria-hidden="true">
      <defs>
        <pattern
          id={`${id}-hatch`}
          width="4"
          height="4"
          patternUnits="userSpaceOnUse"
          patternTransform="rotate(45)"
        >
          <line x1="0" y1="0" x2="0" y2="4" stroke="var(--nodata)" strokeWidth="1.5" />
        </pattern>
      </defs>
      <rect x="1" y="1" width="16" height="12" fill={fill} stroke="var(--border)" strokeWidth="1" />
      {state === "alert" ? <path d="M9 3 L14 11 L4 11 Z" fill="var(--bg)" /> : null}
    </svg>
  );
}

function CoverageCalendar({ ev }: { ev: EvidenceResponse }) {
  const { t } = useTranslation();
  const s = useSettings();
  const id = useId();
  const rtl = s.lang === "ar";
  const years = Object.keys(ev.years).sort();
  const width = LABEL_W + 366 * CELL + 8;
  const height = years.length * ROW_H + 8;
  const cells = useMemo(() => {
    return ev.dates.map((d, i) => {
      const year = d.slice(0, 4);
      const row = years.indexOf(year);
      const start = Date.UTC(Number(year), 0, 1);
      const doy = Math.round((Date.parse(`${d}T00:00:00Z`) - start) / 86400000);
      return { d, row, doy, state: ev.state[i]! };
    });
  }, [ev, years]);
  const x = (doy: number) => (rtl ? width - LABEL_W - (doy + 1) * CELL : LABEL_W + doy * CELL);
  const desc = t("evidence.calendarDesc");
  return (
    <figure className="chart stack" aria-labelledby={`${id}-cap`}>
      <figcaption id={`${id}-cap`}>
        <strong>{t("evidence.calendar")}</strong>. {desc}
      </figcaption>
      <div className="legend" aria-hidden="true">
        <span>
          <Swatch state="clear" id={`${id}-l1`} /> {t("evidence.clear")}
        </span>
        <span>
          <Swatch state="nodata" id={`${id}-l2`} /> {t("evidence.nodata")}
        </span>
        <span>
          <Swatch state="alert" id={`${id}-l3`} /> {t("evidence.alert")}
        </span>
      </div>
      <div className="table-wrap">
        <svg
          viewBox={`0 0 ${width} ${height}`}
          role="img"
          aria-label={`${t("evidence.calendar")}. ${desc}`}
          style={{ minWidth: 640 }}
        >
          <defs>
            <pattern
              id={`${id}-hatch`}
              width="3"
              height="3"
              patternUnits="userSpaceOnUse"
              patternTransform="rotate(45)"
            >
              <line x1="0" y1="0" x2="0" y2="3" stroke="var(--nodata)" strokeWidth="1.2" />
            </pattern>
          </defs>
          {years.map((y, r) => (
            <text
              key={y}
              x={rtl ? width - 4 : 4}
              y={r * ROW_H + 13}
              fontSize="11"
              textAnchor={rtl ? "end" : "start"}
              fill="var(--text-muted)"
            >
              {formatNumber(Number(y), s).replace(/[,٬]/g, "")}
            </text>
          ))}
          {cells.map((c) => (
            <rect
              key={c.d}
              x={x(c.doy)}
              y={c.row * ROW_H + 2}
              width={CELL}
              height={ROW_H - 4}
              fill={
                c.state === "alert"
                  ? "var(--alert-cell)"
                  : c.state === "clear"
                    ? "var(--clear)"
                    : `url(#${id}-hatch)`
              }
            />
          ))}
        </svg>
      </div>
      <div className="table-wrap">
        <table>
          <caption className="muted">{t("evidence.calendar")}</caption>
          <thead>
            <tr>
              <th scope="col">{t("evidence.year")}</th>
              <th scope="col">{t("evidence.totalDays")}</th>
              <th scope="col">{t("evidence.clearDays")}</th>
              <th scope="col">{t("evidence.alertDays")}</th>
              <th scope="col">{t("evidence.nodataDays")}</th>
            </tr>
          </thead>
          <tbody>
            {years.map((y) => {
              const r = ev.years[y]!;
              return (
                <tr key={y}>
                  <th scope="row">{formatNumber(Number(y), s).replace(/[,٬]/g, "")}</th>
                  <td className="num">{formatNumber(r.days, s)}</td>
                  <td className="num">
                    {formatNumber(r.clear, s)} ({formatPercent(r.clear / r.days, s)})
                  </td>
                  <td className="num">{formatNumber(r.alert, s)}</td>
                  <td className="num">{formatNumber(r.nodata, s)}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </figure>
  );
}

function TrackRecord({ tr }: { tr: TrackRecordResponse }) {
  const { t } = useTranslation();
  const s = useSettings();
  const n = (x: number) => formatNumber(x, s);
  const rate = tr.hit_rate.rate ?? 0;
  return (
    <section className="card stack" aria-labelledby="tr-h">
      <h2 id="tr-h">{t("evidence.trackRecord")}</h2>
      <p>{t("evidence.trackIntro")}</p>
      <p>
        <strong>{t("evidence.caught", { k: n(tr.hit_rate.k), n: n(tr.hit_rate.n) })}</strong>{" "}
        <span className="num">
          ({formatPercent(rate, s)}, {t("common.of", { k: n(tr.hit_rate.k), n: n(tr.hit_rate.n) })})
        </span>
      </p>
      <p>{t("evidence.whyMatters")}</p>
      <div className="table-wrap">
        <table>
          <thead>
            <tr>
              <th scope="col">{t("evidence.event")}</th>
              <th scope="col">{t("evidence.outcome")}</th>
              <th scope="col">{t("evidence.clearInLookback")}</th>
              <th scope="col">{t("evidence.lead")}</th>
              <th scope="col">{t("evidence.status")}</th>
            </tr>
          </thead>
          <tbody>
            {tr.rows.map((r) => (
              <tr key={r.event_id}>
                <td>{r.label}</td>
                <td>{t(`evidence.${r.outcome}`)}</td>
                <td className="num">
                  {t("common.of", { k: n(r.clear_days_in_lookback), n: n(r.days_in_lookback) })}
                </td>
                <td className="num">
                  {r.lead_alert_days !== null && r.lead_alert_days !== undefined
                    ? t("common.days", { count: r.lead_alert_days })
                    : "-"}
                </td>
                <td>
                  <span className={r.status_class === "UNVERIFIED" ? "badge warn" : "badge"}>
                    {r.evidence_status}
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <h3>{t("evidence.falseAlarms")}</h3>
      <p className="muted">{t("evidence.falseIntro")}</p>
      <div className="table-wrap">
        <table>
          <thead>
            <tr>
              <th scope="col">{t("common.site")}</th>
              <th scope="col">{t("evidence.alertDaysOf")}</th>
              <th scope="col">{t("evidence.episodesPerYear")}</th>
            </tr>
          </thead>
          <tbody>
            {tr.false_alarms.map((f) => (
              <tr key={`${f.dataset}-${f.site}`}>
                <td>
                  {t(`place.${f.site}`)} (<Abbr k={f.dataset === "olci_v1" ? "OLCI" : "MODIS"} />)
                </td>
                <td className="num">
                  {t("common.of", { k: n(f.alert_days.k), n: n(f.alert_days.n) })} (
                  {formatPercent(f.alert_days.rate ?? 0, s)})
                </td>
                <td className="num">
                  {formatNumber(f.episodes_per_year, s, 2)} (
                  {t("common.of", { k: n(f.episodes), n: n(f.quiet_days) })})
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}

export function EvidenceScreen() {
  const { t } = useTranslation();
  const s = useSettings();
  const sites = useSites();
  const [site, setSite] = useState("kalba");
  const ev = useEvidence(site);
  const tr = useTrackRecord();
  return (
    <div className="stack">
      <h1>{t("evidence.title")}</h1>
      <p>
        {t("evidence.intro")} (<Abbr k="OLCI" />)
      </p>
      <label className="row" style={{ gap: "0.4rem" }}>
        <span>{t("common.site")}</span>
        <select value={site} onChange={(e) => setSite(e.target.value)}>
          {(sites.data ?? []).map((x) => (
            <option key={x.id} value={x.id}>
              {s.lang === "ar" ? x.name_ar : x.name}
            </option>
          ))}
        </select>
      </label>
      <section className="card" aria-busy={ev.isLoading}>
        {ev.isLoading ? (
          <Loading />
        ) : ev.isError || !ev.data ? (
          <ErrorView error={ev.error} onRetry={() => void ev.refetch()} />
        ) : (
          <CoverageCalendar ev={ev.data} />
        )}
      </section>
      {ev.data && ev.data.events.length > 0 ? (
        <section className="card stack" aria-labelledby="ev-h">
          <h2 id="ev-h">{t("evidence.events")}</h2>
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th scope="col">{t("evidence.event")}</th>
                  <th scope="col">{t("evidence.reference")}</th>
                  <th scope="col">{t("evidence.earliest")}</th>
                  <th scope="col">{t("evidence.status")}</th>
                </tr>
              </thead>
              <tbody>
                {ev.data.events.map((e) => (
                  <tr key={e.id}>
                    <td>{e.label}</td>
                    <td className="num">{e.t_ref ? formatDay(e.t_ref, s) : "-"}</td>
                    <td className="num">
                      {e.t_ref_earliest ? formatDay(e.t_ref_earliest, s) : "-"}
                    </td>
                    <td>
                      <span className={e.status_class === "UNVERIFIED" ? "badge warn" : "badge"}>
                        {e.status_badge}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      ) : null}
      {tr.isLoading ? (
        <Loading />
      ) : tr.isError || !tr.data ? (
        <ErrorView error={tr.error} />
      ) : (
        <TrackRecord tr={tr.data} />
      )}
      {tr.data ? (
        <div className="grid two">
          <section className="card tinted stack" aria-labelledby="lead-h">
            <h2 id="lead-h">{t("evidence.leadTitle")}</h2>
            <p>
              {t("evidence.leadText", {
                lead: formatNumber(tr.data.lead_time.lead_alert_days, s),
                min: formatNumber(tr.data.lead_time.lead_alert_min_days, s),
              })}
            </p>
            <p className="muted">
              {t("common.source")}: Nadhir, {tr.data.lead_time.source}
            </p>
          </section>
          <section className="card tinted stack" aria-labelledby="blind-h">
            <h2 id="blind-h">{t("evidence.blindTitle")}</h2>
            <p>{t("evidence.blindText")}</p>
          </section>
        </div>
      ) : null}
    </div>
  );
}
