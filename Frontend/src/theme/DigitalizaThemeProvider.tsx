import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import { ThemeProvider } from "@mui/material/styles";

import { createAppTheme } from "../configs/theme";
import { applyDigitalizaCssVariables } from "./applyCssVariables";
import {
  getSemanticColors,
  type DigitalizaThemeMode,
  type SemanticColors,
} from "./colors";
import { readStoredThemeMode, writeStoredThemeMode } from "./themeStorage";

type DigitalizaThemeContextValue = {
  mode: DigitalizaThemeMode;
  colors: SemanticColors;
  setMode: (mode: DigitalizaThemeMode) => void;
  toggleMode: () => void;
};

const DigitalizaThemeContext = createContext<DigitalizaThemeContextValue | null>(null);

export function setDocumentThemeMode(mode: DigitalizaThemeMode): void {
  document.documentElement.dataset.theme = mode;
}

type DigitalizaThemeProviderProps = {
  children: ReactNode;
  /** Modo resuelto síncronamente antes del primer render (evita flash). */
  initialMode?: DigitalizaThemeMode;
};

export function DigitalizaThemeProvider({
  children,
  initialMode,
}: DigitalizaThemeProviderProps) {
  const [mode, setModeState] = useState<DigitalizaThemeMode>(
    () => initialMode ?? readStoredThemeMode()
  );

  const colors = useMemo(() => getSemanticColors(mode), [mode]);
  const muiTheme = useMemo(() => createAppTheme(mode), [mode]);

  const setMode = useCallback((next: DigitalizaThemeMode) => {
    setModeState(next);
    writeStoredThemeMode(next);
  }, []);

  const toggleMode = useCallback(() => {
    setMode(mode === "dark" ? "light" : "dark");
  }, [mode, setMode]);

  useEffect(() => {
    applyDigitalizaCssVariables(colors);
    setDocumentThemeMode(mode);
  }, [colors, mode]);

  const value = useMemo(
    () => ({ mode, colors, setMode, toggleMode }),
    [mode, colors, setMode, toggleMode]
  );

  return (
    <DigitalizaThemeContext.Provider value={value}>
      <ThemeProvider theme={muiTheme}>{children}</ThemeProvider>
    </DigitalizaThemeContext.Provider>
  );
}

export function useDigitalizaTheme(): DigitalizaThemeContextValue {
  const ctx = useContext(DigitalizaThemeContext);
  if (!ctx) {
    throw new Error("useDigitalizaTheme debe usarse dentro de DigitalizaThemeProvider");
  }
  return ctx;
}
