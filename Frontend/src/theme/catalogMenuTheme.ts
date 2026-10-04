import type { Components, Theme } from "@mui/material/styles";

import type { DigitalizaThemeMode } from "./colors";
import type { SemanticColors } from "./colors/semanticColorsType";

/**
 * Superficie sólida para menús de catálogo (Select / Autocomplete / Menu).
 * Sin glass ni backdrop-filter; legible en light y dark.
 */
export function catalogDropdownPaperStyle(c: SemanticColors, mode: DigitalizaThemeMode) {
  const backgroundColor = mode === "light" ? c.surface.tableRowEven : c.surface.panel;
  return {
    backgroundColor,
    backgroundImage: "none",
    color: c.text.primary,
    border: `1px solid ${c.border.default}`,
    boxShadow: c.shadow.panel,
    backdropFilter: "none",
    WebkitBackdropFilter: "none",
  };
}

/** Overrides MUI centralizados para listas desplegables de catálogo. */
export function createCatalogMenuThemeOverrides(
  c: SemanticColors,
  mode: DigitalizaThemeMode
): Components<Theme> {
  const paper = catalogDropdownPaperStyle(c, mode);

  return {
    MuiMenu: {
      styleOverrides: {
        paper: {
          ...paper,
        },
        list: {
          paddingTop: 4,
          paddingBottom: 4,
        },
      },
    },
    MuiAutocomplete: {
      styleOverrides: {
        paper: {
          ...paper,
        },
        listbox: {
          ...paper,
          border: "none",
          boxShadow: "none",
          maxHeight: 280,
        },
        option: {
          color: c.text.primary,
          "&[aria-selected='true']": {
            backgroundColor: c.action.selected,
          },
          '&[aria-selected="true"].Mui-focused': {
            backgroundColor: c.action.selected,
          },
          "&.Mui-focused": {
            backgroundColor: c.action.hover,
          },
        },
      },
    },
    MuiMenuItem: {
      styleOverrides: {
        root: {
          color: c.text.primary,
          "&.Mui-selected": {
            backgroundColor: c.action.selected,
            "&:hover": {
              backgroundColor: c.action.selected,
            },
          },
          "&:hover": {
            backgroundColor: c.action.hover,
          },
        },
      },
    },
    MuiPopover: {
      styleOverrides: {
        paper: {
          ...paper,
        },
      },
    },
  };
}
