import { useState } from "react";
import { useTranslation } from "react-i18next";
import { useClaims, useMethod } from "../api/hooks";
import { Markdown } from "../components/Markdown";
import { ErrorView, Loading } from "../components/StateView";
import { PredictionTable } from "./Policies";

const TABS = ["method", "claims", "predictions", "limitations", "pilot"] as const;
type Tab = (typeof TABS)[number];

export function MethodScreen() {
  const { t } = useTranslation();
  const m = useMethod();
  const c = useClaims();
  const [tab, setTab] = useState<Tab>("method");
  return (
    <div className="stack">
      <h1>{t("method.title")}</h1>
      <p>
        <strong>{t("app.scope")}</strong>
      </p>
      <p className="muted">{t("method.arabic")}</p>
      <div role="tablist" aria-label={t("method.tabs")} className="row">
        {TABS.map((k) => (
          <button
            key={k}
            type="button"
            role="tab"
            id={`tab-${k}`}
            aria-selected={tab === k}
            aria-controls={`panel-${k}`}
            tabIndex={tab === k ? 0 : -1}
            className="btn"
            onClick={() => setTab(k)}
            onKeyDown={(e) => {
              const i = TABS.indexOf(k);
              if (e.key === "ArrowRight" || e.key === "ArrowLeft") {
                const dir =
                  (e.key === "ArrowRight") !== (document.documentElement.dir === "rtl") ? 1 : -1;
                const next = TABS[(i + dir + TABS.length) % TABS.length]!;
                setTab(next);
                document.getElementById(`tab-${next}`)?.focus();
              }
            }}
          >
            {t(`method.${k}`)}
          </button>
        ))}
      </div>
      <section
        id={`panel-${tab}`}
        role="tabpanel"
        aria-labelledby={`tab-${tab}`}
        className="card stack"
        tabIndex={0}
      >
        {m.isLoading || c.isLoading ? (
          <Loading />
        ) : m.isError || !m.data ? (
          <ErrorView error={m.error} onRetry={() => void m.refetch()} />
        ) : tab === "method" ? (
          <div lang="en" dir="ltr">
            <Markdown text={m.data.method_markdown} />
          </div>
        ) : tab === "limitations" ? (
          <div lang="en" dir="ltr">
            <Markdown text={m.data.limitations_markdown || "Not written yet."} />
          </div>
        ) : tab === "pilot" ? (
          <div lang="en" dir="ltr">
            <Markdown text={m.data.pilot_markdown} />
          </div>
        ) : tab === "predictions" ? (
          <PredictionTable preds={m.data.predictions} />
        ) : c.isError || !c.data ? (
          <ErrorView error={c.error} onRetry={() => void c.refetch()} />
        ) : (
          <div className="table-wrap" tabIndex={0}>
            <table>
              <thead>
                <tr>
                  <th scope="col">{t("method.claimId")}</th>
                  <th scope="col">{t("method.claim")}</th>
                  <th scope="col">{t("method.type")}</th>
                  <th scope="col">{t("method.pointer")}</th>
                </tr>
              </thead>
              <tbody>
                {c.data.claims.map((x) => (
                  <tr key={x.id}>
                    <th scope="row">{x.id}</th>
                    <td lang="en" dir="ltr">
                      {x.text}
                    </td>
                    <td>
                      <span
                        className={
                          x.type === "UNVERIFIED" || x.type === "ASSUMPTION"
                            ? "badge warn"
                            : "badge"
                        }
                      >
                        {x.type}
                      </span>
                    </td>
                    <td>
                      <code>
                        {x.pointer.kind}: {x.pointer.ref}
                      </code>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </div>
  );
}
