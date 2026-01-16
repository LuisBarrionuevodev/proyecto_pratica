/**
 * Opciones de dropdowns para la grilla de actuaciones
 * Enums alineados con el backend
 */

// =============================================================================
// TIPOS DE ACTUACIÓN
// =============================================================================

export const TIPO_ACTUACION_OPTIONS = [
    "INSPECCION",
    "REINSPECCION",
    "RATIFICACION DE CLAUSURA",
    "RATIFICACION DE DECOMISO",
    "VERIFICAR E INFORMAR",
    "TRANSPORTE",
] as const;

// =============================================================================
// TIPOS DE CONTRAPRODUCENCIA
// =============================================================================

export const CONTRAPRODUCENCIA_OPTIONS = [
    "LOCAL CERRADO",
    "NO EXISTE/NO ES EL RUBRO",
    "CLIMA",
    "ZONA ROJA",
    "NO_HUBO",
    "OTROS",
] as const;

// =============================================================================
// MOTIVOS DE COMPROBACIÓN
// =============================================================================

export const COMPROBACION_MOTIVOS = [
    "Falta de Higiene",
    "Condiciones Edilicias Inadecuadas",
    "No Permite la Inspección",
    "Incumplimiento",
    "Incumplimiento de Notificación",
    "Sin Certificado de Desinfección",
    "Sin Carnet de Sanidad",
    "Sin Certificado de Sanidad",
    "Mercadería Vencida",
    "Productos Sin Rotulación",
] as const;

// =============================================================================
// MAPA DE ENUMS POR COLUMNA
// =============================================================================

/** Mapea columnas a sus opciones de dropdown fijas */
export const DROPDOWN_ENUMS: Record<string, readonly string[]> = {
    "Tipo actuación": TIPO_ACTUACION_OPTIONS,
    "Contraproducencia": CONTRAPRODUCENCIA_OPTIONS,
    "Motivo comprobación": COMPROBACION_MOTIVOS,
};

// =============================================================================
// HELPERS
// =============================================================================

/**
 * Obtiene las opciones de dropdown para una columna
 * @param columnId - ID de la columna
 * @param catalogs - Catálogos del backend (inspectores, motivos, rubros)
 * @returns Array de opciones para el dropdown
 */
export function getDropdownOptions(
    columnId: string,
    catalogs: {
        inspectores: string[];
        motivos: string[];
        rubros: string[];
    }
): string[] {
    // Primero verificar enums fijos
    const enumOptions = DROPDOWN_ENUMS[columnId];
    if (enumOptions) {
        return [...enumOptions];
    }

    // Luego verificar catálogos del backend
    if (columnId.startsWith("Inspector")) {
        return catalogs.inspectores;
    }
    if (columnId.startsWith("Motivo notif")) {
        return catalogs.motivos;
    }
    if (columnId === "Rubro") {
        return catalogs.rubros;
    }

    return [];
}
