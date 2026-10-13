import { useState } from "react";
import { useTranslation } from "react-i18next";
import { usePolicies } from "../api/hooks";
import type { Comparison, Prediction } from "../api/types";
import { DotWhisker } from "../components/DotWhisker";
import { ErrorView, Loading } from "../components/StateView";
import { formatPercent, formatValue } from "../format";
import { useSettings } from "../settings";

const POLICIES = ["P0", "P1", "P2", "P3", "P4", "P5"] as const;
const METRICS = [
  "unserved_m3",
  "forced_shutdowns",
  "cleanings",
  "membrane_index",
  "park_days_per_year",
  "derate_days_per_year",
  "escalation_days_per_year",
  "changes_per_30_days",
  "sorties_per_year",
  "weighted_cost_cu",
];

/** Mean and 95 percent interval of the per seed difference a minus b. */
export function pairedDifference(
  a: number[],
  b: number[],
): { mean: number; lo: number; hi: number; n: number } {
  const d = a.map((x, i) => x - (b[i] ?? 0));
  const n = d.length;
  const mean = d.reduce((u, v) => u + v, 0) / n;
  const sd = n > 1 ? Math.sqrt(d.reduce((u, v) => u + (v - mean) ** 2, 0) / (n - 1)) : 0;
  const half = n > 1 ? (1.96 * sd) / Math.sqrt(n) : 0;
  return { mean, lo: mean - half, hi: mean + half, n };
}

function Loses({ preds, cmp }: { preds: Prediction[]; cmp: Comparison }) {
  const { t } = useTranslation();
  const s = useSettings();
  const n = (x: number) => formatValue(x, s);
  const p3p2 = pairedDifference(cmp.policies.P3!.regret_per_seed, cmp.policies.P2!.regret_per_seed);
  const p3p0 = pairedDifference(cmp.policies.P3!.regret_per_seed, cmp.policies.P0!.regret_per_seed);
  const misses = preds.filter((p) => p.result === "MISS" || p.id === "PR-E3-3");
  return (
    <section className="card tinted stack" aria-labelledby="loses-h">
      <h2 id="loses-h">{t("policies.loses")}</h2>
      <p>{t("policies.losesIntro")}</p>
      <ul>
        {misses.map((p) => (
          <li key={p.id}>
            <strong>{p.id}</strong> ({p.result}):{" "}
            <span lang="en" dir="ltr">
              {p.prediction}. {p.observed}.
            </span>
          </li>
        ))}
        <li className="num">
          {cmp.generator}: P3 minus P2 {n(p3p2.mean)} ({n(p3p2.lo)} {t("common.to")} {n(p3p2.hi)})
          CU; P3 minus P0 {n(p3p0.mean)} ({n(p3p0.lo)} {t("common.to")} {n(p3p0.hi)}) CU
        </li>
      </ul>
    </section>
  );
}

export function PoliciesScreen() {
  const { t } = useTranslation();
  const s = useSettings();
  const q = usePolicies();
  const [gen, setGen] = useState<"e2" | "e3">("e2");
  const n = (x: number) => formatValue(x, s);
  if (q.isLoading || q.isError || !q.data)
    return (
      <div className="stack">
        <h1>{t("policies.title")}</h1>
        {q.isLoading ? <Loading /> : <ErrorView error={q.error} onRetry={() => void q.refetch()} />}
      </div>
    );
  const cmp = q.data[gen];
  const preds = q.data.predictions;
  const hits = preds.filter((p) => p.result === "HIT").length;
  const name = (p: string) => t(`policies.policyNames.${p}`);
  const pairs: Array<[string, string]> = [
    ["P3", "P0"],
    ["P3", "P1"],
    ["P3", "P2"],
    ["P4", "P3"],
  ];
  return (
    <div className="stack">
      <h1>{t("policies.title")}</h1>
      <p>{t("policies.intro")}</p>
      <fieldset className="row" style={{ border: 0, padding: 0 }}>
        <legend>{t("policies.generator")}</legend>
        {(["e2", "e3"] as const).map((g) => (
          <label key={g} className="row" style={{ gap: "0.3rem" }}>
            <input
              type="radio"
              name="gen"
              value={g}
              checked={gen === g}
              onChange={() => setGen(g)}
            />
            {g === "e2" ? t("policies.g1") : t("policies.g2")}
          </label>
        ))}
      </fieldset>
      <Loses preds={preds} cmp={cmp} />
      <section className="card stack" aria-labelledby="regret-h">
        <h2 id="regret-h">{t("policies.regret")}</h2>
        <DotWhisker
          title={t("policies.regret")}
          description={t("policies.regretDesc")}
          unit="CU"
          rows={POLICIES.filter((p) => p !== "P1").map((p) => ({
            label: name(p),
            mean: cmp.policies[p]!.regret_cu.mean,
            lo: cmp.policies[p]!.regret_cu.lo,
            hi: cmp.policies[p]!.regret_cu.hi,
            highlight: p === "P3" || p === "P4",
          }))}
        />
        <p className="muted">
          {name("P1")}: {n(cmp.policies.P1!.regret_cu.mean)} ({n(cmp.policies.P1!.regret_cu.lo)}{" "}
          {t("common.to")} {n(cmp.policies.P1!.regret_cu.hi)}) CU
        </p>
        <h3>{t("policies.paired")}</h3>
        <p className="muted">{t("policies.pairedNote")}</p>
        <div className="table-wrap" tabIndex={0}>
          <table>
            <tbody>
              {pairs.map(([a, b]) => {
                const d = pairedDifference(
                  cmp.policies[a]!.regret_per_seed,
                  cmp.policies[b]!.regret_per_seed,
                );
                return (
                  <tr key={`${a}${b}`}>
                    <th scope="row">
                      {name(a)} − {name(b)}
                    </th>
                    <td className="num">
                      {n(d.mean)} ({n(d.lo)} {t("common.to")} {n(d.hi)}) CU
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </section>
      <section className="card stack" aria-labelledby="metrics-h">
        <h2 id="metrics-h">{t("policies.metrics")}</h2>
        <div className="table-wrap" tabIndex={0}>
          <table>
            <thead>
              <tr>
                <th scope="col">{t("policies.metric")}</th>
                {POLICIES.map((p) => (
                  <th scope="col" key={p}>
                    {name(p)}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {METRICS.map((m) => (
                <tr key={m}>
                  <th scope="row">
                    <code>{m}</code>
                  </th>
                  {POLICIES.map((p) => {
                    const v = cmp.policies[p]!.metrics[m]!;
                    return (
                      <td key={p} className="num">
                        {n(v.mean)}
                        <br />
                        <span className="muted">
                          ({n(v.lo)} {t("common.to")} {n(v.hi)})
                        </span>
                      </td>
                    );
                  })}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
      <section className="card stack" aria-labelledby="e4-h">
        <h2 id="e4-h">{t("policies.inspection")}</h2>
        <p>
          {t("policies.breakEven")}:{" "}
          <strong className="num">
            {q.data.e4.break_even.break_even_cost_cu === null
              ? "-"
              : `${n(q.data.e4.break_even.break_even_cost_cu)} CU`}
          </strong>
        </p>
        <div className="table-wrap" tabIndex={0}>
          <table>
            <thead>
              <tr>
                <th scope="col">{t("policies.availability")}</th>
                <th scope="col">{t("policies.cost")}</th>
                <th scope="col">{t("policies.diff")}</th>
                <th scope="col">{t("policies.sorties")}</th>
              </tr>
            </thead>
            <tbody>
              {q.data.e4.grid.map((g) => (
                <tr key={`${g.availability}-${g.sortie_cost_cu}`}>
                  <td className="num">{formatPercent(g.availability, s)}</td>
                  <td className="num">{n(g.sortie_cost_cu)}</td>
                  <td className="num">
                    {n(g.p4_minus_p3_cu.mean)} ({n(g.p4_minus_p3_cu.lo)} {t("common.to")}{" "}
                    {n(g.p4_minus_p3_cu.hi)})
                  </td>
                  <td className="num">{formatValue(g.sorties_per_year.mean, s)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
      <section className="card stack" aria-labelledby="pred-h">
        <h2 id="pred-h">{t("policies.predictions")}</h2>
        <p>
          <strong>{t("policies.hits", { hits: n(hits), total: n(preds.length) })}</strong>
        </p>
        <PredictionTable preds={preds} />
      </section>
    </div>
  );
}

export function PredictionTable({ preds }: { preds: Prediction[] }) {
  return (
    <div className="table-wrap" tabIndex={0}>
      <table>
        <tbody>
          {preds.map((p) => (
            <tr key={p.id}>
              <th scope="row">{p.id}</th>
              <td lang="en" dir="ltr">
                {p.prediction}
              </td>
              <td lang="en" dir="ltr">
                {p.observed}
              </td>
              <td>
                <span className={p.result === "MISS" ? "badge warn" : "badge"}>{p.result}</span>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
