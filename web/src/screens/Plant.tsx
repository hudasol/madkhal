import { useTranslation } from "react-i18next";
import { usePlantProfile, useSensitivity } from "../api/hooks";
import { ErrorView, Loading } from "../components/StateView";
import { formatNumber, formatPercent } from "../format";
import { useSettings } from "../settings";

export function PlantScreen() {
  const { t } = useTranslation();
  const s = useSettings();
  const prof = usePlantProfile();
  const sens = useSensitivity();
  return (
    <div className="stack">
      <h1>{t("plant.title")}</h1>
      <p>{t("plant.intro")}</p>
      {prof.isLoading ? (
        <Loading />
      ) : prof.isError || !prof.data ? (
        <ErrorView error={prof.error} onRetry={() => void prof.refetch()} />
      ) : (
        <section className="card stack" aria-labelledby="params-h">
          <h2 id="params-h">{t("plant.parameters")}</h2>
          <p>
            <strong>
              {t("plant.share", {
                share: formatPercent(prof.data.assumption_share, s),
                level: prof.data.evidence_level,
              })}
            </strong>
          </p>
          <div className="table-wrap" tabIndex={0}>
            <table>
              <thead>
                <tr>
                  <th scope="col">{t("plant.key")}</th>
                  <th scope="col">{t("plant.meaning")}</th>
                  <th scope="col">{t("plant.value")}</th>
                  <th scope="col">{t("plant.unit")}</th>
                  <th scope="col">{t("plant.level")}</th>
                  <th scope="col">{t("plant.source")}</th>
                  <th scope="col">{t("plant.spread")}</th>
                  <th scope="col">{t("plant.role")}</th>
                  <th scope="col">{t("plant.provenance")}</th>
                </tr>
              </thead>
              <tbody>
                {prof.data.parameters.map((p) => (
                  <tr key={p.key}>
                    <td>
                      <code>{p.key}</code>
                    </td>
                    <td lang="en" dir="ltr">
                      {p.label}
                    </td>
                    <td className="num">{formatNumber(p.value, s, 3)}</td>
                    <td className="num">{p.unit}</td>
                    <td className="num">{p.evidence_level}</td>
                    <td>{p.source}</td>
                    <td className="num">{formatPercent(p.rel_spread, s)}</td>
                    <td>{p.role}</td>
                    <td lang="en" dir="ltr">
                      {p.provenance}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      )}
      {sens.isLoading ? (
        <Loading />
      ) : sens.isError || !sens.data ? (
        <ErrorView error={sens.error} onRetry={() => void sens.refetch()} />
      ) : (
        <section className="card stack" aria-labelledby="sens-h">
          <h2 id="sens-h">{t("plant.sensitivity")}</h2>
          <p>
            <strong>{t("plant.measureFirst")}:</strong>{" "}
            {sens.data.measure_first.map((k) => (
              <code key={k} style={{ marginInlineEnd: "0.5rem" }}>
                {k}
              </code>
            ))}
          </p>
          <p className="muted">{t("plant.sensitivityDesc")}</p>
          <div className="table-wrap" tabIndex={0}>
            <table>
              <thead>
                <tr>
                  <th scope="col">#</th>
                  <th scope="col">{t("plant.key")}</th>
                  <th scope="col">{t("plant.role")}</th>
                  <th scope="col">{t("plant.swingFouling")}</th>
                  <th scope="col">{t("plant.swingWater")}</th>
                </tr>
              </thead>
              <tbody>
                {sens.data.rows.map((r) => (
                  <tr key={r.key}>
                    <td className="num">{formatNumber(r.rank, s)}</td>
                    <td>
                      <code>{r.key}</code>
                    </td>
                    <td>{r.role}</td>
                    <td className="num">{formatNumber(r.swing_fouling, s, 3)}</td>
                    <td className="num">{formatNumber(r.swing_water, s, 3)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      )}
    </div>
  );
}
