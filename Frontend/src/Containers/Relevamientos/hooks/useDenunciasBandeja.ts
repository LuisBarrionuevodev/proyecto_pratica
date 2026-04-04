import { useCallback, useEffect, useState } from "react";
import type {
  IDenunciaGestionItem,
  IDenunciasGestionFilters,
  IDenunciasGestionMeta,
} from "../../../api/denunciasApi";
import { getDenunciasGestion, getDenunciasGestionOperativa } from "../../../api/denunciasApi";

export type DenunciasBandejaSlice = "pendientes" | "realizados";

interface UseDenunciasBandeja {
  denuncias: IDenunciaGestionItem[];
  meta: IDenunciasGestionMeta | null;
  loading: boolean;
  error: string | null;
  hasSearched: boolean;
  buscar: (filters: IDenunciasGestionFilters) => Promise<void>;
}

/**
 * Pendientes: GET gestion-operativa (iniciador DENUNCIA pendiente).
 * Realizados: GET gestion con `estado` efectivo (hechas / no_hechas / all).
 */
export const useDenunciasBandeja = (slice: DenunciasBandejaSlice): UseDenunciasBandeja => {
  const [denuncias, setDenuncias] = useState<IDenunciaGestionItem[]>([]);
  const [meta, setMeta] = useState<IDenunciasGestionMeta | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [hasSearched, setHasSearched] = useState(false);

  useEffect(() => {
    setDenuncias([]);
    setMeta(null);
    setHasSearched(false);
    setError(null);
  }, [slice]);

  const buscar = useCallback(
    async (filters: IDenunciasGestionFilters) => {
      setLoading(true);
      setError(null);
      setHasSearched(true);
      try {
        if (slice === "pendientes") {
          const response = await getDenunciasGestionOperativa({
            desde: filters.desde,
            hasta: filters.hasta,
            page: filters.page,
            page_size: filters.page_size,
          });
          setDenuncias(response.items);
          setMeta(response.meta);
        } else {
          const response = await getDenunciasGestion({
            desde: filters.desde,
            hasta: filters.hasta,
            estado: filters.estado ?? "all",
            page: filters.page,
            page_size: filters.page_size,
          });
          setDenuncias(response.items);
          setMeta(response.meta);
        }
      } catch (err: any) {
        setError(err?.response?.data?.detail || "Error al cargar denuncias");
        setDenuncias([]);
        setMeta(null);
      } finally {
        setLoading(false);
      }
    },
    [slice]
  );

  return {
    denuncias,
    meta,
    loading,
    error,
    hasSearched,
    buscar,
  };
};
