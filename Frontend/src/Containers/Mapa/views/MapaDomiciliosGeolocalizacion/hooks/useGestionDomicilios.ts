import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  getGestionDomicilios,
  type GestionDomiciliosResponse,
  type GestionDomiciliosStatusOperativo,
} from "../../../../../api/gestionDomiciliosApi";
import { perfLog, perfTimed } from "../../../../../utils/perfLog";
import { mapModeForStatusFilter } from "../mapaDomiciliosOperativoFilters";

const DEFAULT_PAGE_SIZE = 50;
export const GESTION_DOMICILIOS_SEARCH_DEBOUNCE_MS = 400;

export type UseGestionDomiciliosOptions = {
  enabled?: boolean;
};

export function useGestionDomicilios(
  initialStatus: GestionDomiciliosStatusOperativo = "requiere_accion",
  options?: UseGestionDomiciliosOptions
) {
  const enabled = options?.enabled ?? true;
  const [statusOperativo, setStatusOperativo] =
    useState<GestionDomiciliosStatusOperativo>(initialStatus);
  const [page, setPage] = useState(1);
  const [searchInput, setSearchInput] = useState("");
  const [appliedQ, setAppliedQ] = useState("");
  const [data, setData] = useState<GestionDomiciliosResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const prevAppliedQRef = useRef(appliedQ);

  useEffect(() => {
    const timer = window.setTimeout(() => {
      setAppliedQ(searchInput.trim());
    }, GESTION_DOMICILIOS_SEARCH_DEBOUNCE_MS);
    return () => window.clearTimeout(timer);
  }, [searchInput]);

  useEffect(() => {
    if (prevAppliedQRef.current !== appliedQ) {
      prevAppliedQRef.current = appliedQ;
      setPage(1);
    }
  }, [appliedQ]);

  const queryParams = useMemo(
    () => ({
      status_operativo: statusOperativo,
      page,
      page_size: DEFAULT_PAGE_SIZE,
      q: appliedQ || undefined,
      include_map_points: true as const,
      map_mode: mapModeForStatusFilter(statusOperativo),
      sort: "requiere_accion_desc" as const,
    }),
    [appliedQ, page, statusOperativo]
  );

  const fetchData = useCallback(async () => {
    if (!enabled) return;
    setLoading(true);
    setError(null);
    try {
      const response = await perfTimed("gestionDomicilios.fetch", () =>
        getGestionDomicilios(queryParams)
      );
      setData(response);
      perfLog("gestionDomicilios.loaded", {
        status_operativo: statusOperativo,
        rows: response.rows.length,
        map_points: response.map_points.length,
        page,
        q: appliedQ || null,
      });
    } catch (err: unknown) {
      const detail = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
      setError(typeof detail === "string" ? detail : "Error al cargar domicilios");
      setData(null);
    } finally {
      setLoading(false);
    }
  }, [appliedQ, enabled, page, queryParams, statusOperativo]);

  useEffect(() => {
    void fetchData();
  }, [fetchData]);

  const refetch = useCallback(async () => {
    await fetchData();
  }, [fetchData]);

  const applySearch = useCallback(() => {
    const next = searchInput.trim();
    setAppliedQ(next);
    setPage(1);
  }, [searchInput]);

  const clearSearch = useCallback(() => {
    setSearchInput("");
    setAppliedQ("");
    setPage(1);
  }, []);

  const changeStatusFilter = useCallback((next: GestionDomiciliosStatusOperativo) => {
    setStatusOperativo(next);
    setPage(1);
  }, []);

  return {
    data,
    loading,
    error,
    statusOperativo,
    setStatusOperativo: changeStatusFilter,
    page,
    setPage,
    searchQ: searchInput,
    setSearchQ: setSearchInput,
    appliedQ,
    applySearch,
    clearSearch,
    refetch,
    pageSize: DEFAULT_PAGE_SIZE,
  };
}
