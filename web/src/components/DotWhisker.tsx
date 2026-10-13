import { useId, useState } from "react";
import { useTranslation } from "react-i18next";
import { formatValue } from "../format";
import { useSettings } from "../settings";

export interface DotRow {
  label: string;
  mean: number;
  lo: number;
  hi: number;
  highlight?: boolean;
}

/** Means with 95 percent intervals on a shared horizontal axis. Never a bare point. */
export function DotWhisker({
  title,
  description,
  rows,
  unit,
}: {
  title: string;
  description: string;
  rows: DotRow[];
  unit: string;
}) {
  const { t } = useTranslation();
  const s = useSettings();
  const id = useId();
  const [showTable, setShowTable] = useState(false);
  const W = 720;
  const LEFT = 210;
  const RIGHT = 20;
  const H = rows.length * 34 + 30;
  const lo = Math.min(0, ...rows.map((r) => r.lo));
  const hi = Math.max(...rows.map((r) => r.hi), 1);
  const rtl = s.lang === "ar";
  const sx = (v: number) => {
    const f = (v - lo) / (hi - lo || 1);
    const x = LEFT + f * (W - LEFT - RIGHT);
    return rtl ? W - x : x;
  };
  const n = (v: number) => formatValue(v, s);
  return (
    <figure className="chart" aria-labelledby={`${id}-c`}>
      <figcaption id={`${id}-c`}>
        <strong>{title}</strong>. {description}
      </figcaption>
      <svg viewBox={`0 0 ${W} ${H}`} role="img" aria-label={`${title}. ${description}`}>
        <line
          x1={sx(0)}
          x2={sx(0)}
          y1={6}
          y2={H - 20}
          stroke="var(--border)"
          strokeDasharray="4 3"
        />
        {rows.map((r, i) => {
          const y = 20 + i * 34;
          return (
            <g key={r.label}>
              <text
                x={rtl ? W - 6 : 6}
                y={y + 4}
                fontSize="13"
                textAnchor="start"
                direction={rtl ? "rtl" : "ltr"}
                fill="var(--text)"
                fontWeight={r.highlight ? 700 : 400}
              >
                {r.label}
              </text>
              <line
                x1={sx(r.lo)}
                x2={sx(r.hi)}
                y1={y}
                y2={y}
                stroke="var(--line)"
                strokeWidth="3"
              />
              <line
                x1={sx(r.lo)}
                x2={sx(r.lo)}
                y1={y - 7}
                y2={y + 7}
                stroke="var(--line)"
                strokeWidth="2"
              />
              <line
                x1={sx(r.hi)}
                x2={sx(r.hi)}
                y1={y - 7}
                y2={y + 7}
                stroke="var(--line)"
                strokeWidth="2"
              />
              <rect
                x={sx(r.mean) - 5}
                y={y - 5}
                width="10"
                height="10"
                fill={r.highlight ? "var(--line)" : "var(--surface-2)"}
                stroke="var(--ink)"
                strokeWidth="2"
              />
            </g>
          );
        })}
        <text
          x={sx(lo)}
          y={H - 4}
          fontSize="11"
          textAnchor={rtl ? "end" : "start"}
          fill="var(--text-muted)"
        >
          {n(lo)}
        </text>
        <text
          x={sx(hi)}
          y={H - 4}
          fontSize="11"
          textAnchor={rtl ? "start" : "end"}
          fill="var(--text-muted)"
        >
          {n(hi)} {unit}
        </text>
      </svg>
      <button
        type="button"
        className="btn"
        aria-expanded={showTable}
        onClick={() => setShowTable((v) => !v)}
      >
        {showTable ? t("common.hideTable") : t("common.showTable")}
      </button>
      {showTable ? (
        <div className="table-wrap" tabIndex={0}>
          <table>
            <caption className="muted">{title}</caption>
            <thead>
              <tr>
                <th scope="col"> </th>
                <th scope="col">{t("common.mean")}</th>
                <th scope="col">{t("common.interval95")}</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((r) => (
                <tr key={r.label}>
                  <th scope="row">{r.label}</th>
                  <td className="num">{n(r.mean)}</td>
                  <td className="num">
                    {n(r.lo)} {t("common.to")} {n(r.hi)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : null}
    </figure>
  );
}
