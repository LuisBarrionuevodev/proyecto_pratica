import { useCallback, useState } from "react";
import type {
  IDenunciaGestionItem,
  IDenunciasGestionFilters,
  IDenunciasGestionMeta,
} from "../../../api/denunciasApi";
import { getDenunciasGestion } from "../../../api/denunciasApi";

interface UseDenunciasFiltradas {
  denuncias: IDenunciaGestionItem[];
  meta: IDenunciasGestionMeta | null;
  loading: boolean;
  error: string | null;
  hasSearched: boolean;
  buscar: (filters: IDenunciasGestionFilters) => Promise<void>;
}

export const useDenunciasFiltradas = (): UseDenunciasFiltradas => {
  const [denuncias, setDenuncias] = useState<IDenunciaGestionItem[]>([]);
  const [meta, setMeta] = useState<IDenunciasGestionMeta | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [hasSearched, setHasSearched] = useState(false);

  const buscar = useCallback(async (filters: IDenunciasGestionFilters) => {
    setLoading(true);
    setError(null);
    setHasSearched(true);
    try {
      const response = await getDenunciasGestion(filters);
      setDenuncias(response.items);
      setMeta(response.meta);
    } catch (err: any) {
      setError(err?.response?.data?.detail || "Error al cargar denuncias");
      setDenuncias([]);
      setMeta(null);
    } finally {
      setLoading(false);
    }
  }, []);

  return {
    denuncias,
    meta,
    loading,
    error,
    hasSearched,
    buscar,
  };
};

