import { useState, useEffect } from "react";
import type { IActuacion } from "../types/actuaciones";
import { getActuaciones } from "../api/actuacionesApi";

export const useGestionActuaciones = () => {
  const [actuaciones, setActuaciones] = useState<IActuacion[]>([]);
  const [loading, setLoading] = useState(true);

    useEffect(() => {
    const fetchActuaciones = async () => {
      try {
        const data = await getActuaciones();
        setActuaciones(data);
      } catch (error) {
        console.error("Error al obtener actuaciones:", error);
      } finally {
        setLoading(false);
      }
    };
    fetchActuaciones();
  }, []);
    return { actuaciones, setActuaciones, loading };
};