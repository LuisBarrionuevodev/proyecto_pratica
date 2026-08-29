import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import type { IRutaIniciadorPendienteRow } from "../../../api/rutasTrabajoApi";
import { createRutaPoolDia, deleteRutaPoolDia, type IRutaPoolDiaRow } from "../../../api/rutaPoolDiaApi";
import { parseApiError } from "../../../utils/parseApiError";
import { buildPoolControlMaps } from "../utils/poolDiaDisplay";
import { prunePoolItemsByIds } from "../utils/poolAssignSync";
import { fetchRutaPoolDiaEnPoolAll } from "../utils/poolEnPoolList";

export type UseRutaPoolDiaBackendParams = {
  fecha: string | null | undefined;
  rutaTrabajoId?: number | null;
  onError?: (message: string) => void;
};

export type RefreshPoolOptions = {
  /** Evita spinner en refrescos de fondo (p. ej. tras quitar ítem de grupo). */
  silent?: boolean;
};

export type RutaPoolDiaBackendControl = {
  poolItems: IRutaPoolDiaRow[];
  poolIniciadorIds: number[];
  poolRowsById: Record<number, IRutaIniciadorPendienteRow>;
  poolIdByIniciadorId: Record<number, number>;
  loading: boolean;
  agregandoIniciadorIds: ReadonlySet<number>;
  refreshPool: (fechaOverride?: string | null, opts?: RefreshPoolOptions) => Promise<void>;
  /** Quita filas del snapshot local por pool_id (p. ej. tras agregar-desde-pool). */
  prunePoolEntriesByIds: (poolIds: readonly number[]) => void;
  agregarAlPool: (row: IRutaIniciadorPendienteRow, fecha?: string) => Promise<void>;
  quitarDelPool: (poolId: number) => Promise<void>;
};

/** Fecha efectiva para GET /ruta-pool-dia (override explícito o fecha operativa del hook). */
export function resolvePoolFechaConsulta(
  fechaOverride: string | null | undefined,
  fechaOperativa: string | null
): string | null {
  const f = (fechaOverride ?? fechaOperativa)?.trim();
  return f || null;
}

/**
 * Pool del día persistente (GET /ruta-pool-dia). Reemplaza estado in-memory local.
 */
export function useRutaPoolDiaBackend({
  fecha,
  rutaTrabajoId,
  onError,
}: UseRutaPoolDiaBackendParams): RutaPoolDiaBackendControl {
  const [poolItems, setPoolItems] = useState<IRutaPoolDiaRow[]>([]);
  const [loading, setLoading] = useState(false);
  const [agregandoIniciadorIds, setAgregandoIniciadorIds] = useState<Set<number>>(() => new Set());
  const agregandoRef = useRef<Set<number>>(new Set());
  const refreshPoolReqSeq = useRef(0);

  const fechaOperativa = fecha?.trim() || null;
  const rutaIdOperativa =
    rutaTrabajoId != null && Number.isFinite(Number(rutaTrabajoId)) ? Number(rutaTrabajoId) : null;

  const prunePoolEntriesByIds = useCallback((poolIds: readonly number[]) => {
    if (poolIds.length === 0) return;
    setPoolItems((prev) => prunePoolItemsByIds(prev, poolIds));
  }, []);

  const refreshPool = useCallback(
    async (fechaOverride?: string | null, opts?: RefreshPoolOptions) => {
      const f = resolvePoolFechaConsulta(fechaOverride, fechaOperativa);
      if (!f) {
        refreshPoolReqSeq.current += 1;
        setPoolItems([]);
        return;
      }
      const seq = ++refreshPoolReqSeq.current;
      if (!opts?.silent) setLoading(true);
      try {
        const items = await fetchRutaPoolDiaEnPoolAll({
          fecha: f,
          estado: "EN_POOL",
          ...(rutaIdOperativa != null ? { ruta_trabajo_id: rutaIdOperativa } : {}),
        });
        if (seq !== refreshPoolReqSeq.current) return;
        setPoolItems(items);
      } catch (err) {
        if (seq !== refreshPoolReqSeq.current) return;
        onError?.(parseApiError(err, "No se pudo cargar el pool del día.").message);
        setPoolItems([]);
      } finally {
        if (seq === refreshPoolReqSeq.current && !opts?.silent) {
          setLoading(false);
        }
      }
    },
    [fechaOperativa, rutaIdOperativa, onError]
  );

  useEffect(() => {
    void refreshPool();
  }, [refreshPool]);

  const { poolIniciadorIds, poolRowsById, poolIdByIniciadorId } = useMemo(
    () => buildPoolControlMaps(poolItems),
    [poolItems]
  );

  const agregarAlPool = useCallback(
    async (row: IRutaIniciadorPendienteRow, fechaOverride?: string) => {
      const f = (fechaOverride ?? fechaOperativa)?.trim();
      if (!f) {
        onError?.("No hay fecha operativa para agregar al pool.");
        return;
      }
      if (agregandoRef.current.has(row.id)) {
        return;
      }
      agregandoRef.current.add(row.id);
      setAgregandoIniciadorIds(new Set(agregandoRef.current));
      try {
        await createRutaPoolDia({
          origen_tipo: "INICIADOR",
          iniciador_ruta_id: row.id,
          fecha: f,
          ...(rutaIdOperativa != null ? { ruta_trabajo_id: rutaIdOperativa } : {}),
        });
        await refreshPool(f, { silent: true });
      } catch (err) {
        onError?.(parseApiError(err, "No se pudo agregar al pool del día.").message);
        throw err;
      } finally {
        agregandoRef.current.delete(row.id);
        setAgregandoIniciadorIds(new Set(agregandoRef.current));
      }
    },
    [fechaOperativa, rutaIdOperativa, onError, refreshPool]
  );

  const quitarDelPool = useCallback(
    async (poolId: number) => {
      try {
        await deleteRutaPoolDia(poolId);
        await refreshPool(undefined, { silent: true });
      } catch (err) {
        onError?.(parseApiError(err, "No se pudo quitar del pool.").message);
        throw err;
      }
    },
    [onError, refreshPool]
  );

  return {
    poolItems,
    poolIniciadorIds,
    poolRowsById,
    poolIdByIniciadorId,
    loading,
    agregandoIniciadorIds,
    refreshPool,
    prunePoolEntriesByIds,
    agregarAlPool,
    quitarDelPool,
  };
}
