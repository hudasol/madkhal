import { useTranslation } from "react-i18next";

type Known = "SWRO" | "OLCI" | "MODIS";

/** An abbreviation with its definition on hover and for screen readers. */
export function Abbr({ k }: { k: Known }) {
  const { t } = useTranslation();
  return <abbr title={t(`abbr.${k}`)}>{k}</abbr>;
}
