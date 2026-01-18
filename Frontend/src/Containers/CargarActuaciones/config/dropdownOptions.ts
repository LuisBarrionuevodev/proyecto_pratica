/**
 * Opciones de dropdowns para la grilla de CargarActuaciones
 * NOTA: Se incluye opción vacía al inicio para permitir borrar la selección
 */

// =============================================================================
// ENUMS ESTÁTICOS (definidos en el frontend)
// =============================================================================
export const DROPDOWN_ENUMS: Record<string, string[]> = {
    "Tipo actuación": [
        "", // Opción vacía para poder borrar
        "INSPECCION",
        "REINSPECCION",
        "RATIFICACION DE CLAUSURA",
        "RATIFICACION DE DECOMISO",
        "VERIFICAR E INFORMAR",
        "TRANSPORTE",
    ],
    "Contraproducencia": [
        "", // Opción vacía para poder borrar
        "LOCAL CERRADO",
        "NO EXISTE/NO ES EL RUBRO",
        "CLIMA",
        "ZONA ROJA",
        "NO_HUBO",
        "OTROS",
    ],
};

// =============================================================================
// MOTIVOS DE COMPROBACIÓN (definidos en el frontend)
// =============================================================================
export const COMPROBACION_MOTIVOS = [
    "", // Opción vacía para poder borrar
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
];

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
    }
): string[] => {
    // Primero verificar si es un enum estático
    const enumOptions = DROPDOWN_ENUMS[columnId];
    if (enumOptions && enumOptions.length > 0) {
        return enumOptions;
    }

    // Detectar tipo de columna
    const isInspector = columnId.startsWith("Inspector");
    const isMotivoNotif = columnId.startsWith("Motivo notif");
    const isMotivoComprobacion = columnId === "Motivo comprobación";
    const isRubro = columnId === "Rubro";

    // Retornar opciones del catálogo con opción vacía al inicio
    if (isMotivoComprobacion) {
        return COMPROBACION_MOTIVOS;
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

    return [""];
};
