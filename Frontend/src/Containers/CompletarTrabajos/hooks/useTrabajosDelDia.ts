import { useEffect, useState } from "react";

import type { TrabajoDelDiaRow } from "../types/completarTrabajos.types";
import { getMockTrabajosDelDiaRows } from "./mockTrabajosDelDiaData";

const MOCK_DELAY_MS = 450;

/**
 * Carga trabajos del día para una fecha (mock local con latencia simulada).
 *
 * @param fecha - ISO date YYYY-MM-DD; si vacío, no dispara carga.
 * @returns rows, loading, error — listo para reemplazar por fetch real.
 */
export function useTrabajosDelDia(fecha: string | null) {
  const [rows, setRows] = useState<TrabajoDelDiaRow[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!fecha) {
      setRows([]);
      setError(null);
      setLoading(false);
      return;
    }

    let cancelled = false;
    setLoading(true);
    setError(null);

    const timer = window.setTimeout(() => {
      if (cancelled) return;
      try {
        const next = getMockTrabajosDelDiaRows(fecha);
        setRows(next);
      } catch {
        setError("No se pudieron cargar los trabajos del día.");
        setRows([]);
      } finally {
        if (!cancelled) setLoading(false);
      }
    }, MOCK_DELAY_MS);

    return () => {
      cancelled = true;
      window.clearTimeout(timer);
    };
  }, [fecha]);

  return { rows, loading, error };
}
