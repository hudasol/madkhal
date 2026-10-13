import i18n from "i18next";
import { initReactI18next } from "react-i18next";
import ar from "./ar";
import en from "./en";

export type Lang = "en" | "ar";

export function initialLang(): Lang {
  try {
    const v = window.localStorage.getItem("madkhal.lang");
    if (v === "ar" || v === "en") return v;
  } catch {
    // storage unavailable: fall back to English
  }
  return "en";
}

void i18n.use(initReactI18next).init({
  resources: { en: { translation: en }, ar: { translation: ar } },
  lng: initialLang(),
  fallbackLng: "en",
  interpolation: { escapeValue: false },
  returnNull: false,
});

export function applyDocumentLanguage(lang: Lang): void {
  document.documentElement.lang = lang;
  document.documentElement.dir = lang === "ar" ? "rtl" : "ltr";
}

export default i18n;
