import { useState, useEffect } from "react";
import type { IPoligono } from "../types/poligonos";
import { getPoligonos } from "../api/poligonosApi";

export const usePoligonos = () => {
  const [poligonos, setPoligonos] = useState<IPoligono[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchPoligonos = async () => {
      try {
        const data = await getPoligonos();
        setPoligonos(data);
      } catch (error) {
        console.error("Error al obtener polígonos:", error);
      } finally {
        setLoading(false);
      }
    };

    fetchPoligonos();
  }, []);

  return { poligonos, setPoligonos, loading };
};
