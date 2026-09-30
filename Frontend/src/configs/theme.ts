import { createTheme } from "@mui/material/styles";
import { FONT_FAMILY_UI } from "../theme/typography";
import { getSemanticColors, type DigitalizaThemeMode } from "../theme/colors";

/**
 * Crea el tema MUI para el modo Digitaliza indicado.
 */
export function createAppTheme(mode: DigitalizaThemeMode) {
  const c = getSemanticColors(mode);

  return createTheme({
    palette: {
      mode,
      primary: {
        main: c.action.primary,
      },
      background: {
        default: c.surface.app,
        paper: c.surface.panel,
      },
      text: {
        primary: c.text.primary,
        secondary: c.text.secondary,
        disabled: c.text.disabled,
      },
      divider: c.border.subtle,
      success: {
        main: c.status.success,
      },
      warning: {
        main: c.status.warning,
      },
      error: {
        main: c.status.error,
      },
      info: {
        main: c.status.info,
      },
    },
    typography: {
      fontFamily: FONT_FAMILY_UI,
    },
  });
}

/** @deprecated Usar `createAppTheme("dark")` o `DigitalizaThemeProvider`. */
export const appTheme = createAppTheme("dark");

/** Alias retrocompatible. */
export const darkTheme = appTheme;

/** Alias retrocompatible. */
export const theme = appTheme;
