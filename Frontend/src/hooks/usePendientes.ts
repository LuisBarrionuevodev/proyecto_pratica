import { useState, useEffect } from "react";
import type { IActuacion } from "../types/actuaciones";
import { getActuaciones } from "../api/actuacionesApi";

export const usePendientes = () => {
  const [pendientes, setPendientes] = useState<IActuacion[]>([]);
  const [loading, setLoading] = useState(true);

    useEffect(() => {
    const fetchPendientes = async () => {
      try {
        const data = await getActuaciones();
        setPendientes(data);
      } catch (error) {
        console.error("Error al obtener Pendientes:", error);
      } finally {
        setLoading(false);
      }
    };
    fetchPendientes();
  }, []);
    return { pendientes, setPendientes, loading };
};