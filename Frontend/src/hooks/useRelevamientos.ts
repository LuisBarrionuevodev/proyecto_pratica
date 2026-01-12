import { useEffect, useState } from "react";
import type { IRelevamiento } from "../types/relevamientos";
import { getRelevamientos } from "../api/relevamientosApi";

export const useRelevamientos = () => {
  const [relevamientos, setRelevamientos] = useState<IRelevamiento[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchRelevamientos = async () => {
      try {
        const data = await getRelevamientos();
        setRelevamientos(data);
      } catch (error) {
        console.error("Error al obtener relevamientos:", error);
      } finally {
        setLoading(false);
      }
    };

    fetchRelevamientos();
  }, []);

  return { relevamientos, setRelevamientos, loading };
};
