import { useCallback } from "react";

import {
  clearRutaItemOrdenTrabajo,
  deleteRutaItem,
  moveRutaItem,
  patchRutaItemOrdenTrabajo,
  type IRutaItemMin,
} from "../../../api/rutasTrabajoApi";
import { mensajeErrorGuardarOtPatch } from "../utils/rutaOtAsignacionMessages";

/** Resultado de guardar OT: conflicto de negocio (p. ej. 409) vs error global ya volcado a `setError`. */
export type GuardarOtItemResult =
  | { ok: true }
  | { ok: false; scope: "inline"; message: string; otConsumida?: boolean }
  | { ok: false; scope: "global" };

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

  const saveOtItem = useCallback(
    async (item: IRutaItemMin, numeroOt: string): Promise<GuardarOtItemResult> => {
      if (!rutaId) return { ok: false, scope: "global" };
      try {
        const resp = await patchRutaItemOrdenTrabajo(rutaId, item.id, {
          numero_orden_trabajo: numeroOt,
        });
        setItems((prev) => prev.map((it) => (it.id === resp.item.id ? resp.item : it)));
        return { ok: true };
      } catch (err: unknown) {
        const ax = err as {
          response?: { status?: number; data?: { detail?: unknown; debug?: { validator?: string } } };
        };
        const status = ax?.response?.status;
        const data = ax?.response?.data;
        const parsed = mensajeErrorGuardarOtPatch(data?.detail, data?.debug ?? null);
        if (status === 409) {
          return {
            ok: false,
            scope: "inline",
            message: parsed.message,
            otConsumida: parsed.otConsumida,
          };
        }
        setError(parsed.message);
        return { ok: false, scope: "global" };
      }
    },
    [rutaId, setItems, setError]
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

  return { moveItem, deleteItem, saveOtItem, clearOrdenTrabajo };
}
