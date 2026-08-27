import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ChangeEvent, type PropsWithChildren } from "react";

import { Select } from "../components";
import { en, type Messages, type TranslationKey } from "./locales/en";
import { ms } from "./locales/ms";
import { zh } from "./locales/zh";

export type Locale = "en" | "ms" | "zh";
export type TranslationValues = Record<string, string | number>;
export type Translator = (key: TranslationKey, values?: TranslationValues) => string;

export const localeMessages: Record<Locale, Messages> = { en, ms, zh };

const LOCALE_STORAGE_KEY = "libraryos_locale";
const supportedLocales: Locale[] = ["en", "ms", "zh"];

interface I18nContextValue {
  locale: Locale;
  setLocale: (locale: Locale) => void;
  t: Translator;
}

const I18nContext = createContext<I18nContextValue | undefined>(undefined);

function isLocale(value: string | null): value is Locale {
  return value !== null && supportedLocales.includes(value as Locale);
}

function readInitialLocale(): Locale {
  try {
    const stored = window.localStorage.getItem(LOCALE_STORAGE_KEY);
    return isLocale(stored) ? stored : "en";
  } catch {
    return "en";
  }
}

function interpolate(template: string, values?: TranslationValues): string {
  if (!values) return template;
  return template.replace(/\{\{(\w+)\}\}/g, (match, key: string) => {
    const value = values[key];
    return value === undefined ? match : String(value);
  });
}

export function I18nProvider({ children }: PropsWithChildren) {
  const [locale, setLocaleState] = useState<Locale>(readInitialLocale);

  const setLocale = useCallback((nextLocale: Locale) => {
    setLocaleState(nextLocale);
    try {
      window.localStorage.setItem(LOCALE_STORAGE_KEY, nextLocale);
    } catch {
      // Language switching still works when browser storage is unavailable.
    }
  }, []);

  useEffect(() => {
    document.documentElement.lang = locale;
  }, [locale]);

  const t = useCallback<Translator>(
    (key, values) => interpolate(localeMessages[locale][key] ?? localeMessages.en[key], values),
    [locale],
  );

  const value = useMemo(() => ({ locale, setLocale, t }), [locale, t]);
  return <I18nContext.Provider value={value}>{children}</I18nContext.Provider>;
}

export function useTranslation(): I18nContextValue {
  const context = useContext(I18nContext);
  if (!context) {
    throw new Error("useTranslation must be used inside I18nProvider.");
  }
  return context;
}

const languageOptions: Array<{ value: Locale; key: TranslationKey }> = [
  { value: "en", key: "language.en" },
  { value: "ms", key: "language.ms" },
  { value: "zh", key: "language.zh" },
];

export function LanguageSwitcher() {
  const { locale, setLocale, t } = useTranslation();

  function changeLocale(event: ChangeEvent<HTMLSelectElement>) {
    const nextLocale = event.target.value;
    if (isLocale(nextLocale)) setLocale(nextLocale);
  }

  return (
    <label className="shrink-0">
      <span className="sr-only">{t("language.label")}</span>
      <Select
        aria-label={t("language.label")}
        className="!mt-0 !w-auto min-w-32 py-2 text-xs"
        onChange={changeLocale}
        value={locale}
      >
        {languageOptions.map((option) => (
          <option key={option.value} value={option.value}>{t(option.key)}</option>
        ))}
      </Select>
    </label>
  );
}

export { en, ms, zh };
