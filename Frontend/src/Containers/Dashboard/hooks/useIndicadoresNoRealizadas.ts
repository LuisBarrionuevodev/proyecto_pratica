import { useCallback, useEffect, useState } from "react";
import {
  fetchIndicadoresNoRealizadas,
  type IndicadoresFiltrosParams,
  type IndicadoresNoRealizadasResponse,
} from "../../../api/indicadoresApi";

export interface UseIndicadoresNoRealizadasResult {
  data: IndicadoresNoRealizadasResponse | null;
  loading: boolean;
  error: string | null;
  refetch: () => void;
}

function parseIndicadoresError(err: unknown): string {
  const msg =
    err && typeof err === "object" && "response" in err
      ? (err as { response?: { data?: { detail?: string } } }).response?.data?.detail
      : null;
  return typeof msg === "string" ? msg : "No se pudo cargar las no realizadas.";
}

/**
 * Carga `GET /api/indicadores/no-realizadas` cuando cambian fechas o filtros.
 */
export function useIndicadoresNoRealizadas(
  params: IndicadoresFiltrosParams | null
): UseIndicadoresNoRealizadasResult {
  const [data, setData] = useState<IndicadoresNoRealizadasResponse | null>(null);
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

    fetchIndicadoresNoRealizadas(params)
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
