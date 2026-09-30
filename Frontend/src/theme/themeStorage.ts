import type { DigitalizaThemeMode } from "./colors";

export const THEME_STORAGE_KEY = "digitaliza:theme-mode";

/**
 * Lee preferencia persistida. Default producto: dark.
 */
export function readStoredThemeMode(): DigitalizaThemeMode {
  try {
    const raw = localStorage.getItem(THEME_STORAGE_KEY);
    if (raw === "light" || raw === "dark") return raw;
  } catch {
    /* SSR / privacy mode */
  }
  return "dark";
}

export function writeStoredThemeMode(mode: DigitalizaThemeMode): void {
  try {
    localStorage.setItem(THEME_STORAGE_KEY, mode);
  } catch {
    /* ignore */
  }
}
