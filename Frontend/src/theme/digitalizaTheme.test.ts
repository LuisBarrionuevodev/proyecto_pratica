import { describe, expect, it, beforeEach, vi } from "vitest";

import { applyDigitalizaCssVariables, CSS_VAR_NAMES } from "./applyCssVariables";
import { darkColors, lightColors } from "./colors";
import { readStoredThemeMode, writeStoredThemeMode, THEME_STORAGE_KEY } from "./themeStorage";
import { setDocumentThemeMode } from "./DigitalizaThemeProvider";

function createStyleRoot(): HTMLElement {
  const props = new Map<string, string>();
  return {
    style: {
      setProperty: (name: string, value: string) => props.set(name, value),
      getPropertyValue: (name: string) => props.get(name) ?? "",
    },
  } as HTMLElement;
}

describe("FRONT-PROD.3 — CSS variables y persistencia", () => {
  const store = new Map<string, string>();

  beforeEach(() => {
    store.clear();
    vi.stubGlobal("localStorage", {
      getItem: (key: string) => store.get(key) ?? null,
      setItem: (key: string, value: string) => store.set(key, value),
      removeItem: (key: string) => store.delete(key),
      clear: () => store.clear(),
    });
  });

  it("applyDigitalizaCssVariables alterna --d-text-primary sin reload", () => {
    const root = createStyleRoot();
    applyDigitalizaCssVariables(darkColors, root);
    expect(root.style.getPropertyValue(CSS_VAR_NAMES.textPrimary)).toBe(darkColors.text.primary);

    applyDigitalizaCssVariables(lightColors, root);
    expect(root.style.getPropertyValue(CSS_VAR_NAMES.textPrimary)).toBe(lightColors.text.primary);
  });

  it("readStoredThemeMode default dark y valida valores", () => {
    expect(readStoredThemeMode()).toBe("dark");
    store.set(THEME_STORAGE_KEY, "light");
    expect(readStoredThemeMode()).toBe("light");
    store.set(THEME_STORAGE_KEY, "invalid");
    expect(readStoredThemeMode()).toBe("dark");
  });

  it("writeStoredThemeMode persiste light", () => {
    writeStoredThemeMode("light");
    expect(store.get(THEME_STORAGE_KEY)).toBe("light");
  });

  it("setDocumentThemeMode establece data-theme", () => {
    const html = { dataset: {} as DOMStringMap };
    vi.stubGlobal("document", { documentElement: html });
    setDocumentThemeMode("light");
    expect(html.dataset.theme).toBe("light");
    setDocumentThemeMode("dark");
    expect(html.dataset.theme).toBe("dark");
  });

  it("darkColors y lightColors no se mutan al aplicar variables", () => {
    const root = createStyleRoot();
    const darkPrimary = darkColors.text.primary;
    const lightPrimary = lightColors.text.primary;
    applyDigitalizaCssVariables(lightColors, root);
    applyDigitalizaCssVariables(darkColors, root);
    expect(darkColors.text.primary).toBe(darkPrimary);
    expect(lightColors.text.primary).toBe(lightPrimary);
  });
});
