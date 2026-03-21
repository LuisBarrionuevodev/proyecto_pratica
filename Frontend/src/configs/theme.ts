import { createTheme } from "@mui/material/styles";

import { color as tokenColor } from "../theme/tokens";

const fontStack = `"Tactic Sans", "Roboto", "Arial", sans-serif`;

/**
 * Tema único de la aplicación (modo oscuro + tipografía + primary desde tokens).
 * El ThemeProvider en main.tsx debe usar este tema.
 */
export const appTheme = createTheme({
  palette: {
    mode: "dark",
    primary: {
      main: tokenColor.primary,
    },
  },
  typography: {
    fontFamily: fontStack,
  },
});

/**
 * Alias retrocompatible: antes las pantallas anidaban ThemeProvider con darkTheme.
 * Mantener hasta confirmar que no queda ningún import externo.
 */
export const darkTheme = appTheme;

/** Alias retrocompatible: usado históricamente por main.tsx. */
export const theme = appTheme;
