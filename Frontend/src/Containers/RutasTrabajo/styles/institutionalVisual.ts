/**
 * Superficies de RutasTrabajo — estilo glass (GlassStyles / tokens DIGITALIZA).
 * Misma familia visual que sidebar, content shell y CardGlass.
 */
import type { SxProps, Theme } from "@mui/material";

import { glassCard, glassDivider, GLASS_COLORS } from "../../../styles/GlassStyles";

/** Paneles de planificación, mapa placeholder y columnas. */
export const rutasInstitutionalPanelPaperSx: SxProps<Theme> = {
  ...glassCard,
  p: 2,
  overflow: "hidden",
};

/** Columna flex interna: header/lista/footer sin desbordar (HOTFIX-UI-LAYOUT). */
export const planificacionPanelColumnSx: SxProps<Theme> = {
  display: "flex",
  flexDirection: "column",
  minHeight: 0,
  height: "100%",
  overflow: "hidden",
};

export const planificacionFixedSectionSx: SxProps<Theme> = {
  flexShrink: 0,
};

export const planificacionListViewportSx: SxProps<Theme> = {
  flex: "1 1 auto",
  minHeight: 0,
  overflowY: "auto",
  overflowX: "hidden",
};

/** Columna derecha planificación: Urgentes y Pool en slots flex independientes. */
export const planificacionRightColumnSx: SxProps<Theme> = {
  display: "flex",
  flexDirection: "column",
  gap: 2,
  minWidth: 0,
  minHeight: 0,
  height: "100%",
  overflow: "hidden",
};

/** Slot superior: Urgentes absorbe espacio restante sin empujar pool. */
export const planificacionUrgentesSlotSx: SxProps<Theme> = {
  ...planificacionPanelColumnSx,
  flex: "1 1 0",
};

/** Slot inferior: pool con tope fijo y scroll interno. */
export const planificacionPoolSlotSx: SxProps<Theme> = {
  ...planificacionPanelColumnSx,
  flex: "0 0 auto",
  maxHeight: "min(36vh, 240px)",
};

/** Bloque de resumen de ruta. */
export const rutasInstitutionalResumenPaperSx: SxProps<Theme> = {
  ...glassCard,
  p: 2.5,
  overflow: "hidden",
};

/** Tarjeta de grupo (borde izquierdo de acento). */
export const rutasInstitutionalGrupoPaperSx = (accentColor: string): SxProps<Theme> => ({
  ...glassCard,
  p: 1.5,
  borderLeft: `4px solid ${accentColor}`,
  overflow: "hidden",
});

/** Tarjeta anidada por ítem dentro de un grupo (más sutil). */
export const rutasInstitutionalItemPaperSx: SxProps<Theme> = {
  p: 1,
  backgroundColor: GLASS_COLORS.hoverBg,
  backdropFilter: "blur(12px)",
  WebkitBackdropFilter: "blur(12px)",
  border: `1px solid ${GLASS_COLORS.borderLight}`,
  borderRadius: "12px",
  overflow: "hidden",
};

export const rutasInstitutionalDividerSx: SxProps<Theme> = {
  ...glassDivider,
};

const TACTIC = '"Tactic Sans", sans-serif' as const;

/** Select / AppSelect en filtros de planificación (misma altura y fuente que TextField). */
export const planificacionFilterSelectSx: SxProps<Theme> = {
  "& .MuiOutlinedInput-root": {
    fontFamily: TACTIC,
    fontSize: "0.85rem",
    borderRadius: "10px",
    "& fieldset": { borderColor: GLASS_COLORS.borderLight },
    "&:hover fieldset": { borderColor: GLASS_COLORS.borderMedium },
    "&.Mui-focused fieldset": { borderColor: GLASS_COLORS.primary },
  },
  "& .MuiInputLabel-root": {
    fontFamily: TACTIC,
    fontSize: "0.85rem",
    color: GLASS_COLORS.textSecondary,
  },
  "& .MuiSelect-select": { fontSize: "0.85rem" },
};

/** Campo de búsqueda en paneles Planificación (alineado a glass / Digitaliza). */
export const planificacionTextFieldSx: SxProps<Theme> = {
  "& .MuiOutlinedInput-root": {
    fontFamily: '"Tactic Sans", sans-serif',
    backgroundColor: "rgba(255,255,255,0.04)",
    borderRadius: "10px",
    "& fieldset": { borderColor: GLASS_COLORS.borderLight },
    "&:hover fieldset": { borderColor: GLASS_COLORS.borderMedium },
    "&.Mui-focused fieldset": { borderColor: GLASS_COLORS.primary },
  },
  "& .MuiInputBase-input": { fontSize: "0.85rem" },
};

/** Título de panel en Planificación (pendientes, urgentes, pool) — misma jerarquía en todas las columnas. */
export const planificacionPanelTitleSx: SxProps<Theme> = {
  fontFamily: TACTIC,
  fontWeight: 700,
  fontSize: "0.9375rem",
  color: GLASS_COLORS.textPrimary,
  letterSpacing: "0.02em",
  lineHeight: 1.3,
};

/** Subtítulo / línea de contexto bajo el título (muted, legible en dark). */
export const planificacionPanelSubtitleSx: SxProps<Theme> = {
  fontFamily: TACTIC,
  fontSize: "0.75rem",
  color: GLASS_COLORS.textMuted,
  lineHeight: 1.45,
};

/** Línea de paginación / totales al pie de paneles con lista. */
export const planificacionPanelFooterMetaSx: SxProps<Theme> = {
  fontFamily: TACTIC,
  fontSize: "0.72rem",
  color: GLASS_COLORS.textMuted,
};

/**
 * Título del bloque "Resumen de ruta" y cabeceras de etapa en Asignación / Mapa final.
 * Alineado a jerarquía de Planificación (ligeramente mayor que título de panel de columna).
 */
export const rutasResumenTitleSx: SxProps<Theme> = {
  fontFamily: TACTIC,
  fontWeight: 700,
  fontSize: "1rem",
  color: GLASS_COLORS.textPrimary,
  letterSpacing: "0.02em",
  lineHeight: 1.3,
};

/** Alertas informativas/advertencia en Rutas (glass dark, sin depender de otros módulos). */
export const rutasInstitutionalAlertBaseSx: SxProps<Theme> = {
  fontFamily: TACTIC,
  borderRadius: "12px",
  backgroundColor: "rgba(255,255,255,0.06)",
  color: GLASS_COLORS.textPrimary,
  border: `1px solid ${GLASS_COLORS.borderMedium}`,
  "& .MuiAlert-message": { fontFamily: TACTIC },
};

/**
 * Scrollbar fina dark para listas internas (Planificación y similares en Rutas).
 * Alineada a tonos usados en tablas/mapa (#1E2127 / gris medio).
 */
export const rutasInstitutionalScrollSx: SxProps<Theme> = {
  scrollbarWidth: "thin",
  scrollbarColor: `#3a3d44 #1E2127`,
  "&::-webkit-scrollbar": { width: 8, height: 8 },
  "&::-webkit-scrollbar-track": {
    backgroundColor: "#1E2127",
    borderRadius: "4px",
  },
  "&::-webkit-scrollbar-thumb": {
    backgroundColor: "#3a3d44",
    borderRadius: "4px",
  },
  "&::-webkit-scrollbar-thumb:hover": {
    backgroundColor: "#4a4d54",
  },
};

/**
 * Botón contenido sólido neutro (sync, acciones secundarias “firmes” en Asignación).
 * Evita outlined/ghost cuando se busca UI sólida sin competir con primary blue.
 */
export const rutasAsignacionNeutralContainedButtonSx: SxProps<Theme> = {
  fontFamily: TACTIC,
  textTransform: "none",
  fontWeight: 600,
  fontSize: "0.8125rem",
  minHeight: 32,
  px: 1.5,
  py: 0.5,
  lineHeight: 1.2,
  color: GLASS_COLORS.textPrimary,
  backgroundColor: "rgba(255,255,255,0.12)",
  border: `1px solid ${GLASS_COLORS.borderMedium}`,
  boxShadow: "none",
  "&:hover": {
    backgroundColor: "rgba(255,255,255,0.18)",
    borderColor: GLASS_COLORS.borderActive,
  },
  "&.Mui-disabled": {
    backgroundColor: "rgba(255,255,255,0.06)",
    color: GLASS_COLORS.textMuted,
    borderColor: GLASS_COLORS.borderLight,
  },
};

/** Altura uniforme del slot de input en la fila de filtros de Asignación (selects + buscar). */
export const asignacionFiltroInputSlotSx: SxProps<Theme> = {
  "& .MuiOutlinedInput-root": {
    minHeight: 40,
    alignItems: "center",
    borderRadius: "10px",
  },
};

/** Altura de controles en la fila OT / Guardar / Mover (alineado a `AppButton` `md` y filtros). */
export const asignacionItemControlInputHeight = 40;

/** `TextField` (OT o select) en fila de ítem: alto uniforme y tipografía institucional. */
export const asignacionItemOtTextFieldRootSx: SxProps<Theme> = {
  "& .MuiOutlinedInput-root": {
    minHeight: asignacionItemControlInputHeight,
    alignItems: "center",
    borderRadius: "10px",
    fontFamily: TACTIC,
  },
  "& .MuiInputBase-input": { fontSize: "0.875rem" },
};

/** Botón neutro en fila de ítem (Mover): misma altura que `AppButton` `md`. */
export const asignacionItemRowNeutralButtonSx: SxProps<Theme> = {
  ...rutasAsignacionNeutralContainedButtonSx,
  minHeight: asignacionItemControlInputHeight,
  px: 2,
  fontSize: "0.875rem",
};
