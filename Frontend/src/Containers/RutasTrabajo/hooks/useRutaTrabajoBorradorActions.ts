import { useCallback } from "react";

import {
  clearRutaItemOrdenTrabajo,
  deleteRutaItem,
  moveRutaItem,
  type IRutaItemMin,
} from "../../../api/rutasTrabajoApi";

export type UseRutaTrabajoBorradorActionsParams = {
  rutaId: number | null;
  setItems: React.Dispatch<React.SetStateAction<IRutaItemMin[]>>;
  setError: React.Dispatch<React.SetStateAction<string | null>>;
  loadPendientes: () => Promise<void>;
  /** Tras quitar ítem (p. ej. refrescar pool del día y detalle de borrador). */
  onAfterDeleteItem?: () => Promise<void>;
};

/**
 * Mutaciones de borrador (mover / quitar / OT) sin refetch del detail completo.
 * Actualiza solo `items` en estado local; quitar item dispara `loadPendientes` (no-op en Asignación basada en pool).
 */
export function useRutaTrabajoBorradorActions({
  rutaId,
  setItems,
  setError,
  loadPendientes,
  onAfterDeleteItem,
}: UseRutaTrabajoBorradorActionsParams) {
  const moveItem = useCallback(
    async (item: IRutaItemMin, targetGrupoId: number) => {
      if (!rutaId) return;
      try {
        const resp = await moveRutaItem(rutaId, item.id, { target_grupo_id: targetGrupoId });
        setItems((prev) => prev.map((it) => (it.id === item.id ? resp.item : it)));
      } catch (err: any) {
        setError(err?.response?.data?.detail || "No se pudo mover el item");
      }
    },
    [rutaId, setItems, setError]
  );

  const deleteItem = useCallback(
    async (item: IRutaItemMin) => {
      if (!rutaId) return;
      try {
        await deleteRutaItem(rutaId, item.id);
        setItems((prev) => prev.filter((it) => it.id !== item.id));
        await Promise.all([
          loadPendientes(),
          ...(onAfterDeleteItem ? [onAfterDeleteItem()] : []),
        ]);
      } catch (err: any) {
        setError(err?.response?.data?.detail || "No se pudo quitar el item");
      }
    },
    [rutaId, setItems, loadPendientes, onAfterDeleteItem, setError]
  );

  const clearOrdenTrabajo = useCallback(
    async (item: IRutaItemMin): Promise<boolean> => {
      if (!rutaId) return false;
      try {
        const resp = await clearRutaItemOrdenTrabajo(rutaId, item.id);
        setItems((prev) => prev.map((it) => (it.id === resp.item.id ? resp.item : it)));
        return true;
      } catch (err: unknown) {
        const ax = err as { response?: { data?: { detail?: string } } };
        setError(ax?.response?.data?.detail || "No se pudo quitar la orden de trabajo del ítem");
        return false;
      }
    },
    [rutaId, setItems, setError]
  );

  return { moveItem, deleteItem, clearOrdenTrabajo };
}
