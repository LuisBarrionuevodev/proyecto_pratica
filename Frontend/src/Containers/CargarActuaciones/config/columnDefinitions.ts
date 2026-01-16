/**
 * Definiciones de columnas para la grilla de actuaciones
 * Organizadas por dominios funcionales
 */

import { GridColumnIcon, type GridColumn } from "@glideapps/glide-data-grid";
import type { ColumnDefinition } from "../types";
import { COLORS } from "../styles/cargarActuacionesStyles";
import { getGroupConfig } from "./groupConfig";

// =============================================================================
// DEFINICIÓN DE COLUMNAS
// Estructura de la grilla organizada por dominios funcionales
// =============================================================================

export const COLUMN_DEFINITIONS: ColumnDefinition[] = [
    // =========================================================================
    // Grupo: Actuación - Datos principales de la actuación
    // =========================================================================
    { 
        id: "_rowError", 
        title: "Errores fila", 
        width: 220, 
        editable: false, 
        group: "Actuación", 
        icon: GridColumnIcon.HeaderString, 
        cellType: "rowError" 
    },
    { 
        id: "Fecha actuación", 
        title: "Fecha actuación", 
        width: 130, 
        editable: true, 
        group: "Actuación", 
        icon: GridColumnIcon.HeaderDate, 
        cellType: "date" 
    },
    { 
        id: "Tipo actuación", 
        title: "Tipo actuación", 
        width: 140, 
        editable: true, 
        group: "Actuación", 
        icon: GridColumnIcon.HeaderString, 
        cellType: "dropdown" 
    },
    { 
        id: "Contraproducencia", 
        title: "Contraproducencia", 
        width: 140, 
        editable: true, 
        group: "Actuación", 
        icon: GridColumnIcon.HeaderString, 
        cellType: "dropdown" 
    },
    { 
        id: "Orden de trabajo", 
        title: "Orden de trabajo", 
        width: 130, 
        editable: true, 
        group: "Actuación", 
        icon: GridColumnIcon.HeaderNumber, 
        cellType: "text" 
    },
    
    // =========================================================================
    // Grupo: Inspectores - Personal asignado
    // =========================================================================
    { 
        id: "Inspector 1", 
        title: "Inspector 1", 
        width: 130, 
        editable: true, 
        group: "Inspectores", 
        icon: GridColumnIcon.HeaderString, 
        cellType: "dropdown" 
    },
    { 
        id: "Inspector 2", 
        title: "Inspector 2", 
        width: 130, 
        editable: true, 
        group: "Inspectores", 
        icon: GridColumnIcon.HeaderString, 
        cellType: "dropdown" 
    },
    { 
        id: "Inspector 3", 
        title: "Inspector 3", 
        width: 130, 
        editable: true, 
        group: "Inspectores", 
        icon: GridColumnIcon.HeaderString, 
        cellType: "dropdown" 
    },
    
    // =========================================================================
    // Grupo: Establecimiento - Datos del lugar y contribuyente
    // =========================================================================
    { 
        id: "Calle", 
        title: "Calle", 
        width: 180, 
        editable: true, 
        group: "Establecimiento", 
        icon: GridColumnIcon.HeaderString, 
        cellType: "text" 
    },
    { 
        id: "Número", 
        title: "Número", 
        width: 80, 
        editable: true, 
        group: "Establecimiento", 
        icon: GridColumnIcon.HeaderNumber, 
        cellType: "text" 
    },
    { 
        id: "Rubro", 
        title: "Rubro", 
        width: 130, 
        editable: true, 
        group: "Establecimiento", 
        icon: GridColumnIcon.HeaderString, 
        cellType: "dropdown" 
    },
    { 
        id: "Apellido", 
        title: "Apellido", 
        width: 130, 
        editable: true, 
        group: "Establecimiento", 
        icon: GridColumnIcon.HeaderString, 
        cellType: "text" 
    },
    { 
        id: "Nombre", 
        title: "Nombre", 
        width: 130, 
        editable: true, 
        group: "Establecimiento", 
        icon: GridColumnIcon.HeaderString, 
        cellType: "text" 
    },
    { 
        id: "DNI", 
        title: "DNI", 
        width: 100, 
        editable: true, 
        group: "Establecimiento", 
        icon: GridColumnIcon.HeaderNumber, 
        cellType: "text" 
    },
    
    // =========================================================================
    // Grupo: Actas - Documentos generados
    // =========================================================================
    { 
        id: "Acta inspección", 
        title: "Acta inspección", 
        width: 120, 
        editable: true, 
        group: "Actas", 
        icon: GridColumnIcon.HeaderNumber, 
        cellType: "text" 
    },
    { 
        id: "Acta notificación", 
        title: "Acta notificación", 
        width: 130, 
        editable: true, 
        group: "Actas", 
        icon: GridColumnIcon.HeaderNumber, 
        cellType: "text" 
    },
    { 
        id: "Motivo notif 1", 
        title: "Motivo notif 1", 
        width: 130, 
        editable: true, 
        group: "Actas", 
        icon: GridColumnIcon.HeaderString, 
        cellType: "dropdown" 
    },
    { 
        id: "Motivo notif 2", 
        title: "Motivo notif 2", 
        width: 130, 
        editable: true, 
        group: "Actas", 
        icon: GridColumnIcon.HeaderString, 
        cellType: "dropdown" 
    },
    { 
        id: "Motivo notif 3", 
        title: "Motivo notif 3", 
        width: 130, 
        editable: true, 
        group: "Actas", 
        icon: GridColumnIcon.HeaderString, 
        cellType: "dropdown" 
    },
    { 
        id: "Acta comprobación", 
        title: "Acta comprobación", 
        width: 130, 
        editable: true, 
        group: "Actas", 
        icon: GridColumnIcon.HeaderNumber, 
        cellType: "text" 
    },
    { 
        id: "Motivo comprobación", 
        title: "Motivo comprobación", 
        width: 150, 
        editable: true, 
        group: "Actas", 
        icon: GridColumnIcon.HeaderString, 
        cellType: "dropdown" 
    },
    { 
        id: "Acta clausura", 
        title: "Acta clausura", 
        width: 120, 
        editable: true, 
        group: "Actas", 
        icon: GridColumnIcon.HeaderNumber, 
        cellType: "text" 
    },
    { 
        id: "Acta decomiso", 
        title: "Acta decomiso", 
        width: 120, 
        editable: true, 
        group: "Actas", 
        icon: GridColumnIcon.HeaderNumber, 
        cellType: "text" 
    },
    { 
        id: "Kilos decomiso", 
        title: "Kilos decomiso", 
        width: 110, 
        editable: true, 
        group: "Actas", 
        icon: GridColumnIcon.HeaderNumber, 
        cellType: "text" 
    },
    
    // =========================================================================
    // Grupo: Reinspección - Referencia a actas previas
    // =========================================================================
    { 
        id: "Acta notificación previa", 
        title: "Acta notif. previa", 
        width: 140, 
        editable: true, 
        group: "Reinspección", 
        icon: GridColumnIcon.HeaderReference, 
        cellType: "text" 
    },
    
    // =========================================================================
    // Grupo: Expediente - Datos administrativos
    // =========================================================================
    { 
        id: "Acta comprobación previa", 
        title: "Acta comp. previa", 
        width: 140, 
        editable: true, 
        group: "Expediente", 
        icon: GridColumnIcon.HeaderNumber, 
        cellType: "text" 
    },
    { 
        id: "Expediente año", 
        title: "Exp. año", 
        width: 90, 
        editable: true, 
        group: "Expediente", 
        icon: GridColumnIcon.HeaderDate, 
        cellType: "text" 
    },
    { 
        id: "Expediente número", 
        title: "Exp. número", 
        width: 110, 
        editable: true, 
        group: "Expediente", 
        icon: GridColumnIcon.HeaderNumber, 
        cellType: "text" 
    },
    { 
        id: "Oficio año", 
        title: "Oficio año", 
        width: 90, 
        editable: true, 
        group: "Expediente", 
        icon: GridColumnIcon.HeaderDate, 
        cellType: "text" 
    },
    { 
        id: "Oficio número", 
        title: "Oficio número", 
        width: 110, 
        editable: true, 
        group: "Expediente", 
        icon: GridColumnIcon.HeaderNumber, 
        cellType: "text" 
    },
    { 
        id: "Oficio causa", 
        title: "Oficio causa", 
        width: 100, 
        editable: true, 
        group: "Expediente", 
        icon: GridColumnIcon.HeaderString, 
        cellType: "text" 
    },
];

// =============================================================================
// HELPERS
// =============================================================================

/**
 * Convierte las definiciones de columnas al formato de Glide Data Grid
 * Aplica estilos Neo-Brutalistas por grupo
 * Headers oscuros (#2B2E34) con texto blanco
 */
export function getGridColumns(): GridColumn[] {
    return COLUMN_DEFINITIONS.map((col) => {
        const groupConfig = getGroupConfig(col.group);
        return {
            title: col.title,
            id: col.id,
            width: col.width,
            group: col.group,
            icon: col.icon,
            // Override de tema - Headers oscuros con texto blanco
            themeOverride: groupConfig ? {
                bgHeader: groupConfig.color,           // #2B2E34
                bgHeaderHovered: "#3a3d44",            // Ligeramente más claro al hover
                textHeader: COLORS.white,              // Texto blanco
            } : undefined,
        };
    });
}

/**
 * Obtiene una columna por su índice
 */
export function getColumnByIndex(index: number): ColumnDefinition | undefined {
    return COLUMN_DEFINITIONS[index];
}

/**
 * Obtiene una columna por su ID
 */
export function getColumnById(id: string): ColumnDefinition | undefined {
    return COLUMN_DEFINITIONS.find(col => col.id === id);
}
