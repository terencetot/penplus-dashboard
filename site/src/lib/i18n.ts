import en from "../../i18n/strings.en.json";
import fr from "../../i18n/strings.fr.json";
import pt from "../../i18n/strings.pt.json";

/**
 * Interface strings come from this registry, in English, French and
 * Portuguese (CLAUDE.md, Design system: "No string is translated inside a
 * component"). The three languages are bundled at build time rather than
 * fetched at runtime: the string set is small and fixed, so this avoids an
 * extra round trip without losing the point of keeping copy out of
 * components -- a translator still only ever edits the JSON files in /i18n.
 */
export type Lang = "en" | "fr" | "pt";
export const LANGS: Lang[] = ["en", "fr", "pt"];
export const LANG_LABELS: Record<Lang, string> = { en: "English", fr: "Français", pt: "Português" };

const DICTS: Record<Lang, Record<string, string>> = { en, fr, pt };
const STORAGE_KEY = "penplus.lang";

let current: Lang = detectInitialLang();

function detectInitialLang(): Lang {
  try {
    const stored = localStorage.getItem(STORAGE_KEY);
    if (stored && LANGS.includes(stored as Lang)) return stored as Lang;
  } catch {
    /* storage unavailable (private browsing, sandboxed preview): fall through */
  }
  const nav = (typeof navigator !== "undefined" && navigator.language.slice(0, 2)) || "en";
  return LANGS.includes(nav as Lang) ? (nav as Lang) : "en";
}

export function getLang(): Lang {
  return current;
}

const listeners = new Set<(lang: Lang) => void>();

export function onLangChange(fn: (lang: Lang) => void): () => void {
  listeners.add(fn);
  return () => listeners.delete(fn);
}

export function setLang(lang: Lang): void {
  current = lang;
  try {
    localStorage.setItem(STORAGE_KEY, lang);
  } catch {
    /* per-viewer convenience only; a failed write must not break the switch */
  }
  document.documentElement.lang = lang;
  for (const fn of listeners) fn(lang);
}

/** Look up `key` in the current language, falling back to English, then the key itself. */
export function t(key: string, vars?: Record<string, string | number>): string {
  const raw = DICTS[current][key] ?? DICTS.en[key] ?? key;
  if (!vars) return raw;
  return raw.replace(/\{(\w+)\}/g, (_, name) => String(vars[name] ?? `{${name}}`));
}
