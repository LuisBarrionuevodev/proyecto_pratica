import { useCallback, useEffect, useState } from "react";
import {
  fetchIndicadoresPendientes,
  type IndicadoresFiltrosParams,
  type IndicadoresPendientesResponse,
} from "../../../api/indicadoresApi";

export interface UseIndicadoresPendientesResult {
  data: IndicadoresPendientesResponse | null;
  loading: boolean;
  error: string | null;
  refetch: () => void;
}

function parseIndicadoresError(err: unknown): string {
  const msg =
    err && typeof err === "object" && "response" in err
      ? (err as { response?: { data?: { detail?: string } } }).response?.data?.detail
      : null;
  return typeof msg === "string" ? msg : "No se pudieron cargar los pendientes operativos.";
}

/** Fechas de contrato API; el backend ignora el período para pendientes (stock actual). */
const PENDIENTES_API_DESDE = "2000-01-01";
const PENDIENTES_API_HASTA = "2099-12-31";

/**
 * Carga `GET /api/indicadores/pendientes` cuando cambia el filtro de distrito.
 * No depende del tab Semanal/Mensual/Trimestral/Anual ni del inspector.
 */
export function useIndicadoresPendientes(
  params: Pick<IndicadoresFiltrosParams, "distrito_id"> | null
): UseIndicadoresPendientesResult {
  const [data, setData] = useState<IndicadoresPendientesResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [tick, setTick] = useState(0);

  const refetch = useCallback(() => setTick((t) => t + 1), []);
  const distritoId = params?.distrito_id;

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);

    const query: IndicadoresFiltrosParams = {
      desde: PENDIENTES_API_DESDE,
      hasta: PENDIENTES_API_HASTA,
    };
    if (distritoId != null) {
      query.distrito_id = distritoId;
    }

    fetchIndicadoresPendientes(query)
      .then((res) => {
        if (!cancelled) {
          setData(res);
        }
      })
      .catch((err: unknown) => {
        if (cancelled) return;
        setError(parseIndicadoresError(err));
        setData(null);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [distritoId, tick]);

  return { data, loading, error, refetch };
}
