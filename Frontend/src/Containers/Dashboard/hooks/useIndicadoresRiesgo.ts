import { useCallback, useEffect, useState } from "react";
import {
  fetchIndicadoresRiesgo,
  type IndicadoresFiltrosParams,
  type IndicadoresRiesgoResponse,
} from "../../../api/indicadoresApi";

export interface UseIndicadoresRiesgoResult {
  data: IndicadoresRiesgoResponse | null;
  loading: boolean;
  error: string | null;
  refetch: () => void;
}

function parseIndicadoresError(err: unknown): string {
  const msg =
    err && typeof err === "object" && "response" in err
      ? (err as { response?: { data?: { detail?: string } } }).response?.data?.detail
      : null;
  return typeof msg === "string" ? msg : "No se pudo cargar el riesgo bromatológico.";
}

/**
 * Carga `GET /api/indicadores/riesgo` cuando cambian fechas o filtros.
 */
export function useIndicadoresRiesgo(
  params: IndicadoresFiltrosParams | null
): UseIndicadoresRiesgoResult {
  const [data, setData] = useState<IndicadoresRiesgoResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [tick, setTick] = useState(0);

  const refetch = useCallback(() => setTick((t) => t + 1), []);

  useEffect(() => {
    if (!params?.desde || !params?.hasta) {
      setData(null);
      setLoading(false);
      setError(null);
      return;
    }

    let cancelled = false;
    setLoading(true);
    setError(null);

    fetchIndicadoresRiesgo(params)
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
  }, [params, tick]);

  return { data, loading, error, refetch };
}
