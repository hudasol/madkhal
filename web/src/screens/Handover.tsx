import { useTranslation } from "react-i18next";
import { useAdvisory, useSeries, useSites } from "../api/hooks";
import type { Site } from "../api/types";
import { AdvisoryPanel } from "../components/Advisory";
import { IntervalBar } from "../components/IntervalBar";
import { ErrorView, Loading } from "../components/StateView";
import { formatDay } from "../format";
import { useSettings } from "../settings";

function SiteSummary({ site }: { site: Site }) {
  const { t } = useTranslation();
  const s = useSettings();
  const adv = useAdvisory(site.id);
  const ser = useSeries(site.id);
  if (adv.isLoading || ser.isLoading) return <Loading what={site.name} />;
  if (adv.isError || !adv.data || ser.isError || !ser.data)
    return <ErrorView error={adv.error ?? ser.error} />;
  const i = ser.data.dates.length - 1;
  const band = (b: { lo: number[]; median: number[]; hi: number[] }) => ({
    lo: b.lo[i]!,
    median: b.median[i]!,
    hi: b.hi[i]!,
  });
  return (
    <article className="card stack handover-site" aria-labelledby={`ho-${site.id}`}>
      <h2 id={`ho-${site.id}`}>{s.lang === "ar" ? site.name_ar : site.name}</h2>
      <p className="muted">{t("handover.asOf", { date: formatDay(ser.data.dates[i]!, s) })}</p>
      <AdvisoryPanel adv={adv.data} compact />
      <IntervalBar label={t("console.within", { count: 3 })} {...band(ser.data.within_3)} />
      <p>
        <strong>{t("handover.open")}:</strong>{" "}
        {adv.data.inspect ? t("advisory.inspect") : t("handover.noneOpen")}
      </p>
    </article>
  );
}

export function HandoverScreen() {
  const { t } = useTranslation();
  const sites = useSites();
  return (
    <div className="stack handover">
      <div className="row" style={{ justifyContent: "space-between" }}>
        <h1>{t("handover.title")}</h1>
        <button type="button" className="btn no-print" onClick={() => window.print()}>
          {t("handover.print")}
        </button>
      </div>
      <p>{t("handover.intro")}</p>
      <p className="muted">{t("advisory.replay")}</p>
      {sites.isLoading ? (
        <Loading />
      ) : sites.isError || !sites.data ? (
        <ErrorView error={sites.error} />
      ) : null}
      <div className="grid tiles">
        {(sites.data ?? []).map((s) => (
          <SiteSummary key={s.id} site={s} />
        ))}
      </div>
      <p className="muted">{t("app.scope")}</p>
    </div>
  );
}
