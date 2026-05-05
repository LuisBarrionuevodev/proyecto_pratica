import { useState, useCallback } from "react";
import type {
    IActuacionListItem,
    IActuacionesListMeta,
    IActuacionesListFilters,
} from "../../../api/actuacionesListApi";
import { getActuacionesFiltered } from "../../../api/actuacionesListApi";

interface UseActuacionesFiltradas {
    actuaciones: IActuacionListItem[];
    meta: IActuacionesListMeta | null;
    loading: boolean;
    error: string | null;
    hasSearched: boolean;
    buscar: (filters: IActuacionesListFilters) => Promise<void>;
    /** Fusiona una fila devuelta por el servidor (p. ej. POST quitar-acta) sin disparar `loading` ni remontar la grilla. */
    fusionarActuacionEnLista: (row: IActuacionListItem) => void;
}

/**
 * Hook para cargar actuaciones con filtros.
 * 
 * NO carga automáticamente - solo cuando se llama a `buscar()`
 * 
 * @returns Estado de actuaciones, metadata, loading y función buscar
 */
export const useActuacionesFiltradas = (): UseActuacionesFiltradas => {
    const [actuaciones, setActuaciones] = useState<IActuacionListItem[]>([]);
    const [meta, setMeta] = useState<IActuacionesListMeta | null>(null);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [hasSearched, setHasSearched] = useState(false);

    const buscar = useCallback(async (filters: IActuacionesListFilters) => {
        setLoading(true);
        setError(null);
        setHasSearched(true);
        try {
            const response = await getActuacionesFiltered(filters);
            setActuaciones(response.items);
            setMeta(response.meta);
            if (filters?.orden_trabajo && response.items.length === 0) {
                setError(`No se encontró la Orden de Trabajo: ${filters.orden_trabajo}`);
            }
        } catch (err: any) {
            console.error("Error al cargar actuaciones:", err);
            setError(err?.response?.data?.detail || "Error al cargar actuaciones");
            setActuaciones([]);
            setMeta(null);
        } finally {
            setLoading(false);
        }
    }, []);

    const fusionarActuacionEnLista = useCallback((row: IActuacionListItem) => {
        const rid = Number(row.id);
        setActuaciones((prev) =>
            prev.map((item) => (Number(item.id) === rid ? { ...item, ...row } : item))
        );
    }, []);

    return {
        actuaciones,
        meta,
        loading,
        error,
        hasSearched,
        buscar,
        fusionarActuacionEnLista,
    };
};
