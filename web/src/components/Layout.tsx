import type { ReactNode } from "react";
import { NavLink } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { MODE } from "../api/client";
import { useSettings, type Theme } from "../settings";
import { Banner } from "./Banner";

export interface NavItem {
  path: string;
  key: string;
}

export function Layout({ nav, children }: { nav: NavItem[]; children: ReactNode }) {
  const { t } = useTranslation();
  const s = useSettings();
  const themes: Theme[] = ["system", "light", "dark"];
  return (
    <>
      <a className="skip-link" href="#main">
        {t("app.skip")}
      </a>
      <header className="app-header">
        <div className="brand">
          <strong>{t("app.name")}</strong>
          <span>{t("app.tagline")}</span>
        </div>
        <div className="settings" role="group" aria-label={t("settings.label")}>
          <span className="mode-badge" title={MODE === "static" ? t("mode.staticNote") : undefined}>
            {MODE === "static" ? t("mode.static") : t("mode.live")}
          </span>
          <button
            type="button"
            className="btn"
            lang={s.lang === "en" ? "ar" : "en"}
            aria-label={t("settings.languageName")}
            onClick={() => s.setLang(s.lang === "en" ? "ar" : "en")}
          >
            {t("settings.language")}
          </button>
          <button
            type="button"
            className="btn"
            aria-pressed={s.arabicDigits}
            onClick={() => s.setArabicDigits(!s.arabicDigits)}
          >
            {t("settings.digits")}
          </button>
          <label className="row" style={{ gap: "0.35rem" }}>
            <span>{t("settings.theme")}</span>
            <select value={s.theme} onChange={(e) => s.setTheme(e.target.value as Theme)}>
              {themes.map((th) => (
                <option key={th} value={th}>
                  {t(`settings.${th}`)}
                </option>
              ))}
            </select>
          </label>
        </div>
      </header>
      <Banner />
      <nav className="main-nav" aria-label={t("nav.label")}>
        <ul>
          {nav.map((n) => (
            <li key={n.path}>
              <NavLink to={n.path} end={n.path === "/"}>
                {t(`nav.${n.key}`)}
              </NavLink>
            </li>
          ))}
        </ul>
      </nav>
      <main id="main" tabIndex={-1}>
        {children}
      </main>
      <footer className="app-footer">
        <p>{t("app.scope")}</p>
      </footer>
    </>
  );
}
