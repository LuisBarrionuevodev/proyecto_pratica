import type { SxProps, Theme } from "@mui/material";

import { GLASS_COLORS, glassCard } from "./GlassStyles";

/**
 * Tokens compartidos para modales documentales (Recorrido, Notificación, Actuación).
 * Jerarquía por peso / tamaño / spacing — texto vía tokens semánticos (dark/light).
 */
export const DOC_MODAL_TEXT = GLASS_COLORS.textPrimary;

/** `spacing` del Stack entre intro y bloques / entre bloques sucesivos. */
export const DOC_MODAL_BLOCK_STACK_SPACING = 2;

export const docModalHeaderStackSx: SxProps<Theme> = {
  display: "flex",
  flexDirection: "column",
  alignItems: "flex-start",
  gap: 0.75,
  py: 0.25,
  minWidth: 0,
};

export const docModalChipSx: SxProps<Theme> = {
  height: 24,
  fontWeight: 600,
  borderColor: GLASS_COLORS.borderMedium,
  color: DOC_MODAL_TEXT,
  backgroundColor: GLASS_COLORS.hoverBg,
};

/** Texto auxiliar bajo bloques CRUD documentales (caption / hint). */
export const docModalCaptionSx: SxProps<Theme> = {
  color: GLASS_COLORS.textSecondary,
  lineHeight: 1.4,
  display: "block",
};

export const docModalTitleSx: SxProps<Theme> = {
  fontWeight: 700,
  lineHeight: 1.25,
  color: DOC_MODAL_TEXT,
  wordBreak: "break-word",
};

/** Subtítulo bajo el título: mismo color, menos peso que el H6. */
export const docModalSubtitleSx: SxProps<Theme> = {
  color: DOC_MODAL_TEXT,
  fontWeight: 500,
  lineHeight: 1.4,
  wordBreak: "break-word",
};

/** Referencia tipo Actuación #… / OT: discreta por tamaño y peso (`DOC_MODAL_TEXT` / tema). */
export const docModalReferenceSx: SxProps<Theme> = {
  color: DOC_MODAL_TEXT,
  fontWeight: 400,
  fontSize: "0.8125rem",
  lineHeight: 1.35,
};

/** Título de bloque (card): blanco, negrita; el acento cromático queda en el borde izquierdo (primary en el Box). */
export const docModalBlockOverlineSx: SxProps<Theme> = {
  color: DOC_MODAL_TEXT,
  letterSpacing: "0.06em",
  fontWeight: 700,
  fontSize: "0.8125rem",
  lineHeight: 1.35,
  textTransform: "uppercase",
  display: "block",
};

export const docModalBlockResumenSx: SxProps<Theme> = {
  display: "block",
  color: DOC_MODAL_TEXT,
  fontWeight: 400,
  fontSize: "0.8125rem",
  lineHeight: 1.45,
  mb: 1.25,
  mt: 0.25,
};

export const docModalFilaEtiquetaSx: SxProps<Theme> = {
  color: DOC_MODAL_TEXT,
  fontWeight: 600,
  minWidth: { sm: 160 },
  flex: { xs: "1 1 100%", sm: "0 1 38%" },
};

export const docModalFilaValorSx: SxProps<Theme> = {
  color: DOC_MODAL_TEXT,
  fontWeight: 500,
  textAlign: { xs: "left", sm: "right" },
  flex: { xs: "1 1 100%", sm: "1 1 50%" },
  wordBreak: "break-word",
};

export const docModalIntroParagraphSx: SxProps<Theme> = {
  color: DOC_MODAL_TEXT,
  fontWeight: 400,
  fontSize: "0.875rem",
  lineHeight: 1.5,
};

export const docModalEmptyStateSx: SxProps<Theme> = {
  color: DOC_MODAL_TEXT,
  fontStyle: "italic",
  fontWeight: 400,
  fontSize: "0.875rem",
  lineHeight: 1.45,
};

/** Subtítulos dentro de un bloque (p. ej. etapas administrativas). */
export const docModalSubheadingInCardSx: SxProps<Theme> = {
  display: "block",
  color: DOC_MODAL_TEXT,
  fontWeight: 600,
  fontSize: "0.75rem",
  letterSpacing: "0.04em",
  textTransform: "uppercase",
};

export const docModalFooterRowSx: SxProps<Theme> = {
  display: "flex",
  flexWrap: "wrap",
  alignItems: "center",
  justifyContent: "space-between",
  gap: 1.5,
  width: "100%",
  minHeight: 44,
  boxSizing: "border-box",
};

export const docModalFooterHintSx: SxProps<Theme> = {
  color: DOC_MODAL_TEXT,
  fontWeight: 400,
  fontSize: "0.8125rem",
  lineHeight: 1.35,
  flex: "1 1 220px",
  minWidth: 0,
};

export const docModalFooterButtonsSx: SxProps<Theme> = {
  display: "flex",
  gap: 1,
  flexWrap: "wrap",
  justifyContent: "flex-end",
  alignItems: "center",
};

/** Caja documental estándar: glass + borde de acento. */
export function docModalGlassCardShellSx(borderAccent: string): SxProps<Theme> {
  return {
    ...glassCard,
    p: 2,
    mb: 0,
    borderRadius: "12px",
    borderLeft: `3px solid ${borderAccent}`,
  };
}

/**
 * Card documental para el modal de Actuaciones (bloques dentro del `DialogContent` scrollable).
 * Conserva fondo, borde, sombra e acento lateral; **omite `backdrop-filter`** para reducir
 * recomposición de capas al hacer scroll (ver PR rendimiento / compositing).
 */
export function docModalActuacionScrollCardShellSx(borderAccent: string): SxProps<Theme> {
  return {
    backgroundColor: GLASS_COLORS.cardBg,
    border: `1px solid ${GLASS_COLORS.borderMedium}`,
    boxShadow: "0 2px 14px rgba(0, 0, 0, 0.24)",
    borderRadius: "12px",
    p: 2,
    mb: 0,
    borderLeft: `3px solid ${borderAccent}`,
  };
}

/** Alertas dentro de `AppDialog` glass: legibles en claro y oscuro. */
export const documentalGlassAlertSx: SxProps<Theme> = (theme) => ({
  bgcolor:
    theme.palette.mode === "dark" ? "rgba(0,0,0,0.28)" : theme.palette.action.hover,
  color: theme.palette.text.primary,
  border: `1px solid ${theme.palette.divider}`,
  "& .MuiAlert-message": { color: theme.palette.text.primary },
  "& .MuiAlert-icon": {
    color: theme.palette.mode === "dark" ? "rgba(255,255,255,0.9)" : theme.palette.warning.dark,
  },
});

/** Card seleccionable de oficio en Comprobación (lista tribunal). */
export function comprobacionOficioOperativoCardSx(selected: boolean): SxProps<Theme> {
  return (theme) => ({
    cursor: "pointer",
    borderRadius: 1.5,
    px: 1.5,
    py: 1.25,
    border: selected
      ? `1px solid ${theme.palette.primary.main}`
      : `1px solid ${theme.palette.divider}`,
    backgroundColor: selected ? theme.palette.action.selected : theme.palette.background.paper,
    color: theme.palette.text.primary,
    transition: "border-color 0.15s, background-color 0.15s",
    "&:hover": {
      borderColor: theme.palette.primary.light,
      backgroundColor: theme.palette.action.hover,
    },
    "& .MuiTypography-root": {
      color: theme.palette.text.primary,
    },
    "& .MuiChip-root": {
      borderColor: theme.palette.divider,
      color: theme.palette.text.primary,
    },
    "& .MuiChip-colorWarning": {
      borderColor: theme.palette.warning.main,
      color: theme.palette.warning.dark,
      backgroundColor:
        theme.palette.mode === "dark" ? "rgba(234, 179, 8, 0.12)" : theme.palette.warning.light,
    },
  });
}

/** Advertencia inline/toast: acento amarillo institucional sobre fondo glass. */
export const documentalGlassWarningAlertSx: SxProps<Theme> = {
  bgcolor: "rgba(234, 179, 8, 0.14)",
  border: "1px solid rgba(234, 179, 8, 0.45)",
  "& .MuiAlert-message": { color: DOC_MODAL_TEXT },
  "& .MuiAlert-icon": { color: "rgba(250, 204, 21, 0.95)" },
};

/** Éxito toast: acento azul primario (no verde MUI por defecto). */
export const documentalGlassSuccessAlertSx: SxProps<Theme> = {
  bgcolor: "rgba(1, 102, 255, 0.16)",
  border: "1px solid rgba(1, 102, 255, 0.45)",
  "& .MuiAlert-message": { color: DOC_MODAL_TEXT },
  "& .MuiAlert-icon": { color: "rgba(96, 165, 250, 0.98)" },
};

/** Error toast: acento rojo sobre fondo glass. */
export const documentalGlassErrorAlertSx: SxProps<Theme> = {
  bgcolor: "rgba(239, 68, 68, 0.14)",
  border: "1px solid rgba(239, 68, 68, 0.45)",
  "& .MuiAlert-message": { color: DOC_MODAL_TEXT },
  "& .MuiAlert-icon": { color: "rgba(248, 113, 113, 0.98)" },
};
