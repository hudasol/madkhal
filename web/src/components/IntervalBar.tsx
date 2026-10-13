import { useTranslation } from "react-i18next";
import { formatPercent } from "../format";
import { useSettings } from "../settings";

interface Props {
  label: string;
  lo: number;
  median: number;
  hi: number;
}

/** A probability with its 90 percent interval: band from lo to hi, tick at the median. */
export function IntervalBar({ label, lo, median, hi }: Props) {
  const { t } = useTranslation();
  const s = useSettings();
  const f = (x: number) => formatPercent(x, s);
  const text = `${label}: ${t("common.median")} ${f(median)}, ${t("common.interval")} ${f(lo)} ${t("common.to")} ${f(hi)}`;
  const rtl = s.lang === "ar";
  const x = (p: number) => (rtl ? 100 - p * 100 : p * 100);
  const x0 = Math.min(x(lo), x(hi));
  const w = Math.max(Math.abs(x(hi) - x(lo)), 0.6);
  return (
    <div className="ibar">
      <div className="label">
        <span>{label}</span>
        <span className="num">
          {f(median)}{" "}
          <span className="muted">
            ({f(lo)} {t("common.to")} {f(hi)})
          </span>
        </span>
      </div>
      <svg viewBox="0 0 100 10" preserveAspectRatio="none" role="img" aria-label={text}>
        <rect x="0" y="3" width="100" height="4" fill="var(--clear)" />
        <rect
          x={x0}
          y="1"
          width={w}
          height="8"
          fill="var(--band-fill)"
          stroke="var(--band)"
          strokeWidth="0.6"
        />
        <rect x={x(median) - 0.6} y="0" width="1.2" height="10" fill="var(--ink)" />
      </svg>
    </div>
  );
}
