import { useMemo, useState } from "react";
import { useTranslation } from "react-i18next";
import { MODE } from "../api/client";
import { useAdvisory, useSeries, useSites } from "../api/hooks";
import { AdvisoryPanel } from "../components/Advisory";
import { ActionLegend } from "../components/Ribbon";
import type { BeliefSeries, Site } from "../api/types";
import { BandChart } from "../components/BandChart";
import { IntervalBar } from "../components/IntervalBar";
import { Empty, ErrorView, Loading } from "../components/StateView";
import { formatDay } from "../format";
import { useSettings } from "../settings";

const WINDOW = 60;

function SiteTile({
  site,
  series,
  index,
  latest,
}: {
  site: Site;
  series: BeliefSeries;
  index: number;
  latest: boolean;
}) {
  const { t } = useTranslation();
  const s = useSettings();
  const day = series.dates[index]!;
  const adv = useAdvisory(site.id, day);
  const staticOld = MODE === "static" && !latest;
  const name = s.lang === "ar" ? site.name_ar : site.name;
  const stale = series.staleness_days[index];
  const staleText =
    stale === null || stale === undefined
      ? t("console.stalenessNever")
      : stale === 0
        ? t("console.stalenessToday")
        : t("console.stalenessDays", { count: stale });
  const clear = series.clear[index];
  const alert = series.alert[index];
  const band = (b: BeliefSeries["within_1"]) => ({
    lo: b.lo[index]!,
    median: b.median[index]!,
    hi: b.hi[index]!,
  });
  return (
    <article
      className="card stack"
      aria-labelledby={`tile-${site.id}`}
      data-testid={`tile-${site.id}`}
    >
      <div className="row" style={{ justifyContent: "space-between" }}>
        <h2 id={`tile-${site.id}`}>{name}</h2>
        <span className="badge warn">{t("common.estimated")}</span>
      </div>
      <p className="muted">{t("advisory.replay")}</p>
      {staticOld ? (
        <p className="state" role="status">
          {t("advisory.staticOnlyLatest")}
        </p>
      ) : adv.isLoading ? (
        <Loading />
      ) : adv.isError || !adv.data ? (
        <ErrorView error={adv.error} onRetry={() => void adv.refetch()} />
      ) : (
        <AdvisoryPanel adv={adv.data} compact />
      )}
      <p>
        {alert ? (
          <strong>{t("console.alertToday")}</strong>
        ) : clear ? (
          t("console.noAlert")
        ) : (
          t("console.nodataToday")
        )}
        {" · "}
        {t("console.staleness")}: <span className="num">{staleText}</span>
      </p>
      <IntervalBar label={t("console.anyBloom")} {...band(series.p_any_bloom)} />
      <IntervalBar label={t("console.within", { count: 1 })} {...band(series.within_1)} />
      <IntervalBar label={t("console.within", { count: 3 })} {...band(series.within_3)} />
      <IntervalBar label={t("console.within", { count: 7 })} {...band(series.within_7)} />
    </article>
  );
}

function useAllSeries(ids: string[]) {
  const a = useSeries(ids[0] ?? "kalba");
  const b = useSeries(ids[1] ?? "barka");
  const c = useSeries(ids[2] ?? "alraha");
  return [a, b, c];
}

export function ConsoleScreen() {
  const { t } = useTranslation();
  const s = useSettings();
  const sites = useSites();
  const ids = (sites.data ?? []).map((x) => x.id);
  const all = useAllSeries(ids);
  const first = all[0]?.data;
  const lastDate = first ? first.dates[first.dates.length - 1]! : "";
  const [asOf, setAsOf] = useState<string | null>(null);
  const day = asOf ?? lastDate;
  const [focus, setFocus] = useState<string>("kalba");

  const focusQuery = all[ids.indexOf(focus)];
  const focusSeries = focusQuery?.data;
  const windowed = useMemo(() => {
    if (!focusSeries) return null;
    const end = focusSeries.dates.indexOf(day);
    if (end < 0) return null;
    const start = Math.max(0, end - WINDOW + 1);
    const cut = (b: BeliefSeries["within_3"]) => ({
      lo: b.lo.slice(start, end + 1),
      median: b.median.slice(start, end + 1),
      hi: b.hi.slice(start, end + 1),
    });
    return {
      dates: focusSeries.dates.slice(start, end + 1),
      band: cut(focusSeries.within_3),
      clear: focusSeries.clear.slice(start, end + 1),
      alert: focusSeries.alert.slice(start, end + 1),
    };
  }, [focusSeries, day]);

  if (sites.isLoading) return <Loading what={t("console.title")} />;
  if (sites.isError) return <ErrorView error={sites.error} onRetry={() => void sites.refetch()} />;
  if (!sites.data || sites.data.length === 0) return <Empty />;

  return (
    <div className="stack">
      <h1>{t("console.title")}</h1>
      <p>{t("console.intro")}</p>
      <ActionLegend />
      <div className="row">
        <label className="row" style={{ gap: "0.4rem" }}>
          <span>{t("common.asOf")}</span>
          <input
            type="date"
            value={day}
            min={first?.dates[0]}
            max={lastDate}
            onChange={(e) => setAsOf(e.target.value || null)}
          />
        </label>
        {first ? (
          <span className="muted">{t("common.asOfHelp", { last: formatDay(lastDate, s) })}</span>
        ) : null}
      </div>
      <div className="grid tiles">
        {sites.data.map((site, k) => {
          const q = all[k];
          if (!q || q.isLoading) return <Loading key={site.id} what={site.name} />;
          if (q.isError || !q.data)
            return <ErrorView key={site.id} error={q.error} onRetry={() => void q.refetch()} />;
          const idx = q.data.dates.indexOf(day);
          if (idx < 0) return <Empty key={site.id} />;
          return (
            <SiteTile
              key={site.id}
              site={site}
              series={q.data}
              index={idx}
              latest={day === lastDate}
            />
          );
        })}
      </div>
      <section className="card stack" aria-labelledby="chart-h">
        <div className="row" style={{ justifyContent: "space-between" }}>
          <h2 id="chart-h">{t("console.chartTitle")}</h2>
          <label className="row" style={{ gap: "0.4rem" }}>
            <span>{t("common.site")}</span>
            <select value={focus} onChange={(e) => setFocus(e.target.value)}>
              {sites.data.map((x) => (
                <option key={x.id} value={x.id}>
                  {s.lang === "ar" ? x.name_ar : x.name}
                </option>
              ))}
            </select>
          </label>
        </div>
        {windowed ? (
          <BandChart
            title={t("console.chartTitle")}
            description={t("console.chartDesc")}
            dates={windowed.dates}
            band={windowed.band}
            clear={windowed.clear}
            alert={windowed.alert}
          />
        ) : !focusQuery || focusQuery.isLoading ? (
          <Loading />
        ) : focusQuery.isError || !focusSeries ? (
          <ErrorView error={focusQuery.error} onRetry={() => void focusQuery.refetch()} />
        ) : (
          <Empty />
        )}
      </section>
    </div>
  );
}
