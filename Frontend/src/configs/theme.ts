import { createTheme } from "@mui/material/styles";
import { FONT_FAMILY_UI } from "../theme/typography";
import { darkColors } from "../theme/colors";

const c = darkColors;

/**
 * Tema único de la aplicación (modo oscuro + tipografía + tokens semánticos).
 * El ThemeProvider en main.tsx debe usar este tema.
 */
export const appTheme = createTheme({
  palette: {
    mode: "dark",
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

/**
 * Alias retrocompatible: antes las pantallas anidaban ThemeProvider con darkTheme.
 * Mantener hasta confirmar que no queda ningún import externo.
 */
export const darkTheme = appTheme;

/** Alias retrocompatible: usado históricamente por main.tsx. */
export const theme = appTheme;
