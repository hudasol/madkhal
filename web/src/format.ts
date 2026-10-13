// Number and time formatting. Probabilities are 0 to 1 and shown as percentages.
// Calendar days are UTC days; timestamps are shown in Asia/Dubai with UTC on hover.

export const DISPLAY_TZ = "Asia/Dubai";

export interface FormatOptions {
  lang: "en" | "ar";
  arabicDigits: boolean;
}

function locale(o: FormatOptions): string {
  if (o.lang === "ar") return o.arabicDigits ? "ar-u-nu-arab" : "ar-u-nu-latn";
  return o.arabicDigits ? "en-u-nu-arab" : "en-u-nu-latn";
}

export function formatNumber(x: number, o: FormatOptions, maxDigits = 0): string {
  return new Intl.NumberFormat(locale(o), { maximumFractionDigits: maxDigits }).format(x);
}

/** A probability (0 to 1) as a percentage, one decimal below 1 percent. */
export function formatPercent(p: number, o: FormatOptions): string {
  const pct = p * 100;
  const digits = pct > 0 && pct < 1 ? 1 : 0;
  return new Intl.NumberFormat(locale(o), {
    style: "percent",
    maximumFractionDigits: digits,
    minimumFractionDigits: 0,
  }).format(p);
}

/** A calendar day (YYYY-MM-DD, UTC) in the display language. */
export function formatDay(iso: string, o: FormatOptions): string {
  const d = new Date(`${iso}T00:00:00Z`);
  return new Intl.DateTimeFormat(locale(o), {
    timeZone: "UTC",
    year: "numeric",
    month: "short",
    day: "numeric",
  }).format(d);
}

/** A timestamp in Asia/Dubai, with the UTC form for a tooltip. */
export function formatInstant(iso: string, o: FormatOptions): { local: string; utc: string } {
  const d = new Date(iso);
  const local = new Intl.DateTimeFormat(locale(o), {
    timeZone: DISPLAY_TZ,
    dateStyle: "medium",
    timeStyle: "short",
  }).format(d);
  const utc = `${d.toISOString().slice(0, 16).replace("T", " ")} UTC`;
  return { local, utc };
}
