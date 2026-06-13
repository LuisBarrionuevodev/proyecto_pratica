import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { getMapPendientes } from "../../../api/mapApi";
import type { DomicilioPendienteItem, DomiciliosFilters, DomiciliosTab } from "../types";

export type UseDomiciliosPendientesOptions = {
  /**
   * Si es false, no se consulta la API al montar ni al cambiar filtros.
   */
  enabled?: boolean;
};

type TabKind = "norm" | "map";

type TabCacheSlot = {
  key: string;
  items: DomicilioPendienteItem[];
};

function filtersToCacheKey(filters: DomiciliosFilters): string {
  return JSON.stringify({
    desde: filters.desde ?? "",
    hasta: filters.hasta ?? "",
    scope: filters.scope ?? "",
  });
}

function tabToKind(activeTab: DomiciliosTab): TabKind {
  return activeTab === "nomenclatura" ? "norm" : "map";
}

/**
 * Carga pendientes de domicilio por pestaña activa (STAB-10) con cache por pestaña+filtros (STAB-10b).
 */
export const useDomiciliosPendientes = (
  filters: DomiciliosFilters,
  activeTab: DomiciliosTab,
  options?: UseDomiciliosPendientesOptions
) => {
  const enabled = options?.enabled ?? true;

  const [nomenclaturaItems, setNomenclaturaItems] = useState<DomicilioPendienteItem[]>([]);
  const [geolocalizacionItems, setGeolocalizacionItems] = useState<DomicilioPendienteItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const tabCacheRef = useRef<Partial<Record<TabKind, TabCacheSlot>>>({});

  const filtersCacheKey = useMemo(() => filtersToCacheKey(filters), [filters]);

  const baseParams = useCallback(
    () => ({
      desde: filters.desde || undefined,
      hasta: filters.hasta || undefined,
      scope: filters.scope || undefined,
    }),
    [filters.desde, filters.hasta, filters.scope]
  );

  const invalidateCache = useCallback(() => {
    tabCacheRef.current = {};
  }, []);

  const applyItems = useCallback((kind: TabKind, items: DomicilioPendienteItem[]) => {
    if (kind === "norm") {
      setNomenclaturaItems(items);
    } else {
      setGeolocalizacionItems(items);
    }
  }, []);

  const fetchKind = useCallback(
    async (kind: TabKind, cacheKey: string) => {
      const items = await getMapPendientes({ ...baseParams(), kind });
      tabCacheRef.current[kind] = { key: cacheKey, items };
      applyItems(kind, items);
    },
    [applyItems, baseParams]
  );

  const refetch = useCallback(async () => {
    invalidateCache();
    setLoading(true);
    setError(null);
    try {
      const kind = tabToKind(activeTab);
      await fetchKind(kind, filtersCacheKey);
    } catch (err: unknown) {
      const detail = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
      setError(typeof detail === "string" ? detail : "Error al cargar domicilios pendientes");
      if (activeTab === "nomenclatura") {
        setNomenclaturaItems([]);
      } else {
        setGeolocalizacionItems([]);
      }
    } finally {
      setLoading(false);
    }
  }, [activeTab, fetchKind, filtersCacheKey, invalidateCache]);

  useEffect(() => {
    if (!enabled) {
      setNomenclaturaItems([]);
      setGeolocalizacionItems([]);
      setError(null);
      setLoading(false);
      tabCacheRef.current = {};
      return;
    }

    const kind = tabToKind(activeTab);
    const cached = tabCacheRef.current[kind];
    if (cached?.key === filtersCacheKey) {
      applyItems(kind, cached.items);
      setError(null);
      setLoading(false);
      return;
    }

    let cancel = false;
    const run = async () => {
      setLoading(true);
      setError(null);
      try {
        const items = await getMapPendientes({ ...baseParams(), kind });
        if (cancel) return;
        tabCacheRef.current[kind] = { key: filtersCacheKey, items };
        applyItems(kind, items);
      } catch (err: unknown) {
        if (cancel) return;
        const detail = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
        setError(typeof detail === "string" ? detail : "Error al cargar domicilios pendientes");
        if (activeTab === "nomenclatura") {
          setNomenclaturaItems([]);
        } else {
          setGeolocalizacionItems([]);
        }
      } finally {
        if (!cancel) setLoading(false);
      }
    };
    void run();
    return () => {
      cancel = true;
    };
  }, [enabled, activeTab, filtersCacheKey, baseParams, applyItems]);

  return {
    nomenclaturaItems,
    geolocalizacionItems,
    loading,
    error,
    refetch,
    invalidateCache,
  };
};
