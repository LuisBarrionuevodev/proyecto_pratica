import { useState, useCallback } from "react";
import type {
  IRelevamientoListItem,
  IRelevamientosListMeta,
  IRelevamientosListFilters,
} from "../../../api/relevamientosListApi";
import { getRelevamientosOperativosFiltered } from "../../../api/relevamientosListApi";

interface UseRelevamientosFiltradas {
  relevamientos: IRelevamientoListItem[];
  meta: IRelevamientosListMeta | null;
  loading: boolean;
  error: string | null;
  hasSearched: boolean;
  buscar: (filters: IRelevamientosListFilters) => Promise<void>;
}

export const useRelevamientosFiltradas = (): UseRelevamientosFiltradas => {
  const [relevamientos, setRelevamientos] = useState<IRelevamientoListItem[]>([]);
  const [meta, setMeta] = useState<IRelevamientosListMeta | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [hasSearched, setHasSearched] = useState(false);

  const buscar = useCallback(async (filters: IRelevamientosListFilters) => {
    setLoading(true);
    setError(null);
    setHasSearched(true);
    try {
      const response = await getRelevamientosOperativosFiltered(filters);
      setRelevamientos(response.items);
      setMeta(response.meta);
    } catch (err: any) {
      setError(err?.response?.data?.detail || "Error al cargar relevamientos");
      setRelevamientos([]);
      setMeta(null);
    } finally {
      setLoading(false);
    }
  }, []);

  return {
    relevamientos,
    meta,
    loading,
    error,
    hasSearched,
    buscar,
  };
};
