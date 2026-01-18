/**
 * Funciones auxiliares para la grilla de CargarActuaciones
 */
import type { GridRow } from "../../../api/gridApi";

// =============================================================================
// GENERADOR DE IDs ÚNICOS
// =============================================================================
const generateRowIdCounter = { value: 0 };

export const generateRowId = (): string => {
    return `row_${Date.now()}_${generateRowIdCounter.value++}`;
};

// =============================================================================
// HELPERS PARA FILAS
// =============================================================================

/**
 * Extrae solo las columnas de datos de una fila (sin metadatos internos)
 */
export const extractDataColumns = (row: GridRow): Partial<GridRow> => {
    const { _rowId, _state, _cellErrors, _rowError, _normalized, _validation_history, _touched, ...dataColumns } = row as any;
    return dataColumns;
};

/**
 * Verifica si una fila tiene datos cargados (ha sido tocada)
 * Una fila se considera "tocada" si tiene algún valor en sus columnas de datos
 */
export const rowHasData = (row: GridRow): boolean => {
    // Si tiene flag _touched explícito, usar eso
    if ((row as any)._touched) return true;
    
    // Verificar si hay algún valor en las columnas de datos
    const dataColumns = extractDataColumns(row);
    return Object.values(dataColumns).some(value => 
        value !== null && value !== undefined && value !== ""
    );
};

/**
 * Crea una nueva fila vacía con los valores por defecto
 */
export const createEmptyRow = (): GridRow => ({
    _rowId: generateRowId(),
    _state: "PENDIENTE",
    _cellErrors: {},
} as GridRow);

/**
 * Crea múltiples filas vacías
 */
export const createEmptyRows = (count: number): GridRow[] => {
    return Array.from({ length: count }, () => createEmptyRow());
};

// =============================================================================
// HELPERS PARA FECHAS
// =============================================================================

/**
 * Parsea un valor de fecha y retorna un objeto Date o null
 */
export const parseDateValue = (value: any): { date: Date | null; displayDate: string } => {
    if (!value) {
        return { date: null, displayDate: "" };
    }

    try {
        const dateValue = new Date(value as string);
        if (!isNaN(dateValue.getTime())) {
            return {
                date: dateValue,
                displayDate: dateValue.toISOString().split('T')[0],
            };
        }
    } catch {
        // Ignorar errores de parseo
    }

    return { date: null, displayDate: value.toString() };
};

/**
 * Formatea una fecha para enviar al backend
 */
export const formatDateToISO = (date: Date | null): string | null => {
    if (!date || isNaN(date.getTime())) return null;
    return date.toISOString().split('T')[0];
};
