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
