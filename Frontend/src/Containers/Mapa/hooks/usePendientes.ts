import { useCallback, useEffect, useState } from "react";
import { getMapPendientes, type PendingItem } from "../../../api/mapApi";

export type PendientesKind = "norm" | "map";

export interface PendientesFilters {
  desde?: string | null;
  hasta?: string | null;
  scope?: string | null;
}

export const usePendientes = (kind: PendientesKind, filters: PendientesFilters) => {
  const [items, setItems] = useState<PendingItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchItems = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const params: Record<string, any> = {
        kind,
        desde: filters.desde || undefined,
        hasta: filters.hasta || undefined,
        scope: filters.scope || undefined,
      };
      const data = await getMapPendientes(params);
      setItems(data);
    } catch (err: any) {
      setError(err?.response?.data?.detail || "Error al cargar pendientes");
      setItems([]);
    } finally {
      setLoading(false);
    }
  }, [kind, filters.desde, filters.hasta, filters.scope]);

  useEffect(() => {
    fetchItems();
  }, [fetchItems]);

  return { items, loading, error, refetch: fetchItems };
};
