import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import type { ReactNode } from "react";
import i18n, { applyDocumentLanguage, initialLang, type Lang } from "./i18n";
import type { FormatOptions } from "./format";

export type Theme = "system" | "light" | "dark";

interface Settings extends FormatOptions {
  theme: Theme;
  setLang: (l: Lang) => void;
  setArabicDigits: (v: boolean) => void;
  setTheme: (t: Theme) => void;
}

const Ctx = createContext<Settings | null>(null);

function read(key: string): string | null {
  try {
    return window.localStorage.getItem(key);
  } catch {
    return null;
  }
}

function write(key: string, value: string): void {
  try {
    window.localStorage.setItem(key, value);
  } catch {
    // storage unavailable: settings last for this page only
  }
}

export function SettingsProvider({ children }: { children: ReactNode }) {
  const [lang, setLangState] = useState<Lang>(initialLang());
  const [arabicDigits, setDigitsState] = useState<boolean>(read("madkhal.digits") === "arab");
  const [theme, setThemeState] = useState<Theme>(() => {
    const t = read("madkhal.theme");
    return t === "light" || t === "dark" ? t : "system";
  });

  useEffect(() => {
    applyDocumentLanguage(lang);
    void i18n.changeLanguage(lang);
  }, [lang]);

  useEffect(() => {
    const root = document.documentElement;
    if (theme === "system") root.removeAttribute("data-theme");
    else root.setAttribute("data-theme", theme);
  }, [theme]);

  const setLang = useCallback((l: Lang) => {
    write("madkhal.lang", l);
    setLangState(l);
  }, []);
  const setArabicDigits = useCallback((v: boolean) => {
    write("madkhal.digits", v ? "arab" : "latn");
    setDigitsState(v);
  }, []);
  const setTheme = useCallback((t: Theme) => {
    write("madkhal.theme", t);
    setThemeState(t);
  }, []);

  const value = useMemo(
    () => ({ lang, arabicDigits, theme, setLang, setArabicDigits, setTheme }),
    [lang, arabicDigits, theme, setLang, setArabicDigits, setTheme],
  );
  return <Ctx.Provider value={value}>{children}</Ctx.Provider>;
}

export function useSettings(): Settings {
  const v = useContext(Ctx);
  if (!v) throw new Error("useSettings outside SettingsProvider");
  return v;
}
