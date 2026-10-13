import { useState } from "react";
import { useTranslation } from "react-i18next";
import { MODE } from "../api/client";
import { useTimeline } from "../api/hooks";
import { BandChart } from "../components/BandChart";
import { ActionLegend, Ribbon } from "../components/Ribbon";
import { SiteSelect } from "../components/SiteSelect";
import { Empty, ErrorView, Loading } from "../components/StateView";

export function TimelineScreen() {
  const { t } = useTranslation();
  const [site, setSite] = useState("kalba");
  const [start, setStart] = useState("2018-08-01");
  const [end, setEnd] = useState("2018-11-30");
  const q = useTimeline(site, start, end);
  return (
    <div className="stack">
      <h1>{t("timeline.title")}</h1>
      <p>{t("timeline.intro")}</p>
      <p className="muted">{t("advisory.replay")}</p>
      <div className="row">
        <SiteSelect value={site} onChange={setSite} />
        {MODE === "static" ? (
          <span className="muted">{t("timeline.staticWindow")}</span>
        ) : (
          <fieldset className="row" style={{ border: 0, padding: 0, margin: 0 }}>
            <legend className="muted">{t("timeline.window")}</legend>
            <input
              type="date"
              aria-label={`${t("timeline.window")} start`}
              value={start}
              min="2018-01-01"
              max="2023-11-07"
              onChange={(e) => setStart(e.target.value)}
            />
            <input
              type="date"
              aria-label={`${t("timeline.window")} end`}
              value={end}
              min="2018-01-01"
              max="2023-11-07"
              onChange={(e) => setEnd(e.target.value)}
            />
          </fieldset>
        )}
      </div>
      <ActionLegend />
      {q.isLoading ? (
        <Loading />
      ) : q.isError || !q.data ? (
        <ErrorView error={q.error} onRetry={() => void q.refetch()} />
      ) : q.data.dates.length === 0 ? (
        <Empty />
      ) : (
        <section className="card stack" aria-label={t("timeline.ribbon")}>
          <Ribbon
            title={t("timeline.ribbon")}
            description={t("timeline.ribbonDesc")}
            dates={q.data.dates}
            actions={q.data.action}
            scales={q.data.scale}
            inspect={q.data.inspect}
          />
          <BandChart
            title={t("timeline.band")}
            description={t("console.chartDesc")}
            dates={q.data.dates}
            band={q.data.within_3}
            clear={q.data.clear}
            alert={q.data.alert}
          />
        </section>
      )}
    </div>
  );
}
