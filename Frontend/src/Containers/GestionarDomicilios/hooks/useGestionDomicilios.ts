import { useCallback, useEffect, useMemo, useState } from "react";
import {
  getGestionDomicilios,
  type GestionDomiciliosResponse,
  type GestionDomiciliosStatusOperativo,
} from "../../../api/gestionDomiciliosApi";
import { perfLog, perfTimed } from "../../../utils/perfLog";
import { mapModeForStatusFilter } from "../gestionDomiciliosOperativoFilters";

const DEFAULT_PAGE_SIZE = 50;

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
  const [searchQ, setSearchQ] = useState("");
  const [data, setData] = useState<GestionDomiciliosResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const queryParams = useMemo(
    () => ({
      status_operativo: statusOperativo,
      page,
      page_size: DEFAULT_PAGE_SIZE,
      q: searchQ.trim() || undefined,
      include_map_points: true as const,
      map_mode: mapModeForStatusFilter(statusOperativo),
      sort: "requiere_accion_desc" as const,
    }),
    [page, searchQ, statusOperativo]
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
      });
    } catch (err: unknown) {
      const detail = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
      setError(typeof detail === "string" ? detail : "Error al cargar domicilios");
      setData(null);
    } finally {
      setLoading(false);
    }
  }, [enabled, queryParams, statusOperativo, page]);

  useEffect(() => {
    void fetchData();
  }, [fetchData]);

  const refetch = useCallback(async () => {
    await fetchData();
  }, [fetchData]);

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
    searchQ,
    setSearchQ,
    refetch,
    pageSize: DEFAULT_PAGE_SIZE,
  };
}
