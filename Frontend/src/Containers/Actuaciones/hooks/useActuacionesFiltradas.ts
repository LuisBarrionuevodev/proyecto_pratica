import { useState, useCallback, useRef } from "react";
import type {
    IActuacionListItem,
    IActuacionesListMeta,
    IActuacionesListFilters,
} from "../../../api/actuacionesListApi";
import { getActuacionesFiltered } from "../../../api/actuacionesListApi";

const DEFAULT_PAGE_SIZE = 50;

interface UseActuacionesFiltradas {
    actuaciones: IActuacionListItem[];
    meta: IActuacionesListMeta | null;
    loading: boolean;
    error: string | null;
    hasSearched: boolean;
    buscar: (filters: IActuacionesListFilters) => Promise<void>;
    /** Repite la última consulta (misma página y filtros); útil tras editar sin perder contexto. */
    refrescarUltimaBusqueda: () => Promise<void>;
    /** Limpia resultados y bandera de búsqueda (p. ej. «Limpiar» filtros sin dejar meta vieja). */
    limpiarLista: () => void;
    /** Fusiona una fila devuelta por el servidor (p. ej. POST quitar-acta) sin disparar `loading` ni remontar la grilla. */
    fusionarActuacionEnLista: (row: IActuacionListItem) => void;
}

/**
 * Hook para cargar actuaciones con filtros y paginación servidor.
 */
export const useActuacionesFiltradas = (): UseActuacionesFiltradas => {
    const [actuaciones, setActuaciones] = useState<IActuacionListItem[]>([]);
    const [meta, setMeta] = useState<IActuacionesListMeta | null>(null);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [hasSearched, setHasSearched] = useState(false);
    const lastFiltersRef = useRef<IActuacionesListFilters>({
        page: 1,
        page_size: DEFAULT_PAGE_SIZE,
    });

    const buscar = useCallback(async (filters: IActuacionesListFilters) => {
        const merged: IActuacionesListFilters = {
            page: 1,
            page_size: DEFAULT_PAGE_SIZE,
            ...filters,
        };
        lastFiltersRef.current = merged;
        setLoading(true);
        setError(null);
        setHasSearched(true);
        try {
            const response = await getActuacionesFiltered(merged);
            setActuaciones(response.items);
            setMeta(response.meta);
            const specificLookup = Boolean(filters?.q || filters?.actuacion_id);
            if (
                specificLookup &&
                response.items.length === 0 &&
                response.meta.total === 0
            ) {
                const term = filters?.q?.trim() || `id ${filters?.actuacion_id}`;
                setError(`Sin actuaciones para «${term}». Probá otro texto o ampliá el criterio.`);
            } else if (
                filters?.orden_trabajo &&
                response.items.length === 0 &&
                response.meta.total === 0
            ) {
                setError(`Sin actuaciones para la OT ${filters.orden_trabajo}.`);
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

    const refrescarUltimaBusqueda = useCallback(async () => {
        await buscar(lastFiltersRef.current);
    }, [buscar]);

    const limpiarLista = useCallback(() => {
        setActuaciones([]);
        setMeta(null);
        setHasSearched(false);
        setError(null);
        lastFiltersRef.current = { page: 1, page_size: DEFAULT_PAGE_SIZE };
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
        refrescarUltimaBusqueda,
        limpiarLista,
        fusionarActuacionEnLista,
    };
};
