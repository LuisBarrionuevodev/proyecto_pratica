import type { SxProps, Theme } from "@mui/material";

import { formDialogContentStackSx } from "./formDialogStyles";
import { dashboardAnalyticsCardSx } from "./DashboardStyles";
import { GLASS_COLORS, glassDialogBackdropSx } from "./GlassStyles";

/** Radio y borde estándar de modales CRUD glass. */
export const CRUD_DIALOG_BORDER_RADIUS = "18px";

/** Texto del modal CRUD: blanco con opacidades controladas (nunca oscuro). */
export const CRUD_DIALOG_TEXT = {
  primary: "#ffffff",
  secondary: "rgba(255,255,255,0.86)",
  muted: "rgba(255,255,255,0.72)",
} as const;

/**
 * Azul oscuro del header CRUD — misma familia que `dashboardAnalyticsCardSx`
 * (Overview Operativo), no el primary brillante `#0166FF`.
 */
export const CRUD_DIALOG_HEADER_BLUE = dashboardAnalyticsCardSx.backgroundColor;

/** Fondo glass del paper del modal CRUD. */
export const CRUD_DIALOG_PAPER_BG = "rgba(12, 18, 32, 0.88)";

/**
 * Paper del modal CRUD: glass oscuro liviano + borde suave + radio 18px.
 * Componer sobre `AppDialog` vía `paperSx`.
 */
export const crudDialogPaperSx: SxProps<Theme> = {
  backgroundColor: CRUD_DIALOG_PAPER_BG,
  backdropFilter: "blur(14px)",
  WebkitBackdropFilter: "blur(14px)",
  borderRadius: CRUD_DIALOG_BORDER_RADIUS,
  border: `1px solid ${GLASS_COLORS.borderLight}`,
  boxShadow: "0 1px 2px rgba(0,0,0,0.24), 0 12px 40px rgba(0,0,0,0.42)",
  color: CRUD_DIALOG_TEXT.primary,
  maxHeight: "min(92vh, 920px)",
  display: "flex",
  flexDirection: "column",
  overflow: "hidden",
};

/** Backdrop reutilizable (alias explícito para CRUD). */
export const crudDialogBackdropSx = glassDialogBackdropSx;

/**
 * Header azul oscuro tipo cards de indicadores; texto blanco, compacto.
 * Aplicar en `DialogTitle` vía `titleSx` de `AppDialog`.
 */
export const crudDialogHeaderSx: SxProps<Theme> = {
  fontFamily: '"Tactic Sans", sans-serif',
  backgroundColor: CRUD_DIALOG_HEADER_BLUE,
  color: CRUD_DIALOG_TEXT.primary,
  borderBottom: `1px solid ${GLASS_COLORS.borderLight}`,
  py: 1.25,
  px: 2,
  boxShadow: "none",
};

/** Área scrolleable interna del contenido — sin panel gris pesado. */
export const crudDialogContentSx: SxProps<Theme> = {
  ...formDialogContentStackSx,
  flex: "1 1 auto",
  minHeight: 0,
  overflowY: "auto",
  maxHeight: { xs: "calc(100vh - 11rem)", sm: "min(72vh, 760px)" },
  px: 0,
  py: 0,
  backgroundColor: "transparent",
  color: CRUD_DIALOG_TEXT.primary,
  borderTop: "none",
  borderBottom: "none",
};

/** Pie sticky con acciones visibles — glass oscuro liviano. */
export const crudDialogActionsSx: SxProps<Theme> = {
  position: "sticky",
  bottom: 0,
  zIndex: 1,
  backgroundColor: "rgba(12, 18, 32, 0.78)",
  backdropFilter: "blur(10px)",
  WebkitBackdropFilter: "blur(10px)",
  borderTop: `1px solid ${GLASS_COLORS.borderLight}`,
  color: CRUD_DIALOG_TEXT.primary,
  px: 2,
  py: 1.25,
  display: "flex",
  flexDirection: "row",
  flexWrap: "nowrap",
  justifyContent: "flex-end",
  alignItems: "center",
  gap: 1.5,
  "& > *": {
    width: "auto",
    flex: "0 0 auto",
  },
};

/** Fila horizontal de botones dentro del footer CRUD (sin apilar). */
export const crudDialogActionsRowSx: SxProps<Theme> = {
  display: "flex",
  flexDirection: "row",
  flexWrap: "nowrap",
  justifyContent: "flex-end",
  alignItems: "center",
  gap: 1.5,
  width: "auto",
  maxWidth: "100%",
  minWidth: 0,
};

/** Scrollbar oculto en el modal CRUD (scroll sigue funcionando). */
export const crudDialogScrollbarSx: SxProps<Theme> = {
  scrollbarWidth: "none",
  msOverflowStyle: "none",
  "&::-webkit-scrollbar": {
    display: "none",
    width: 0,
    height: 0,
  },
};

/** Título pequeño de sección (overline). */
export const crudDialogSectionTitleSx: SxProps<Theme> = {
  fontFamily: '"Tactic Sans", sans-serif',
  fontWeight: 700,
  fontSize: "0.7rem",
  letterSpacing: "0.04em",
  textTransform: "uppercase",
  color: CRUD_DIALOG_TEXT.primary,
  mb: 1.25,
  display: "block",
  lineHeight: 1.35,
};

/** Sección plain: título + spacing + divisor sutil (default). */
export const crudDialogSectionPlainSx: SxProps<Theme> = {
  width: "100%",
  minWidth: 0,
  boxSizing: "border-box",
  pb: 2,
  mb: 0.5,
  color: CRUD_DIALOG_TEXT.primary,
  borderBottom: `1px solid ${GLASS_COLORS.borderLight}`,
  "&:last-of-type": {
    borderBottom: "none",
    pb: 0,
    mb: 0,
  },
};

/** Sección soft: contenedor apenas marcado (opt-in). */
export const crudDialogSectionSoftSx: SxProps<Theme> = {
  ...crudDialogSectionPlainSx,
  backgroundColor: "rgba(255, 255, 255, 0.028)",
  borderRadius: "10px",
  border: `1px solid ${GLASS_COLORS.borderLight}`,
  borderBottom: `1px solid ${GLASS_COLORS.borderLight}`,
  p: { xs: 1.5, sm: 1.75 },
  mb: 1,
  "&:last-of-type": {
    borderBottom: `1px solid ${GLASS_COLORS.borderLight}`,
    mb: 0,
  },
};

/** @deprecated Usar `crudDialogSectionPlainSx` o variante `soft` en `CrudDialogSection`. */
export const crudDialogSectionSx: SxProps<Theme> = crudDialogSectionSoftSx;

/** Grilla estándar de campos CRUD (2 columnas en sm+). */
export const crudFieldGridSx: SxProps<Theme> = {
  display: "grid",
  gridTemplateColumns: { xs: "1fr", sm: "repeat(2, 1fr)" },
  gap: 2,
  width: "100%",
};

/** Altura fija del control (shell readonly = input editable). */
export const CRUD_FIELD_INPUT_HEIGHT_PX = 40;

/** Reserva vertical del helper para no saltar layout entre vista/edición. */
export const CRUD_FIELD_HELPER_MIN_HEIGHT_PX = 20;

/** Label sobre el campo (vista y edición). */
export const crudFieldSlotLabelSx: SxProps<Theme> = {
  display: "block",
  fontFamily: '"Tactic Sans", sans-serif',
  fontSize: "0.8125rem",
  fontWeight: 500,
  color: CRUD_DIALOG_TEXT.primary,
  mb: 0.5,
  lineHeight: 1.4,
};

/** Shell readonly tipo input — mismo glass que inputs editables. */
export const crudReadonlyFieldShellSx: SxProps<Theme> = {
  height: CRUD_FIELD_INPUT_HEIGHT_PX,
  minHeight: CRUD_FIELD_INPUT_HEIGHT_PX,
  maxHeight: CRUD_FIELD_INPUT_HEIGHT_PX,
  display: "flex",
  alignItems: "center",
  px: 1.5,
  py: 0,
  borderRadius: "8px",
  border: "1px solid rgba(255,255,255,0.12)",
  backgroundColor: "rgba(255, 255, 255, 0.04)",
  boxSizing: "border-box",
  width: "100%",
};

/** Campo readonly completo (shell + valor) — alias conveniente. */
export const crudReadonlyFieldSx: SxProps<Theme> = {
  ...crudReadonlyFieldShellSx,
  color: CRUD_DIALOG_TEXT.primary,
};

/** Texto dentro del shell readonly. */
export const crudReadonlyFieldValueSx: SxProps<Theme> = {
  color: CRUD_DIALOG_TEXT.primary,
  lineHeight: 1.45,
  fontSize: "0.875rem",
  wordBreak: "break-word",
};

/** @deprecated Usar `crudFieldSlotLabelSx` + shell readonly. */
export const crudFieldLabelSx: SxProps<Theme> = crudFieldSlotLabelSx;

/** @deprecated Usar `crudReadonlyFieldValueSx` dentro del shell. */
export const crudFieldValueSx: SxProps<Theme> = crudReadonlyFieldValueSx;

/** Estilos de campos dentro del modal CRUD (labels, inputs, helpers en blanco). */
export const crudDialogFormFieldsSx: SxProps<Theme> = {
  color: CRUD_DIALOG_TEXT.primary,
  "& .MuiFormControl-root": {
    marginTop: 0,
    marginBottom: 0,
  },
  "& .MuiInputLabel-root": {
    color: CRUD_DIALOG_TEXT.primary,
    fontSize: "0.8125rem",
    fontWeight: 500,
    position: "static",
    transform: "none",
    mb: 0.5,
    lineHeight: 1.4,
  },
  "& .MuiInputLabel-root.Mui-focused": {
    color: CRUD_DIALOG_TEXT.primary,
  },
  "& .MuiInputLabel-shrink": {
    transform: "none",
  },
  "& .MuiOutlinedInput-root": {
    color: CRUD_DIALOG_TEXT.primary,
    backgroundColor: "rgba(255, 255, 255, 0.04) !important",
    height: CRUD_FIELD_INPUT_HEIGHT_PX,
    minHeight: CRUD_FIELD_INPUT_HEIGHT_PX,
    maxHeight: CRUD_FIELD_INPUT_HEIGHT_PX,
    boxSizing: "border-box",
  },
  "& .MuiOutlinedInput-notchedOutline": {
    borderColor: "rgba(255,255,255,0.12) !important",
  },
  "& .MuiOutlinedInput-root:hover .MuiOutlinedInput-notchedOutline": {
    borderColor: "rgba(255,255,255,0.18)",
  },
  "& .MuiOutlinedInput-input": {
    color: CRUD_DIALOG_TEXT.primary,
    fontSize: "0.875rem",
    py: 0,
    boxSizing: "border-box",
  },
  "& .MuiSelect-select": {
    color: CRUD_DIALOG_TEXT.primary,
    fontSize: "0.875rem",
    py: 0,
    display: "flex",
    alignItems: "center",
    minHeight: "unset",
  },
  "& .MuiFormHelperText-root": {
    color: CRUD_DIALOG_TEXT.secondary,
    minHeight: CRUD_FIELD_HELPER_MIN_HEIGHT_PX,
    marginTop: "4px",
    marginLeft: 0,
    marginRight: 0,
    lineHeight: 1.25,
  },
  "& .MuiFormHelperText-root.Mui-error": {
    color: "#ff8a80",
  },
  "& .MuiChip-label": {
    color: CRUD_DIALOG_TEXT.primary,
  },
};

/** Alias de estilos para controles editables glass dentro del modal CRUD. */
export const crudEditableFieldSx: SxProps<Theme> = crudDialogFormFieldsSx;

/** Chips integrados al header CRUD oscuro. */
export const crudDialogHeaderChipSx = {
  domain: {
    height: 22,
    fontWeight: 600,
    fontSize: "0.6875rem",
    borderColor: "rgba(255,255,255,0.28)",
    color: CRUD_DIALOG_TEXT.primary,
    backgroundColor: "rgba(255,255,255,0.06)",
  },
  mode: {
    height: 22,
    fontWeight: 600,
    fontSize: "0.6875rem",
    color: CRUD_DIALOG_TEXT.primary,
    backgroundColor: "rgba(255,255,255,0.08)",
    border: "1px solid rgba(255,255,255,0.14)",
  },
  status: {
    height: 22,
    fontWeight: 600,
    fontSize: "0.6875rem",
    borderColor: "rgba(255,255,255,0.28)",
    color: CRUD_DIALOG_TEXT.primary,
    backgroundColor: "transparent",
  },
} as const;
