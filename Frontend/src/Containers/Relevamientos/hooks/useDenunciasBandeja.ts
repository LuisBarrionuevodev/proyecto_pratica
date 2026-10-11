import { useCallback, useEffect, useState } from "react";
import type {
  IDenunciaGestionItem,
  IDenunciasGestionFilters,
  IDenunciasGestionMeta,
} from "../../../api/denunciasApi";
import { getDenunciasGestionOperativa, getDenunciasGestionProcesados } from "../../../api/denunciasApi";

export type DenunciasBandejaSlice = "pendientes" | "procesados";

interface UseDenunciasBandeja {
  denuncias: IDenunciaGestionItem[];
  meta: IDenunciasGestionMeta | null;
  loading: boolean;
  error: string | null;
  hasSearched: boolean;
  buscar: (filters: IDenunciasGestionFilters) => Promise<void>;
  limpiarLista: () => void;
}

/**
 * Pendientes: GET gestion-operativa (iniciador DENUNCIA pendiente).
 * Procesados: GET gestion-procesados (iniciador DENUNCIA terminal).
 */
export const useDenunciasBandeja = (slice: DenunciasBandejaSlice): UseDenunciasBandeja => {
  const [denuncias, setDenuncias] = useState<IDenunciaGestionItem[]>([]);
  const [meta, setMeta] = useState<IDenunciasGestionMeta | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [hasSearched, setHasSearched] = useState(false);

  const buscar = useCallback(
    async (filters: IDenunciasGestionFilters) => {
      setLoading(true);
      setError(null);
      setHasSearched(true);
      try {
        const response =
          slice === "pendientes"
            ? await getDenunciasGestionOperativa({
                desde: filters.desde,
                hasta: filters.hasta,
                page: filters.page,
                page_size: filters.page_size,
              })
            : await getDenunciasGestionProcesados({
                desde: filters.desde,
                hasta: filters.hasta,
                page: filters.page,
                page_size: filters.page_size,
              });
        setDenuncias(response.items);
        setMeta(response.meta);
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

  /** Al cambiar de pestaña: sin tabla hasta Filtrar. */
  useEffect(() => {
    setHasSearched(false);
    setDenuncias([]);
    setMeta(null);
    setError(null);
  }, [slice]);

  const limpiarLista = useCallback(() => {
    setHasSearched(false);
    setDenuncias([]);
    setMeta(null);
    setError(null);
  }, []);

  return {
    denuncias,
    meta,
    loading,
    error,
    hasSearched,
    buscar,
    limpiarLista,
  };
};
