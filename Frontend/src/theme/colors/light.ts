import type { SemanticColors } from "./semanticColorsType";
import { darkColors } from "./dark";

/**
 * Paleta semántica modo claro — misma estructura que dark, identidad Digitaliza (#0166FF).
 */
export const lightColors = {
  surface: {
    app: "#F0F2F5",
    sidebar: "rgba(255, 255, 255, 0.94)",
    content: "rgba(255, 255, 255, 0.90)",
    panel: "rgba(255, 255, 255, 0.82)",
    panelSubtle: "rgba(0, 0, 0, 0.035)",
    panelElevated: "#FFFFFF",
    input: "#F4F5F7",
    overlay: "rgba(15, 23, 42, 0.42)",
    dialogTitle: "rgba(0, 0, 0, 0.04)",
    dialogContent: "rgba(248, 250, 252, 0.96)",
    dialogActions: "rgba(0, 0, 0, 0.03)",
    tableRowEven: "#FFFFFF",
    tableRowOdd: "#F7F8FA",
    tableRowHover: "#EEF1F5",
    tableRowSelected: "rgba(1, 102, 255, 0.10)",
    tableRowSelectedHover: "rgba(1, 102, 255, 0.16)",
    alertInfo: "#F7F8FA",
    scrollbarTrack: "#F0F2F5",
    scrollbarThumb: "#C5CAD3",
    scrollbarThumbHover: "#AAB0BA",
  },
  text: {
    primary: "#1A1D23",
    secondary: "rgba(26, 29, 35, 0.72)",
    muted: "rgba(26, 29, 35, 0.48)",
    inverse: "#FFFFFF",
    disabled: "rgba(26, 29, 35, 0.38)",
  },
  border: {
    subtle: "rgba(0, 0, 0, 0.06)",
    default: "rgba(0, 0, 0, 0.10)",
    strong: "#D5DAE3",
    active: "rgba(1, 102, 255, 0.45)",
    neo: "#1A1D23",
  },
  action: {
    primary: "#0166FF",
    primaryHover: "#0055DD",
    primaryMuted: "rgba(1, 102, 255, 0.12)",
    primaryGlow: "rgba(1, 102, 255, 0.22)",
    hover: "rgba(0, 0, 0, 0.04)",
    selected: "rgba(0, 0, 0, 0.06)",
    tabSelected: "rgba(1, 102, 255, 0.10)",
    tabSelectedHover: "rgba(1, 102, 255, 0.16)",
    tabPrimarySelected: "rgba(1, 102, 255, 0.14)",
    tabPrimarySelectedHover: "rgba(1, 102, 255, 0.20)",
  },
  status: {
    success: "#1B8A3E",
    successSurface: "#E8F5EC",
    warning: "#E67E00",
    warningSurface: "#FFF4E5",
    error: "#D32F2F",
    errorSurface: "#FDECEA",
    info: "#0166FF",
  },
  shadow: {
    sidebar: "0 8px 24px rgba(15, 23, 42, 0.08)",
    content: "0 10px 32px rgba(15, 23, 42, 0.10)",
    panel: "0 4px 16px rgba(15, 23, 42, 0.08)",
    neoOffset: "4px 4px 0px rgba(26, 29, 35, 0.85)",
    authCard: darkColors.shadow.authCard,
  },
  /** Rutas públicas: diseño claro institucional fijo en V1. */
  auth: { ...darkColors.auth },
  primitive: {
    black: "#000000",
    white: "#FFFFFF",
    grayMedium: "#5C6370",
    grayLight: "#D9D9D9",
    grayLighter: "#F5F5F5",
  },
} satisfies SemanticColors;
