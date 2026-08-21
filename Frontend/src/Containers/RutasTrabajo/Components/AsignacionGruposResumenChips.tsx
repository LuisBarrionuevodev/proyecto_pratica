import { Chip, Stack } from "@mui/material";

import type { IRutaGrupoMin, IRutaTrabajo } from "../../../api/rutasTrabajoApi";
import { GLASS_COLORS } from "../../../styles/GlassStyles";

const tactic = '"Tactic Sans", sans-serif' as const;

const chipSx = {
  height: 24,
  fontFamily: tactic,
  fontSize: "0.6875rem",
  fontWeight: 600,
  borderColor: GLASS_COLORS.borderMedium,
  color: GLASS_COLORS.textSecondary,
  backgroundColor: "rgba(255,255,255,0.04)",
} as const;

export type AsignacionGruposResumenChipsProps = {
  ruta: IRutaTrabajo;
  grupos: IRutaGrupoMin[];
  itemsCount: number;
};

/**
 * Resumen compacto dentro del panel Grupos (Asignación).
 */
export function AsignacionGruposResumenChips({ ruta, grupos, itemsCount }: AsignacionGruposResumenChipsProps) {
  const totalInspectores = grupos.reduce((acc, g) => acc + g.inspectores.length, 0);
  const observaciones = ruta.observaciones?.trim() || "—";

  return (
    <Stack
      direction="row"
      flexWrap="wrap"
      useFlexGap
      spacing={0.5}
      sx={{ mb: 1.25 }}
      data-testid="asignacion-grupos-resumen"
    >
      <Chip size="small" variant="outlined" label={`Grupos: ${grupos.length}`} sx={chipSx} />
      <Chip size="small" variant="outlined" label={`Items: ${itemsCount}`} sx={chipSx} />
      <Chip size="small" variant="outlined" label={`Inspectores: ${totalInspectores}`} sx={chipSx} />
      <Chip
        size="small"
        variant="outlined"
        label={`Observaciones: ${observaciones.length > 28 ? `${observaciones.slice(0, 28)}…` : observaciones}`}
        sx={{ ...chipSx, maxWidth: "100%" }}
      />
    </Stack>
  );
}
