import { useId } from "react";
import { useTranslation } from "react-i18next";
import { formatPercent } from "../format";
import { useSettings } from "../settings";

export type ActionCode = "GO" | "DERATE" | "PARK" | "NO_SAFE_OPTION_ESCALATE" | "INSPECT";

const COLOR: Record<ActionCode, string> = {
  GO: "var(--go)",
  DERATE: "var(--derate)",
  PARK: "var(--park)",
  NO_SAFE_OPTION_ESCALATE: "var(--nosafe)",
  INSPECT: "var(--inspect)",
};

/** Shape and pattern per action, so colour is never the only cue:
 *  GO solid circle, DERATE hatched diamond, PARK crossed square,
 *  NO SAFE OPTION octagon with an exclamation mark, INSPECT outlined triangle. */
export function ActionGlyph({ action, size = 18 }: { action: ActionCode; size?: number }) {
  const id = useId();
  const c = COLOR[action];
  return (
    <svg width={size} height={size} viewBox="0 0 20 20" aria-hidden="true" focusable="false">
      <defs>
        <pattern
          id={`${id}-h`}
          width="3"
          height="3"
          patternUnits="userSpaceOnUse"
          patternTransform="rotate(45)"
        >
          <line x1="0" y1="0" x2="0" y2="3" stroke={c} strokeWidth="1.4" />
        </pattern>
      </defs>
      {action === "GO" ? <circle cx="10" cy="10" r="8" fill={c} /> : null}
      {action === "DERATE" ? (
        <polygon points="10,1 19,10 10,19 1,10" fill={`url(#${id}-h)`} stroke={c} strokeWidth="2" />
      ) : null}
      {action === "PARK" ? (
        <g>
          <rect x="2" y="2" width="16" height="16" fill="none" stroke={c} strokeWidth="2.5" />
          <path d="M4 4 L16 16 M16 4 L4 16" stroke={c} strokeWidth="2.5" />
        </g>
      ) : null}
      {action === "NO_SAFE_OPTION_ESCALATE" ? (
        <g>
          <polygon points="6,1 14,1 19,6 19,14 14,19 6,19 1,14 1,6" fill={c} />
          <rect x="9" y="4.5" width="2" height="7" fill="var(--bg)" />
          <rect x="9" y="13.5" width="2" height="2" fill="var(--bg)" />
        </g>
      ) : null}
      {action === "INSPECT" ? (
        <polygon points="10,2 19,18 1,18" fill="none" stroke={c} strokeWidth="2.5" />
      ) : null}
    </svg>
  );
}

export function ActionBadge({
  action,
  scale,
  large = false,
}: {
  action: ActionCode;
  scale?: number;
  large?: boolean;
}) {
  const { t } = useTranslation();
  const s = useSettings();
  const label =
    action === "DERATE" && scale !== undefined
      ? `${t("action.DERATE")} ${formatPercent(scale, s)}`
      : t(`action.${action}`);
  return (
    <span
      className={`action-badge${large ? " large" : ""}`}
      style={{ borderColor: COLOR[action], color: COLOR[action] }}
      data-action={action}
    >
      <ActionGlyph action={action} size={large ? 34 : 18} />
      <span className="action-text">{label}</span>
    </span>
  );
}
