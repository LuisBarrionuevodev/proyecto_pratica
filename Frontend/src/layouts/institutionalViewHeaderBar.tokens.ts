import type { SxProps, Theme } from "@mui/material/styles";
import { FONT_FAMILY_UI } from "../theme/typography";

import { GLASS_COLORS } from "../styles/GlassStyles";/**
 * Tokens del header institucional del shell (F3.8a): vista a la izquierda, fecha del día (YYYY-MM-DD local) a la derecha.
 * Usar siempre el mismo preset para color, padding y tipografía responsive entre vistas.
 */
export const institutionalViewHeaderBarSx: SxProps<Theme> = {
  display: "flex",
  alignItems: "center",
  justifyContent: "space-between",
  gap: { xs: 1, sm: 2 },
  px: 2.5,
  py: 1.25,
  borderBottom: `1px solid ${GLASS_COLORS.borderLight}`,
  flexShrink: 0,
};

export const institutionalViewHeaderTitleRowSx: SxProps<Theme> = {
  display: "flex",
  alignItems: "center",
  gap: 0.5,
  minWidth: 0,
};

export const institutionalViewHeaderTitleSx: SxProps<Theme> = {
  fontFamily: FONT_FAMILY_UI,
  fontSize: "12px",
  fontWeight: 500,
  color: GLASS_COLORS.textSecondary,
  letterSpacing: "0.3px",
  overflow: "hidden",
  textOverflow: "ellipsis",
  whiteSpace: "nowrap",
};

export const institutionalViewHeaderDateSx: SxProps<Theme> = {
  fontFamily: FONT_FAMILY_UI,
  fontSize: "12px",
  fontWeight: 600,
  color: GLASS_COLORS.textSecondary,
  letterSpacing: "0.2px",
  flexShrink: 0,
  fontVariantNumeric: "tabular-nums",
};
