import { useId, useState } from "react";
import { useTranslation } from "react-i18next";
import { formatDay, formatPercent } from "../format";
import { useSettings } from "../settings";
import { ActionGlyph, type ActionCode } from "./ActionBadge";

interface Props {
  title: string;
  description: string;
  dates: string[];
  actions: string[];
  scales: number[];
  inspect?: boolean[];
}

const W = 720;
const ROW = 22;

/** One mark per day; the glyph shape and pattern encode the action. Table alternative included. */
export function Ribbon({ title, description, dates, actions, scales, inspect }: Props) {
  const { t } = useTranslation();
  const s = useSettings();
  const id = useId();
  const [showTable, setShowTable] = useState(false);
  const n = dates.length;
  const cell = n > 0 ? (W - 20) / n : 0;
  const glyph = Math.max(6, Math.min(16, cell));
  const rtl = s.lang === "ar";
  const x = (i: number) => {
    const v = 10 + i * cell + cell / 2;
    return rtl ? W - v : v;
  };
  const label = (i: number) => {
    const a = actions[i] as ActionCode;
    return a === "DERATE"
      ? `${t("action.DERATE")} ${formatPercent(scales[i] ?? 0, s)}`
      : t(`action.${a}`);
  };
  return (
    <figure className="chart" aria-labelledby={`${id}-c`}>
      <figcaption id={`${id}-c`}>
        <strong>{title}</strong>. {description}
      </figcaption>
      <svg viewBox={`0 0 ${W} ${ROW * 2 + 6}`} role="img" aria-label={`${title}. ${description}`}>
        {dates.map((d, i) => {
          const a = actions[i] as ActionCode;
          return (
            <g key={d} transform={`translate(${x(i) - glyph / 2},4)`}>
              <svg width={glyph} height={glyph} viewBox="0 0 20 20">
                <ActionGlyph action={a} size={20} />
              </svg>
              {inspect?.[i] ? (
                <svg y={ROW} width={glyph} height={glyph} viewBox="0 0 20 20">
                  <ActionGlyph action="INSPECT" size={20} />
                </svg>
              ) : null}
            </g>
          );
        })}
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
                <th scope="col">{t("common.date")}</th>
                <th scope="col">{t("timeline.ribbon")}</th>
              </tr>
            </thead>
            <tbody>
              {dates.map((d, i) => (
                <tr key={d}>
                  <td title={t("common.utcDay")}>{formatDay(d, s)}</td>
                  <td>
                    {label(i)}
                    {inspect?.[i] ? `, ${t("action.INSPECT")}` : ""}
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

export function ActionLegend() {
  const { t } = useTranslation();
  const codes: ActionCode[] = ["GO", "DERATE", "PARK", "NO_SAFE_OPTION_ESCALATE", "INSPECT"];
  return (
    <div className="legend" role="list" aria-label={t("action.legend")}>
      {codes.map((c) => (
        <span key={c} role="listitem">
          <ActionGlyph action={c} />
          <strong>{t(`action.${c}`)}</strong>{" "}
          <span className="muted">{t(`action.explain${c}`)}</span>
        </span>
      ))}
    </div>
  );
}
