/**
 * Funciones auxiliares para la grilla de actuaciones
 */

import type { GridRow } from "../types";

// =============================================================================
// GENERADOR DE IDs ÚNICOS
// =============================================================================

/** Contador interno para IDs únicos */
let rowIdCounter = 0;

/**
 * Genera un ID único para una fila
 * Formato: row_<timestamp>_<counter>
 */
export function generateRowId(): string {
    return `row_${Date.now()}_${rowIdCounter++}`;
}

/**
 * Resetea el contador de IDs (útil para tests)
 */
export function resetRowIdCounter(): void {
    rowIdCounter = 0;
}

// =============================================================================
// EXTRACCIÓN DE DATOS
// =============================================================================

/**
 * Extrae solo las columnas de datos de una fila (sin metadatos internos)
 * Elimina: _rowId, _state, _cellErrors, _rowError, _normalized, _validation_history
 */
export function extractDataColumns(row: GridRow): GridRow {
    const { 
        _rowId, 
        _state, 
        _cellErrors, 
        _rowError, 
        _normalized, 
        _validation_history, 
        ...dataColumns 
    } = row;
    return dataColumns;
}

// =============================================================================
// CREACIÓN DE FILAS
// =============================================================================

/**
 * Crea una nueva fila vacía con estado PENDIENTE
 */
export function createEmptyRow(): GridRow {
    return {
        _rowId: generateRowId(),
        _state: "PENDIENTE",
        _cellErrors: {},
    };
}

/**
 * Crea múltiples filas vacías
 */
export function createEmptyRows(count: number): GridRow[] {
    return Array.from({ length: count }, () => createEmptyRow());
}

// =============================================================================
// CONTADORES
// =============================================================================

/**
 * Cuenta filas por estado
 */
export function countRowsByState(rows: GridRow[]): {
    ok: number;
    error: number;
    pending: number;
    total: number;
} {
    const ok = rows.filter(r => r._state === "OK").length;
    const error = rows.filter(r => r._state === "ERROR").length;
    const pending = rows.filter(r => r._state === "PENDIENTE").length;
    
    return {
        ok,
        error,
        pending,
        total: rows.length,
    };
}

// =============================================================================
// PARSEO DE VALORES
// =============================================================================

/**
 * Parsea el valor de una fecha para mostrar
 */
export function parseDateValue(value: unknown): { date: Date | null; display: string } {
    if (!value) {
        return { date: null, display: "" };
    }

    try {
        const dateValue = new Date(value as string);
        if (!isNaN(dateValue.getTime())) {
            return {
                date: dateValue,
                display: dateValue.toISOString().split('T')[0],
            };
        }
    } catch {
        // Ignorar error de parseo
    }

    return { date: null, display: String(value) };
}

/**
 * Formatea una fecha Date a string ISO (YYYY-MM-DD)
 */
export function formatDateToISO(date: Date | null | undefined): string | null {
    if (!date || isNaN(date.getTime())) {
        return null;
    }
    return date.toISOString().split('T')[0];
}
