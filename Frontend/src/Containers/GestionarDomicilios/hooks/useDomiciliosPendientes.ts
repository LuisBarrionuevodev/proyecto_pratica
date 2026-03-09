import { useCallback, useEffect, useState } from "react";
import { getMapPendientes } from "../../../api/mapApi";
import type { DomicilioPendienteItem, DomiciliosFilters } from "../types";

export const useDomiciliosPendientes = (filters: DomiciliosFilters) => {
  const [nomenclaturaItems, setNomenclaturaItems] = useState<DomicilioPendienteItem[]>([]);
  const [geolocalizacionItems, setGeolocalizacionItems] = useState<DomicilioPendienteItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const refetch = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const baseParams = {
        desde: filters.desde || undefined,
        hasta: filters.hasta || undefined,
        scope: filters.scope || undefined,
      };
      const [norm, map] = await Promise.all([
        getMapPendientes({ ...baseParams, kind: "norm" }),
        getMapPendientes({ ...baseParams, kind: "map" }),
      ]);
      setNomenclaturaItems(norm);
      setGeolocalizacionItems(map);
    } catch (err: any) {
      setError(err?.response?.data?.detail || "Error al cargar domicilios pendientes");
      setNomenclaturaItems([]);
      setGeolocalizacionItems([]);
    } finally {
      setLoading(false);
    }
  }, [filters.desde, filters.hasta, filters.scope]);

  useEffect(() => {
    refetch();
  }, [refetch]);

  return {
    nomenclaturaItems,
    geolocalizacionItems,
    loading,
    error,
    refetch,
  };
};
