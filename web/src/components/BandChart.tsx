import { useId, useState } from "react";
import { useTranslation } from "react-i18next";
import { formatDay, formatPercent } from "../format";
import { useSettings } from "../settings";
import type { Band } from "../api/types";

interface Props {
  title: string;
  description: string;
  dates: string[];
  band: Band;
  clear?: boolean[];
  alert?: boolean[];
}

const W = 720;
const H = 220;
const PAD_X = 44;
const PAD_TOP = 12;
const PLOT_H = 150;
const STRIP_Y = PAD_TOP + PLOT_H + 18;

/** A probability over time: median line, 90 percent band, and a coverage strip below.
 *  Always paired with a table alternative. */
export function BandChart({ title, description, dates, band, clear, alert }: Props) {
  const { t } = useTranslation();
  const s = useSettings();
  const [showTable, setShowTable] = useState(false);
  const id = useId();
  const n = dates.length;
  const rtl = s.lang === "ar";
  const xi = (i: number) => {
    const frac = n > 1 ? i / (n - 1) : 0.5;
    const x = PAD_X + frac * (W - 2 * PAD_X);
    return rtl ? W - x : x;
  };
  const y = (p: number) => PAD_TOP + (1 - p) * PLOT_H;
  const upper = band.hi.map((v, i) => `${xi(i)},${y(v)}`);
  const lower = band.lo.map((v, i) => `${xi(i)},${y(v)}`).reverse();
  const median = band.median.map((v, i) => `${i === 0 ? "M" : "L"}${xi(i)},${y(v)}`).join(" ");
  const cellW = n > 0 ? (W - 2 * PAD_X) / n : 0;
  const pct = (p: number) => formatPercent(p, s);
  return (
    <figure className="chart" aria-labelledby={`${id}-t`}>
      <figcaption id={`${id}-t`}>
        <strong>{title}</strong>. {description}
      </figcaption>
      <svg viewBox={`0 0 ${W} ${H}`} role="img" aria-label={`${title}. ${description}`}>
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
        {[0, 0.25, 0.5, 0.75, 1].map((p) => (
          <g key={p}>
            <line
              x1={PAD_X}
              x2={W - PAD_X}
              y1={y(p)}
              y2={y(p)}
              stroke="var(--border)"
              strokeOpacity="0.25"
            />
            <text
              x={rtl ? W - PAD_X + 6 : PAD_X - 6}
              y={y(p) + 4}
              fontSize="11"
              textAnchor={rtl ? "start" : "end"}
              fill="var(--text-muted)"
            >
              {pct(p)}
            </text>
          </g>
        ))}
        {n > 0 ? (
          <>
            <polygon
              points={[...upper, ...lower].join(" ")}
              fill="var(--band-fill)"
              stroke="var(--band)"
              strokeWidth="1"
            />
            <path d={median} fill="none" stroke="var(--line)" strokeWidth="2.5" />
          </>
        ) : null}
        {clear && alert
          ? dates.map((d, i) => {
              const x = rtl ? xi(i) - cellW / 2 : xi(i) - cellW / 2;
              const state = alert[i] ? "alert" : clear[i] ? "clear" : "nodata";
              const fill =
                state === "alert"
                  ? "var(--alert-cell)"
                  : state === "clear"
                    ? "var(--clear)"
                    : `url(#${id}-hatch)`;
              return (
                <rect
                  key={d}
                  x={x}
                  y={STRIP_Y}
                  width={Math.max(cellW, 1)}
                  height={14}
                  fill={fill}
                />
              );
            })
          : null}
        {n > 0 ? (
          <>
            <text
              x={xi(0)}
              y={H - 6}
              fontSize="11"
              textAnchor="middle"
              direction={rtl ? "rtl" : "ltr"}
              fill="var(--text-muted)"
            >
              {formatDay(dates[0]!, s)}
            </text>
            <text
              x={xi(n - 1)}
              y={H - 6}
              fontSize="11"
              textAnchor="middle"
              direction={rtl ? "rtl" : "ltr"}
              fill="var(--text-muted)"
            >
              {formatDay(dates[n - 1]!, s)}
            </text>
          </>
        ) : null}
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
        <div className="table-wrap">
          <table>
            <caption className="muted">{title}</caption>
            <thead>
              <tr>
                <th scope="col">{t("common.date")}</th>
                <th scope="col">{t("common.median")}</th>
                <th scope="col">{t("common.interval")}</th>
                {clear ? <th scope="col">{t("evidence.calendar")}</th> : null}
              </tr>
            </thead>
            <tbody>
              {dates.map((d, i) => (
                <tr key={d}>
                  <td title={t("common.utcDay")}>{formatDay(d, s)}</td>
                  <td className="num">{pct(band.median[i]!)}</td>
                  <td className="num">
                    {pct(band.lo[i]!)} {t("common.to")} {pct(band.hi[i]!)}
                  </td>
                  {clear && alert ? (
                    <td>
                      {alert[i]
                        ? t("evidence.alert")
                        : clear[i]
                          ? t("evidence.clear")
                          : t("evidence.nodata")}
                    </td>
                  ) : null}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : null}
    </figure>
  );
}
