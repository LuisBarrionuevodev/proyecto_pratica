import { useCallback, useEffect, useState } from "react";
import { getRutaItemArchivos } from "../../../api/mediaApi";
import type { RutaItemArchivosListResponse } from "../mediaTypes";

/**
 * Carga archivos READY del backend para un `rutaItemId` (continuación de carga / modal evidencias).
 */
export function useRutaItemReadyArchivos(rutaItemId: number | null | undefined, enabled: boolean) {
  const [data, setData] = useState<RutaItemArchivosListResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const reload = useCallback(async () => {
    if (rutaItemId == null) {
      setData(null);
      setError(null);
      return;
    }
    setLoading(true);
    try {
      setError(null);
      const res = await getRutaItemArchivos(rutaItemId);
      setData(res);
    } catch {
      setError("No se pudieron cargar las fotos ya subidas.");
    } finally {
      setLoading(false);
    }
  }, [rutaItemId]);

  useEffect(() => {
    if (!enabled || rutaItemId == null) {
      setData(null);
      setError(null);
      return;
    }
    void reload();
  }, [enabled, rutaItemId, reload]);

  return { data, loading, error, reload };
}
