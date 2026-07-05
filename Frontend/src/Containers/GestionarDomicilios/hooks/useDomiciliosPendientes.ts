import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { getMapPendientes } from "../../../api/mapApi";
import type { DomicilioPendienteItem, DomiciliosFilters, DomiciliosSlice } from "../types";

export type UseDomiciliosPendientesOptions = {
  /**
   * Si es false, no se consulta la API al montar ni al cambiar filtros.
   */
  enabled?: boolean;
};

type SliceCacheSlot = {
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

/**
 * Carga domicilios por slice PR2 con cache por pestaña+filtros.
 */
export const useDomiciliosPendientes = (
  filters: DomiciliosFilters,
  activeSlice: DomiciliosSlice,
  options?: UseDomiciliosPendientesOptions
) => {
  const enabled = options?.enabled ?? true;

  const [itemsBySlice, setItemsBySlice] = useState<
    Partial<Record<DomiciliosSlice, DomicilioPendienteItem[]>>
  >({});
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const itemsBySliceRef = useRef<Partial<Record<DomiciliosSlice, SliceCacheSlot>>>({});
  const loadedSlicesRef = useRef<Set<string>>(new Set());

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
    itemsBySliceRef.current = {};
    loadedSlicesRef.current = new Set();
    setItemsBySlice({});
  }, []);

  const ensureSliceLoaded = useCallback(
    async (slice: DomiciliosSlice, force = false) => {
      const cacheToken = `${slice}:${filtersCacheKey}`;
      const cached = itemsBySliceRef.current[slice];
      if (!force && cached?.key === filtersCacheKey) {
        setItemsBySlice((prev) => ({ ...prev, [slice]: cached.items }));
        loadedSlicesRef.current.add(cacheToken);
        return cached.items;
      }

      const items = await getMapPendientes({ ...baseParams(), slice });
      itemsBySliceRef.current[slice] = { key: filtersCacheKey, items };
      loadedSlicesRef.current.add(cacheToken);
      setItemsBySlice((prev) => ({ ...prev, [slice]: items }));
      return items;
    },
    [baseParams, filtersCacheKey]
  );

  const refreshActiveSlice = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      await ensureSliceLoaded(activeSlice, true);
    } catch (err: unknown) {
      const detail = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
      setError(typeof detail === "string" ? detail : "Error al cargar domicilios pendientes");
      setItemsBySlice((prev) => ({ ...prev, [activeSlice]: [] }));
      delete itemsBySliceRef.current[activeSlice];
    } finally {
      setLoading(false);
    }
  }, [activeSlice, ensureSliceLoaded]);

  useEffect(() => {
    if (!enabled) {
      invalidateCache();
      setError(null);
      setLoading(false);
      return;
    }

    const cached = itemsBySliceRef.current[activeSlice];
    if (cached?.key === filtersCacheKey) {
      setItemsBySlice((prev) => ({ ...prev, [activeSlice]: cached.items }));
      setError(null);
      setLoading(false);
      return;
    }

    let cancel = false;
    const run = async () => {
      setLoading(true);
      setError(null);
      try {
        await ensureSliceLoaded(activeSlice);
        if (cancel) return;
      } catch (err: unknown) {
        if (cancel) return;
        const detail = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
        setError(typeof detail === "string" ? detail : "Error al cargar domicilios pendientes");
        setItemsBySlice((prev) => ({ ...prev, [activeSlice]: [] }));
      } finally {
        if (!cancel) setLoading(false);
      }
    };
    void run();
    return () => {
      cancel = true;
    };
  }, [enabled, activeSlice, filtersCacheKey, ensureSliceLoaded, invalidateCache]);

  const activeItems = itemsBySlice[activeSlice] ?? itemsBySliceRef.current[activeSlice]?.items ?? [];

  const getSliceCount = useCallback(
    (slice: DomiciliosSlice): number | null => {
      const items = itemsBySlice[slice] ?? itemsBySliceRef.current[slice]?.items;
      if (items) return items.length;
      const token = `${slice}:${filtersCacheKey}`;
      return loadedSlicesRef.current.has(token) ? 0 : null;
    },
    [filtersCacheKey, itemsBySlice]
  );

  const isSliceLoaded = useCallback(
    (slice: DomiciliosSlice): boolean => {
      const cached = itemsBySliceRef.current[slice];
      return cached?.key === filtersCacheKey;
    },
    [filtersCacheKey]
  );

  return {
    activeItems,
    itemsBySlice,
    loading,
    error,
    refreshActiveSlice,
    /** Alias histórico (STAB-10). */
    refetch: refreshActiveSlice,
    invalidateCache,
    ensureSliceLoaded,
    getSliceCount,
    isSliceLoaded,
    loadedSlicesRef,
    itemsBySliceRef,
    /** Compat temporal: ya no hay split norm/map. */
    nomenclaturaItems: activeSlice === "nomenclatura_pendiente" ? activeItems : itemsBySlice.nomenclatura_pendiente ?? [],
    geolocalizacionItems: activeSlice === "geo_pendiente" ? activeItems : itemsBySlice.geo_pendiente ?? [],
  };
};
