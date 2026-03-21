import { useCallback, useState } from "react";

import { getMapPointsV2, type MapPointFeature } from "../../../api/mapApi";

export type MapaOperativoModo = "pendientes" | "realizados";

export type LoadRealizadosParams = {
  from: string;
  to: string;
  distritoId: string;
  tipoIniciador: string;
};

/**
 * Estado y carga del mapa operativo.
 *
 * Pendientes: sin API dedicada aún → lista vacía.
 * Realizados: usa temporalmente `GET /map/points` (getMapPointsV2) con fecha, distrito y origen según tipo.
 */
export function useMapaOperativo() {
  const [features, setFeatures] = useState<MapPointFeature[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [infoMessage, setInfoMessage] = useState<string | null>(null);

  const loadPendientes = useCallback(() => {
    setLoading(false);
    setError(null);
    setInfoMessage(
      "Los pendientes operativos se conectarán al endpoint municipal (p. ej. /map/operativo). Por ahora no hay datos en mapa."
    );
    setFeatures([]);
  }, []);

  const loadRealizados = useCallback(async (params: LoadRealizadosParams) => {
    setInfoMessage(null);
    setLoading(true);
    setError(null);
    try {
      const distrito_id = params.distritoId ? Number(params.distritoId) : undefined;
      if (params.distritoId && Number.isNaN(distrito_id)) {
        setError("Distrito no válido.");
        setFeatures([]);
        return;
      }

      let origin: string | undefined;
      if (params.tipoIniciador === "RELEVAMIENTOS") {
        origin = "relevamientos";
      } else if (params.tipoIniciador === "TODOS") {
        origin = undefined;
      } else {
        origin = "actuaciones";
      }

      const fc = await getMapPointsV2({
        from: params.from || undefined,
        to: params.to || undefined,
        distrito_id,
        origin,
      });
      setFeatures(fc.features ?? []);
    } catch (e: unknown) {
      const err = e as { response?: { data?: { detail?: string } } };
      setError(err?.response?.data?.detail ?? "No se pudieron cargar los puntos.");
      setFeatures([]);
    } finally {
      setLoading(false);
    }
  }, []);

  const clearForModoSwitch = useCallback(() => {
    setError(null);
    setInfoMessage(null);
    setFeatures([]);
  }, []);

  return {
    features,
    loading,
    error,
    infoMessage,
    setInfoMessage,
    loadPendientes,
    loadRealizados,
    clearForModoSwitch,
    setFeatures,
  };
}
