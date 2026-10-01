import { useCallback, useState } from "react";
import { Stack, Typography } from "@mui/material";

import { GLASS_COLORS } from "../../../styles/GlassStyles";
import { AppButton } from "../../../ui";
import { planificacionPanelFooterMetaSx } from "../styles/institutionalVisual";
import { RutasOperativaChip } from "./RutasOperativaChip";

export type AsignacionPoolSelectionActionsProps = {
  totalEnPool: number;
  rowsVisiblesCount: number;
  selectedIds: number[];
  assignedIniciadorIds: Set<number>;
  onAssignSelected: () => void;
  poolIdByIniciadorId?: Record<number, number>;
  onEliminarDelPool?: (poolIds: number[]) => void | Promise<void>;
};

/**
 * Barra de acciones sobre selección del pool (Asignación): mismos handlers en MRT y listado móvil.
 */
export function AsignacionPoolSelectionActions({
  totalEnPool,
  rowsVisiblesCount,
  selectedIds,
  assignedIniciadorIds,
  onAssignSelected,
  poolIdByIniciadorId,
  onEliminarDelPool,
}: AsignacionPoolSelectionActionsProps) {
  const nSel = selectedIds.length;
  const puedeEliminar =
    nSel > 0 &&
    Boolean(onEliminarDelPool && poolIdByIniciadorId) &&
    selectedIds.every((id) => !assignedIniciadorIds.has(id) && poolIdByIniciadorId![id] != null);

  const [eliminandoPool, setEliminandoPool] = useState(false);

  const handleEliminarDelPool = useCallback(async () => {
    if (!onEliminarDelPool || !poolIdByIniciadorId) return;
    const poolIds = selectedIds
      .map((id) => poolIdByIniciadorId[id])
      .filter((pid): pid is number => pid != null);
    if (!poolIds.length) return;
    setEliminandoPool(true);
    try {
      await onEliminarDelPool(poolIds);
    } finally {
      setEliminandoPool(false);
    }
  }, [onEliminarDelPool, poolIdByIniciadorId, selectedIds]);

  return (
    <Stack
      direction={{ xs: "column", sm: "row" }}
      spacing={1}
      alignItems={{ xs: "stretch", sm: "center" }}
      flexWrap="wrap"
      useFlexGap
      data-testid="asignacion-pool-selection-actions"
      sx={{ width: "100%", minWidth: 0, pl: { sm: 0.5 } }}
    >
      <Typography
        sx={{
          ...planificacionPanelFooterMetaSx,
          fontSize: "0.8125rem",
          color: GLASS_COLORS.textSecondary,
          flex: { sm: "1 1 auto" },
          minWidth: 0,
        }}
      >
        {totalEnPool} en pool · {rowsVisiblesCount} visibles
      </Typography>
      <RutasOperativaChip label={`${nSel} seleccionados`} color="primary" sx={{ alignSelf: { xs: "flex-start", sm: "center" } }} />
      {onEliminarDelPool ? (
        <AppButton
          dsVariant="danger"
          dsSize="sm"
          disabled={!puedeEliminar || eliminandoPool}
          onClick={() => void handleEliminarDelPool()}
          data-testid="asignacion-eliminar-del-pool"
          sx={{ width: { xs: "100%", sm: "auto" } }}
        >
          {eliminandoPool ? "Eliminando…" : "Eliminar del pool"}
        </AppButton>
      ) : null}
      <AppButton
        dsVariant="primary"
        dsSize="sm"
        onClick={onAssignSelected}
        disabled={nSel === 0}
        sx={{ width: { xs: "100%", sm: "auto" } }}
      >
        Asignar seleccionados
      </AppButton>
    </Stack>
  );
}
