import { useCallback, useEffect, useState } from "react";
import { getInspectorFotosPendientesCount } from "../api/completarTrabajoApi";
import { useAppSession } from "../auth/AppSessionProvider";
import { subscribeInspectorFotosPendientesRefresh } from "../features/media/utils/mediaUploadSessionNotify";

const POLL_MS = 60_000;

/**
 * Conteo de trabajos con fotos pendientes para el Inspector autenticado.
 */
export function useInspectorFotosPendientesCount() {
  const { role } = useAppSession();
  const enabled = role === "relevador";
  const [count, setCount] = useState(0);

  const reload = useCallback(async () => {
    if (!enabled) {
      setCount(0);
      return;
    }
    try {
      const n = await getInspectorFotosPendientesCount();
      setCount(n);
    } catch {
      /* mantener último valor conocido */
    }
  }, [enabled]);

  useEffect(() => {
    void reload();
    if (!enabled) return;
    const id = window.setInterval(() => void reload(), POLL_MS);
    const unsub = subscribeInspectorFotosPendientesRefresh(() => void reload());
    return () => {
      window.clearInterval(id);
      unsub();
    };
  }, [enabled, reload]);

  return { count, enabled, reload };
}
