import type { Components, Theme } from "@mui/material/styles";

import { responsiveLayout } from "./tokens";

const MOBILE_MAX = responsiveLayout.dialogFullscreenMaxBreakpoint;

/**
 * Evita zoom automático al enfocar en iOS Safari (font-size &lt; 16px).
 * No deshabilita el zoom manual del usuario.
 */
export const mobileIosInputFontSizeSx = {
  [`@media (max-width: 599.95px)`]: {
    fontSize: "16px",
    lineHeight: 1.4,
  },
} as const;

export function createMobileFormInputThemeOverrides(): Components<Theme> {
  return {
    MuiInputBase: {
      styleOverrides: {
        input: {
          [`@media (max-width: 599.95px)`]: {
            fontSize: "16px",
          },
        },
        inputMultiline: {
          [`@media (max-width: 599.95px)`]: {
            fontSize: "16px",
          },
        },
      },
    },
    MuiOutlinedInput: {
      styleOverrides: {
        input: {
          [`@media (max-width: 599.95px)`]: {
            fontSize: "16px",
          },
        },
      },
    },
    MuiSelect: {
      styleOverrides: {
        select: {
          [`@media (max-width: 599.95px)`]: {
            fontSize: "16px",
          },
        },
      },
    },
  };
}

export { MOBILE_MAX };
