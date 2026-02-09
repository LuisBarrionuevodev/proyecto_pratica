import { useEffect, useState } from "react";
import { fetchCallesCatalogo, type CalleCatalogoItem } from "../../../api/geolocalizacionApi";

export const useCallesCatalogoOptions = () => {
  const [items, setItems] = useState<CalleCatalogoItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    setLoading(true);
    fetchCallesCatalogo("", 200)
      .then((resp) => {
        if (!active) return;
        setItems(resp.items || []);
        setError(null);
      })
      .catch((err: any) => {
        if (!active) return;
        setError(err?.response?.data?.detail || "Error al cargar catálogo");
      })
      .finally(() => {
        if (!active) return;
        setLoading(false);
      });
    return () => {
      active = false;
    };
  }, []);

  return { items, loading, error };
};
