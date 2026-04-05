import { useCallback, useEffect, useState } from "react";
import type {
  IRelevamientoListItem,
  IRelevamientosListFilters,
  IRelevamientosListMeta,
} from "../../../api/relevamientosListApi";
import {
  getRelevamientosOperativosFiltered,
  getRelevamientosRealizadosActuacionCompletadaFiltered,
} from "../../../api/relevamientosListApi";

export type RelevamientosBandejaSlice = "pendientes" | "realizados";

interface UseRelevamientosBandeja {
  relevamientos: IRelevamientoListItem[];
  meta: IRelevamientosListMeta | null;
  loading: boolean;
  error: string | null;
  hasSearched: boolean;
  buscar: (filters: IRelevamientosListFilters) => Promise<void>;
}

/**
 * Pendientes: gestion-operativa (iniciador RELEVAMIENTO pendiente).
 * Realizados: GET /relevamientos/realizados (iniciador RELEVAMIENTO CUMPLIDO con actuación).
 */
export const useRelevamientosBandeja = (slice: RelevamientosBandejaSlice): UseRelevamientosBandeja => {
  const [relevamientos, setRelevamientos] = useState<IRelevamientoListItem[]>([]);
  const [meta, setMeta] = useState<IRelevamientosListMeta | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [hasSearched, setHasSearched] = useState(false);

  const buscar = useCallback(
    async (filters: IRelevamientosListFilters) => {
      setLoading(true);
      setError(null);
      setHasSearched(true);
      try {
        const response =
          slice === "pendientes"
            ? await getRelevamientosOperativosFiltered(filters)
            : await getRelevamientosRealizadosActuacionCompletadaFiltered(filters);
        setRelevamientos(response.items);
        setMeta(response.meta);
      } catch (err: any) {
        setError(err?.response?.data?.detail || "Error al cargar relevamientos");
        setRelevamientos([]);
        setMeta(null);
      } finally {
        setLoading(false);
      }
    },
    [slice]
  );

  /** Al cambiar de pestaña: sin tabla hasta que el usuario pulse Filtrar. */
  useEffect(() => {
    setHasSearched(false);
    setRelevamientos([]);
    setMeta(null);
    setError(null);
  }, [slice]);

  return {
    relevamientos,
    meta,
    loading,
    error,
    hasSearched,
    buscar,
  };
};
