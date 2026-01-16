/**
 * Tipos específicos para el módulo CargarActuaciones
 * Define interfaces y tipos para el manejo de datos de la grilla
 */

import type { GridRow } from "../../../../api/gridApi";

// =============================================================================
// ESTADOS DE FILA
// =============================================================================

/** Estados posibles de una fila en la grilla */
export type RowState = "PENDIENTE" | "OK" | "ERROR";

// =============================================================================
// CONFIGURACIÓN DE COLUMNAS
// =============================================================================

/** Tipos de celda disponibles en la grilla */
export type CellType = "text" | "date" | "dropdown" | "rowError";

/** Definición de una columna de la grilla */
export interface ColumnDefinition {
    id: string;
    title: string;
    width: number;
    editable: boolean;
    group: string;
    icon: any;
    cellType: CellType;
}

// =============================================================================
// CONFIGURACIÓN DE GRUPOS
// =============================================================================

/** Configuración visual de un grupo de columnas */
export interface GroupConfig {
    icon: any;
    color: string;
}

/** Mapa de configuración de grupos */
export type GroupConfigMap = Record<string, GroupConfig>;

// =============================================================================
// CATÁLOGOS
// =============================================================================

/** Estado de los catálogos cargados del backend */
export interface CatalogsState {
    inspectores: string[];
    motivos: string[];
    rubros: string[];
    isLoading: boolean;
    error: string | null;
}

// =============================================================================
// BATCH OPERATIONS
// =============================================================================

/** Estado de las operaciones de batch */
export interface BatchState {
    batchId: string | null;
    isLoading: boolean;
    isValidating: boolean;
    isCommitting: boolean;
    error: string | null;
}

/** Contadores de estado de filas */
export interface RowCounters {
    ok: number;
    error: number;
    pending: number;
    total: number;
}

// =============================================================================
// RE-EXPORTACIONES
// =============================================================================

export type { GridRow };
