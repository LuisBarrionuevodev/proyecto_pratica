import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { getMapPendientes } from "../../../api/mapApi";
import { mergeSliceItems, sortItemsForReview } from "../domicilioItemsMerge";
import { SLICES_FOR_VIEW } from "../domicilioViewTabs";
import type { DomiciliosViewTab } from "../domicilioViewTabs";
import type { DomicilioPendienteItem, DomiciliosFilters, DomiciliosSlice } from "../types";

export type UseDomiciliosPendientesOptions = {
  enabled?: boolean;
};

export type DomiciliosLoadSelection =
  | { mode: "slice"; slice: DomiciliosSlice }
  | {
      mode: "view";
      view: DomiciliosViewTab;
      filterSlice?: DomiciliosSlice | "all";
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

function slicesForSelection(selection: DomiciliosLoadSelection): readonly DomiciliosSlice[] {
  if (selection.mode === "slice") return [selection.slice];
  return SLICES_FOR_VIEW[selection.view];
}

/**
 * Carga domicilios por slice o vista agrupada PR6B, con cache por slice+filtros.
 */
export const useDomiciliosPendientes = (
  filters: DomiciliosFilters,
  selection: DomiciliosLoadSelection,
  options?: UseDomiciliosPendientesOptions
) => {
  const enabled = options?.enabled ?? true;
  const slicesToLoad = useMemo(() => slicesForSelection(selection), [selection]);

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
      await Promise.all(slicesToLoad.map((slice) => ensureSliceLoaded(slice, true)));
    } catch (err: unknown) {
      const detail = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
      setError(typeof detail === "string" ? detail : "Error al cargar domicilios pendientes");
      for (const slice of slicesToLoad) {
        setItemsBySlice((prev) => ({ ...prev, [slice]: [] }));
        delete itemsBySliceRef.current[slice];
      }
    } finally {
      setLoading(false);
    }
  }, [ensureSliceLoaded, slicesToLoad]);

  useEffect(() => {
    if (!enabled) {
      invalidateCache();
      setError(null);
      setLoading(false);
      return;
    }

    const allCached = slicesToLoad.every(
      (slice) => itemsBySliceRef.current[slice]?.key === filtersCacheKey
    );
    if (allCached) {
      const next: Partial<Record<DomiciliosSlice, DomicilioPendienteItem[]>> = {};
      for (const slice of slicesToLoad) {
        next[slice] = itemsBySliceRef.current[slice]?.items ?? [];
      }
      setItemsBySlice((prev) => ({ ...prev, ...next }));
      setError(null);
      setLoading(false);
      return;
    }

    let cancel = false;
    const run = async () => {
      setLoading(true);
      setError(null);
      try {
        await Promise.all(slicesToLoad.map((slice) => ensureSliceLoaded(slice)));
        if (cancel) return;
      } catch (err: unknown) {
        if (cancel) return;
        const detail = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
        setError(typeof detail === "string" ? detail : "Error al cargar domicilios pendientes");
      } finally {
        if (!cancel) setLoading(false);
      }
    };
    void run();
    return () => {
      cancel = true;
    };
  }, [enabled, slicesToLoad, filtersCacheKey, ensureSliceLoaded, invalidateCache]);

  const filterSlice =
    selection.mode === "view" ? (selection.filterSlice ?? "all") : selection.slice;

  const activeItems = useMemo(() => {
    const merged = mergeSliceItems(slicesToLoad, itemsBySlice, filterSlice);
    if (selection.mode === "view" && selection.view === "para_revisar") {
      return sortItemsForReview(merged);
    }
    return merged;
  }, [filterSlice, itemsBySlice, selection, slicesToLoad]);

  const getSliceCount = useCallback(
    (slice: DomiciliosSlice): number | null => {
      const items = itemsBySlice[slice] ?? itemsBySliceRef.current[slice]?.items;
      if (items) return items.length;
      const token = `${slice}:${filtersCacheKey}`;
      return loadedSlicesRef.current.has(token) ? 0 : null;
    },
    [filtersCacheKey, itemsBySlice]
  );

  const getViewCount = useCallback(
    (view: DomiciliosViewTab): number | null => {
      const slices = SLICES_FOR_VIEW[view];
      let total = 0;
      let anyUnknown = false;
      for (const slice of slices) {
        const count = getSliceCount(slice);
        if (count == null) {
          anyUnknown = true;
          continue;
        }
        total += count;
      }
      return anyUnknown ? null : total;
    },
    [getSliceCount]
  );

  const isSliceLoaded = useCallback(
    (slice: DomiciliosSlice): boolean => {
      const cached = itemsBySliceRef.current[slice];
      return cached?.key === filtersCacheKey;
    },
    [filtersCacheKey]
  );

  const activeSlice =
    selection.mode === "slice"
      ? selection.slice
      : filterSlice === "all"
        ? slicesToLoad[0]
        : filterSlice;

  return {
    activeItems,
    activeSlice,
    itemsBySlice,
    loading,
    error,
    refreshActiveSlice,
    refetch: refreshActiveSlice,
    invalidateCache,
    ensureSliceLoaded,
    getSliceCount,
    getViewCount,
    isSliceLoaded,
    loadedSlicesRef,
    itemsBySliceRef,
    nomenclaturaItems:
      itemsBySlice.nomenclatura_pendiente ??
      itemsBySliceRef.current.nomenclatura_pendiente?.items ??
      [],
    geolocalizacionItems:
      itemsBySlice.geo_pendiente ?? itemsBySliceRef.current.geo_pendiente?.items ?? [],
  };
};
