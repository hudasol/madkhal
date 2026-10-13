import { useTranslation } from "react-i18next";

/** The two part banner. It is on every screen and has no close control. */
export function Banner() {
  const { t } = useTranslation();
  return (
    <section className="banner" aria-label={t("banner.label")} data-testid="banner">
      <p className="real">{t("banner.evidence")}</p>
      <p className="hypo">{t("banner.hypothetical")}</p>
    </section>
  );
}
