/**
 * Hook para cargar catálogos del backend
 * Maneja: inspectores, motivos, rubros
 */

import { useState, useEffect } from "react";
import {
    fetchInspectores,
    fetchMotivos,
    fetchRubros,
} from "../../../api/gridApi";

// =============================================================================
// TIPOS
// =============================================================================

interface CatalogsState {
    inspectores: string[];
    motivos: string[];
    rubros: string[];
    isLoading: boolean;
    error: string | null;
}

// =============================================================================
// HOOK
// =============================================================================

/**
 * Hook para cargar y manejar los catálogos del backend
 * Se ejecuta una vez al montar el componente
 * 
 * @returns Estado de los catálogos y función para recargar
 */
export function useCatalogs() {
    const [catalogs, setCatalogs] = useState<CatalogsState>({
        inspectores: [],
        motivos: [],
        rubros: [],
        isLoading: true,
        error: null,
    });

    // Cargar catálogos al montar
    useEffect(() => {
        loadCatalogs();
    }, []);

    /**
     * Carga todos los catálogos en paralelo
     */
    async function loadCatalogs() {
        setCatalogs(prev => ({ ...prev, isLoading: true, error: null }));

        try {
            const [inspectoresResp, motivosResp, rubrosResp] = await Promise.all([
                fetchInspectores(),
                fetchMotivos(),
                fetchRubros(),
            ]);

            setCatalogs({
                inspectores: inspectoresResp.items.map((i) => i.nombre),
                motivos: motivosResp.items.map((m) => m.nombre),
                rubros: rubrosResp.items.map((r) => r.nombre),
                isLoading: false,
                error: null,
            });

            console.log("✅ Catálogos cargados:", {
                inspectores: inspectoresResp.items.length,
                motivos: motivosResp.items.length,
                rubros: rubrosResp.items.length,
            });
        } catch (error: any) {
            console.error("❌ Error cargando catálogos:", error);
            setCatalogs(prev => ({
                ...prev,
                isLoading: false,
                error: "Error cargando catálogos (inspectores/motivos/rubros).",
            }));
        }
    }

    return {
        ...catalogs,
        reloadCatalogs: loadCatalogs,
    };
}

export default useCatalogs;
