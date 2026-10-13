import { useTranslation } from "react-i18next";
import { useSites } from "../api/hooks";
import { useSettings } from "../settings";

export function SiteSelect({ value, onChange }: { value: string; onChange: (v: string) => void }) {
  const { t } = useTranslation();
  const s = useSettings();
  const sites = useSites();
  return (
    <label className="row" style={{ gap: "0.4rem" }}>
      <span>{t("common.site")}</span>
      <select value={value} onChange={(e) => onChange(e.target.value)}>
        {(sites.data ?? []).map((x) => (
          <option key={x.id} value={x.id}>
            {s.lang === "ar" ? x.name_ar : x.name}
          </option>
        ))}
      </select>
    </label>
  );
}

/** Render a query's loading and error states, or the content when data is present. */
export function useSiteName(id: string): string {
  const { t } = useTranslation();
  return t(`place.${id}`);
}
