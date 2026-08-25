import { Stack } from "@mui/material";

import type { IRutaGrupoMin, IRutaTrabajo } from "../../../api/rutasTrabajoApi";
import { RutasOperativaChip } from "./RutasOperativaChip";

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
      spacing={0.75}
      sx={{ mb: 1.25 }}
      data-testid="asignacion-grupos-resumen"
    >
      <RutasOperativaChip label={`Grupos: ${grupos.length}`} />
      <RutasOperativaChip label={`Items: ${itemsCount}`} />
      <RutasOperativaChip label={`Inspectores: ${totalInspectores}`} />
      <RutasOperativaChip
        label={`Observaciones: ${observaciones.length > 28 ? `${observaciones.slice(0, 28)}…` : observaciones}`}
        sx={{ maxWidth: "100%" }}
      />
    </Stack>
  );
}
