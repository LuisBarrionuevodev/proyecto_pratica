import { useEffect, useState } from "react";
import { fetchCallesCatalogo } from "../api/callesCatalogoApi";

export const useCallesCatalogo = () => {
  const [calles, setCalles] = useState<string[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    setLoading(true);
    fetchCallesCatalogo()
      .then((items) => {
        if (!active) return;
        const unique = Array.from(new Set(items));
        setCalles(unique);
        setError(null);
      })
      .catch((err: any) => {
        if (!active) return;
        setError(err?.response?.data?.detail || "Error al cargar catálogo de calles");
      })
      .finally(() => {
        if (!active) return;
        setLoading(false);
      });

    return () => {
      active = false;
    };
  }, []);

  return { calles, loading, error };
};
