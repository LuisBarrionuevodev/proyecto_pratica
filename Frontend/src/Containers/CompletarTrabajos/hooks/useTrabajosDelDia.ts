import { useEffect, useRef, useState } from "react";

import {
  getCompletarTrabajoPendientes,
  type ICompletarTrabajoPendienteRow,
  type ICompletarTrabajoPendientesMeta,
} from "../../../api/completarTrabajoApi";

export type UseTrabajosDelDiaOptions = {
  page?: number;
  perPage?: number;
  /** Incrementar para forzar refetch manteniendo fecha/paginación. */
  refreshNonce?: number;
};

/**
 * Carga trabajos pendientes de completar para una fecha (API real, paginado).
 *
 * @param fecha - Día operativo de la ruta (YYYY-MM-DD), igual a `RutaTrabajo.fecha`; si vacío, no dispara carga.
 */
export function useTrabajosDelDia(fecha: string | null, options: UseTrabajosDelDiaOptions = {}) {
  const page = options.page ?? 1;
  const perPage = options.perPage ?? 20;
  const refreshNonce = options.refreshNonce ?? 0;

  const [rows, setRows] = useState<ICompletarTrabajoPendienteRow[]>([]);
  const [meta, setMeta] = useState<ICompletarTrabajoPendientesMeta | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const lastFechaRef = useRef<string | null>(null);

  useEffect(() => {
    if (!fecha) {
      setRows([]);
      setMeta(null);
      setError(null);
      setLoading(false);
      lastFechaRef.current = null;
      return;
    }

    if (lastFechaRef.current !== fecha) {
      lastFechaRef.current = fecha;
      setRows([]);
      setMeta(null);
    }

    let cancelled = false;
    setLoading(true);
    setError(null);

    void (async () => {
      try {
        const resp = await getCompletarTrabajoPendientes({ fecha, page, per_page: perPage });
        if (cancelled) return;
        setRows(resp.items);
        setMeta(resp.meta);
      } catch (err: unknown) {
        if (cancelled) return;
        const ax = err as { response?: { data?: { detail?: string; errors?: unknown } } };
        const detail = ax?.response?.data?.detail;
        setError(typeof detail === "string" ? detail : "No se pudieron cargar los trabajos del día.");
        setRows([]);
        setMeta(null);
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();

    return () => {
      cancelled = true;
    };
  }, [fecha, page, perPage, refreshNonce]);

  return { rows, meta, loading, error };
}
