/**
 * Superficies de RutasTrabajo — estilo glass (GlassStyles / tokens DIGITALIZA).
 * Misma familia visual que sidebar, content shell y CardGlass.
 */
import type { SxProps, Theme } from "@mui/material";

import { glassCard, glassDivider, glassTabsHeaderPanelSx, GLASS_COLORS } from "../../../styles/GlassStyles";

/** Cabecera principal (tabs, descripción) — mismo glass base que Mapa; padding ligeramente mayor. */
export const rutasInstitutionalHeaderPaperSx: SxProps<Theme> = {
  ...glassTabsHeaderPanelSx,
  p: 2.2,
};

/** Paneles de planificación, mapa placeholder y columnas. */
export const rutasInstitutionalPanelPaperSx: SxProps<Theme> = {
  ...glassCard,
  p: 2,
  overflow: "hidden",
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

const TACTIC = '"Tactic Sans", sans-serif' as const;

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
