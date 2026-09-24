import { useCallback, useEffect, useState } from "react";
import {
  fetchIndicadoresResumen,
  type IndicadoresResumenParams,
  type IndicadoresResumenResponse,
} from "../../../api/indicadoresApi";

export interface UseIndicadoresResumenResult {
  data: IndicadoresResumenResponse | null;
  loading: boolean;
  error: string | null;
  refetch: () => void;
}

/**
 * Carga `GET /api/indicadores/resumen` cuando cambian fechas o filtros opcionales.
 *
 * Parámetros: mismo criterio que el backend (desde/hasta obligatorios en ISO date).
 * Retorno: data, loading, error legible, refetch manual.
 */
export function useIndicadoresResumen(params: IndicadoresResumenParams | null): UseIndicadoresResumenResult {
  const [data, setData] = useState<IndicadoresResumenResponse | null>(null);
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

    fetchIndicadoresResumen(params)
      .then((res) => {
        if (!cancelled) {
          setData(res);
        }
      })
      .catch((err: unknown) => {
        if (cancelled) return;
        const msg =
          err && typeof err === "object" && "response" in err
            ? (err as { response?: { data?: { detail?: string } } }).response?.data?.detail
            : null;
        setError(typeof msg === "string" ? msg : "No se pudieron cargar los indicadores.");
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
