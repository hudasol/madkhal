import { useState } from "react";
import { useTranslation } from "react-i18next";
import { useReplay } from "../api/hooks";
import { ActionBadge, type ActionCode } from "../components/ActionBadge";
import { SiteSelect } from "../components/SiteSelect";
import { ErrorView, Loading } from "../components/StateView";
import { formatDay, formatNumber, formatPercent } from "../format";
import { useSettings } from "../settings";

export function ReplayScreen() {
  const { t } = useTranslation();
  const s = useSettings();
  const [site, setSite] = useState("kalba");
  const q = useReplay(site);
  const n = (x: number) => formatNumber(x, s);
  return (
    <div className="stack">
      <h1>{t("replay.title")}</h1>
      <p className="badge warn">{t("advisory.replay")}</p>
      <p>{t("replay.intro")}</p>
      <SiteSelect value={site} onChange={setSite} />
      {q.isLoading ? (
        <Loading />
      ) : q.isError || !q.data ? (
        <ErrorView error={q.error} onRetry={() => void q.refetch()} />
      ) : (
        <>
          <section className="card stack" aria-labelledby="burden-h">
            <h2 id="burden-h">{t("replay.burden")}</h2>
            <p>
              {t("replay.burdenDesc")}{" "}
              <strong className="num">
                {t("replay.perYear", {
                  value: formatNumber(q.data.quiet_non_go_per_year ?? 0, s, 1),
                })}
              </strong>{" "}
              <span className="muted num">
                ({t("common.of", { k: n(q.data.quiet_non_go_days), n: n(q.data.quiet_days) })})
              </span>
            </p>
            <div className="table-wrap" tabIndex={0}>
              <table>
                <thead>
                  <tr>
                    <th scope="col">{t("replay.year")}</th>
                    <th scope="col">{t("replay.days")}</th>
                    <th scope="col">{t("replay.nonGo")}</th>
                    <th scope="col">{t("replay.quietDays")}</th>
                    <th scope="col">{t("replay.quietNonGo")}</th>
                  </tr>
                </thead>
                <tbody>
                  {Object.entries(q.data.by_year).map(([y, r]) => (
                    <tr key={y}>
                      <th scope="row">{y}</th>
                      <td className="num">{n(r.days)}</td>
                      <td className="num">{n(r.non_go)}</td>
                      <td className="num">{n(r.quiet_days)}</td>
                      <td className="num">{n(r.quiet_non_go)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>
          <section className="card stack" aria-labelledby="events-h">
            <h2 id="events-h">{t("replay.beforeEvents")}</h2>
            <div className="table-wrap" tabIndex={0}>
              <table>
                <thead>
                  <tr>
                    <th scope="col">{t("replay.event")}</th>
                    <th scope="col">{t("replay.status")}</th>
                    <th scope="col">{t("replay.anchor")}</th>
                    <th scope="col">{t("replay.daysBefore")}</th>
                    <th scope="col">{t("common.date")}</th>
                    <th scope="col">{t("replay.advice")}</th>
                    <th scope="col">{t("replay.belief")}</th>
                  </tr>
                </thead>
                <tbody>
                  {q.data.points.map((p) => (
                    <tr key={`${p.event_id}-${p.anchor}-${p.days_before}`}>
                      <td>{p.label}</td>
                      <td>
                        <span
                          className={p.status_badge.includes("UNVERIFIED") ? "badge warn" : "badge"}
                        >
                          {p.status_badge}
                        </span>
                      </td>
                      <td>{t(`replay.${p.anchor}`)}</td>
                      <td className="num">{n(p.days_before)}</td>
                      <td className="num" title={t("common.utcDay")}>
                        {formatDay(p.date, s)}
                      </td>
                      <td>
                        {p.action ? (
                          <ActionBadge action={p.action as ActionCode} scale={p.scale} />
                        ) : (
                          <span className="muted">{p.note}</span>
                        )}
                      </td>
                      <td className="num">
                        {p.p_any_bloom
                          ? `${formatPercent(p.p_any_bloom[1]!, s)} (${formatPercent(p.p_any_bloom[0]!, s)} ${t("common.to")} ${formatPercent(p.p_any_bloom[2]!, s)})`
                          : ""}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>
        </>
      )}
    </div>
  );
}
