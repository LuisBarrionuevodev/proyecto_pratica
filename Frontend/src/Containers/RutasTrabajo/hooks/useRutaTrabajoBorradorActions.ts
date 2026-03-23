import { useCallback } from "react";

import {
  deleteRutaItem,
  moveRutaItem,
  patchRutaItemOrdenTrabajo,
  type IRutaItemMin,
} from "../../../api/rutasTrabajoApi";

export type UseRutaTrabajoBorradorActionsParams = {
  rutaId: number | null;
  setItems: React.Dispatch<React.SetStateAction<IRutaItemMin[]>>;
  setError: React.Dispatch<React.SetStateAction<string | null>>;
  loadPendientes: () => Promise<void>;
};

/**
 * Mutaciones de borrador (mover / quitar / OT) sin refetch del detail completo.
 * Actualiza solo `items` en estado local; quitar item dispara `loadPendientes` para la grilla de pendientes.
 */
export function useRutaTrabajoBorradorActions({
  rutaId,
  setItems,
  setError,
  loadPendientes,
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
        await loadPendientes();
      } catch (err: any) {
        setError(err?.response?.data?.detail || "No se pudo quitar el item");
      }
    },
    [rutaId, setItems, loadPendientes, setError]
  );

  const saveOtItem = useCallback(
    async (item: IRutaItemMin, numeroOt: string): Promise<boolean> => {
      if (!rutaId) return false;
      try {
        const resp = await patchRutaItemOrdenTrabajo(rutaId, item.id, {
          numero_orden_trabajo: numeroOt,
        });
        setItems((prev) => prev.map((it) => (it.id === resp.item.id ? resp.item : it)));
        return true;
      } catch (err: any) {
        setError(err?.response?.data?.detail || "No se pudo guardar la OT");
        return false;
      }
    },
    [rutaId, setItems, setError]
  );

  return { moveItem, deleteItem, saveOtItem };
}
