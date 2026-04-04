/**
 * Opciones de dropdowns para la grilla de CargarActuaciones
 * NOTA: Se incluye opción vacía al inicio para permitir borrar la selección
 */

// =============================================================================
// Catálogos dinámicos (desde backend)
// =============================================================================

/**
 * Obtiene las opciones para un dropdown según la columna
 * @param columnId - ID de la columna
 * @param catalogs - Catálogos cargados desde el backend
 * @returns Array de opciones (siempre incluye opción vacía al inicio)
 */
export const getDropdownOptions = (
    columnId: string,
    catalogs: {
        inspectores: string[];
        motivos: string[];
        rubros: string[];
        tipos: string[];
        contraproducencias: string[];
        motivosComprobacion: string[];
    }
): string[] => {
    // Detectar tipo de columna
    const isInspector = columnId.startsWith("Inspector");
    const isMotivoNotif = columnId.startsWith("Motivo notif");
    const isMotivoComprobacion = columnId === "Motivo comprobación";
    const isRubro = columnId === "Rubro";
    const isTipoActuacion = columnId === "Tipo actuación";
    const isContraproducencia = columnId === "Contraproducencia";

    // Retornar opciones del catálogo con opción vacía al inicio
    if (isMotivoComprobacion) {
        return ["", ...catalogs.motivosComprobacion];
    }
    if (isInspector) {
        return ["", ...catalogs.inspectores];
    }
    if (isMotivoNotif) {
        return ["", ...catalogs.motivos];
    }
    if (isRubro) {
        return ["", ...catalogs.rubros];
    }
    if (isTipoActuacion) {
        return ["", ...catalogs.tipos];
    }
    if (isContraproducencia) {
        return ["", ...catalogs.contraproducencias];
    }

    if (columnId === "Turno") {
        return ["", "MANIANA", "TARDE"];
    }
    if (columnId === "Está abierto") {
        return ["", "Sí", "No"];
    }

    return [""];
};
