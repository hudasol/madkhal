import type React from "react";
import { useTranslation } from "react-i18next";
import type { AdvisoryResponse } from "../api/types";
import { formatNumber, formatPercent } from "../format";
import { useSettings } from "../settings";
import { ActionBadge, ActionGlyph, type ActionCode } from "./ActionBadge";

/** Text produced by the API is English; mark it so assistive technology reads it correctly. */
function En({ children }: { children: React.ReactNode }) {
  const s = useSettings();
  return s.lang === "en" ? (
    <>{children}</>
  ) : (
    <span lang="en" dir="ltr">
      {children}
    </span>
  );
}

type T = (k: string, o?: Record<string, unknown>) => string;

/** The "what to do" sentence from the structured action, in the display language. */
function whatText(
  adv: AdvisoryResponse,
  t: T,
  s: { lang: "en" | "ar"; arabicDigits: boolean },
): string {
  const base = t(`action.explain${adv.action}`);
  return adv.action === "DERATE" ? `${base} (${formatPercent(adv.scale, s)})` : base;
}

/** Binding constraint names such as "fouling and water_security", in the display language. */
function bindingText(b: string, t: T): string {
  return b
    .split(" and ")
    .map((x) => (["fouling", "water_security", "dwell"].includes(x) ? t(`advisory.${x}`) : x))
    .join(" + ");
}

/** How close one constraint is to its budget: a bar with a pattern once it is used up. */
export function ConstraintBar({
  name,
  used,
  label,
}: {
  name: string;
  used: number;
  label: string;
}) {
  const { t } = useTranslation();
  const s = useSettings();
  const pct = Math.max(0, Math.min(100, used));
  // For the dwell rule a full bar means the minimum time has passed: satisfied, not breached.
  const isDwell = name.endsWith("-dwell");
  const full = pct >= 100 && !isDwell;
  const text = isDwell
    ? `${label}: ${pct >= 100 ? t("advisory.dwellMet") : t("advisory.dwellHolding", { used: formatPercent(pct / 100, s) })}`
    : `${label}: ${t("advisory.used", { used: formatPercent(pct / 100, s) })}`;
  return (
    <div className="ibar" data-constraint={name}>
      <div className="label">
        <span>{label}</span>
        <span className="num">{text.slice(label.length + 2)}</span>
      </div>
      <svg viewBox="0 0 100 10" preserveAspectRatio="none" role="img" aria-label={text}>
        <defs>
          <pattern
            id={`full-${name}`}
            width="3"
            height="3"
            patternUnits="userSpaceOnUse"
            patternTransform="rotate(45)"
          >
            <line x1="0" y1="0" x2="0" y2="3" stroke="var(--nosafe)" strokeWidth="1.5" />
          </pattern>
        </defs>
        <rect x="0" y="2" width="100" height="6" fill="var(--clear)" />
        <rect
          x={s.lang === "ar" ? 100 - pct : 0}
          y="1"
          width={pct}
          height="8"
          fill={full ? `url(#full-${name})` : "var(--band-fill)"}
          stroke={full ? "var(--nosafe)" : "var(--band)"}
          strokeWidth="0.6"
        />
      </svg>
    </div>
  );
}

export function AdvisoryPanel({
  adv,
  compact = false,
}: {
  adv: AdvisoryResponse;
  compact?: boolean;
}) {
  const { t } = useTranslation();
  const s = useSettings();
  const ex = adv.explanation;
  const ttl =
    adv.time_to_limit_hours === null || adv.time_to_limit_hours === undefined
      ? t("advisory.beyond")
      : t("advisory.hours", { count: Math.round(adv.time_to_limit_hours) });
  return (
    <div className="stack advisory" data-testid={`advisory-${adv.site}`}>
      <div className="row" style={{ justifyContent: "space-between" }}>
        <ActionBadge action={adv.action as ActionCode} scale={adv.scale} large />
        {adv.inspect ? (
          <span className="action-badge" data-action="INSPECT">
            <ActionGlyph action="INSPECT" /> {t("advisory.inspect")}
          </span>
        ) : (
          <span className="muted">{t("advisory.noInspect")}</span>
        )}
      </div>
      <p>
        <strong>{t("advisory.what")}:</strong>{" "}
        {s.lang === "en" ? adv.text.what : whatText(adv, t, s)}
      </p>
      {compact ? (
        <p>
          <strong>{t("advisory.reason")}:</strong> <En>{adv.reasons[0]}</En>
        </p>
      ) : (
        <>
          <p>
            <strong>{t("advisory.why")}:</strong> <En>{adv.text.why}</En>
          </p>
          <p>
            <strong>{t("advisory.change")}:</strong> <En>{adv.text.change}</En>
          </p>
        </>
      )}
      <dl className="facts">
        <div>
          <dt>{t("advisory.binding")}</dt>
          <dd>
            {adv.binding_constraint ? bindingText(adv.binding_constraint, t) : t("advisory.none")}
          </dd>
        </div>
        <div>
          <dt>{t("advisory.evidenceLevel")}</dt>
          <dd className="num">{adv.evidence_level}</dd>
        </div>
        <div>
          <dt>{t("advisory.assumptions")}</dt>
          <dd className="num">{formatPercent(adv.assumption_share, s)}</dd>
        </div>
        <div>
          <dt>{t("advisory.pBreach")}</dt>
          <dd className="num">{formatPercent(adv.p_breach_full_scale, s)}</dd>
        </div>
        <div>
          <dt>{t("advisory.timeToLimit")}</dt>
          <dd className="num">{ttl}</dd>
        </div>
      </dl>
      <div className="stack">
        <h3>{t("advisory.constraints")}</h3>
        {adv.constraints.map((c) => (
          <ConstraintBar
            key={c.name}
            name={`${adv.site}-${c.name}`}
            used={c.used_percent}
            label={t(`advisory.${c.name}`)}
          />
        ))}
      </div>
      {!compact ? (
        <details>
          <summary>{t("advisory.details")}</summary>
          <div className="table-wrap" tabIndex={0}>
            <table>
              <caption className="muted">{t("advisory.candidates")}</caption>
              <thead>
                <tr>
                  <th scope="col">{t("advisory.option")}</th>
                  <th scope="col">{t("advisory.fouling")}</th>
                  <th scope="col">{t("advisory.water_security")}</th>
                  <th scope="col">{t("advisory.expectedUnserved")}</th>
                  <th scope="col">{t("advisory.feasible")}</th>
                </tr>
              </thead>
              <tbody>
                {ex.candidates.map((c) => (
                  <tr key={`${c.action}-${c.scale}`}>
                    <td>
                      <ActionBadge action={c.action as ActionCode} scale={c.scale} />
                    </td>
                    <td className="num">{formatPercent(c.p_fouling_breach, s)}</td>
                    <td className="num">{formatPercent(c.p_water_breach, s)}</td>
                    <td className="num">{formatNumber(c.expected_unserved_m3, s)} m3</td>
                    <td>{c.feasible ? t("advisory.yes") : t("advisory.no")}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <ul>
            {ex.what_would_change.map((w) => (
              <li key={w}>
                <En>{w}</En>
              </li>
            ))}
          </ul>
          <p className="muted num">
            id {adv.id} · inputs {adv.inputs_hash.slice(0, 16)} · seed {adv.seed}
          </p>
        </details>
      ) : null}
    </div>
  );
}
