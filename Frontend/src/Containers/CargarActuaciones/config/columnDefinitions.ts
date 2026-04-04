/**
 * Definición de columnas para la grilla de CargarActuaciones
 */
import { GridColumnIcon } from "@glideapps/glide-data-grid";
import { COLORS } from "../styles/cargarActuacionesStyles";

// =============================================================================
// CONFIGURACIÓN DE GRUPOS DE COLUMNAS
// =============================================================================
export const GROUP_CONFIG = {
    "Actuación": { icon: GridColumnIcon.HeaderArray, color: COLORS.grayDark },
    "Inspectores": { icon: GridColumnIcon.HeaderCode, color: COLORS.grayDark },
    "Establecimiento": { icon: GridColumnIcon.HeaderUri, color: COLORS.grayDark },
    "Actas": { icon: GridColumnIcon.HeaderString, color: COLORS.grayDark },
};

// =============================================================================
// DEFINICIÓN DE COLUMNAS
// =============================================================================
export const COLUMN_DEFINITIONS = [
    { id: "Fecha actuación", title: "Fecha actuación", width: 150, editable: true, group: "Actuación", icon: GridColumnIcon.HeaderDate, cellType: "date" },
    { id: "Orden de trabajo", title: "Orden de trabajo", width: 150, editable: true, group: "Actuación", icon: GridColumnIcon.HeaderNumber, cellType: "text" },
    { id: "Inspector 1", title: "Inspector 1", width: 150, editable: true, group: "Inspectores", icon: GridColumnIcon.HeaderString, cellType: "dropdown" },
    { id: "Inspector 2", title: "Inspector 2", width: 150, editable: true, group: "Inspectores", icon: GridColumnIcon.HeaderString, cellType: "dropdown" },
    { id: "Inspector 3", title: "Inspector 3", width: 150, editable: true, group: "Inspectores", icon: GridColumnIcon.HeaderString, cellType: "dropdown" },
    { id: "Calle", title: "Calle", width: 200, editable: true, group: "Establecimiento", icon: GridColumnIcon.HeaderString, cellType: "text" },
    { id: "Número", title: "Número", width: 100, editable: true, group: "Establecimiento", icon: GridColumnIcon.HeaderNumber, cellType: "text" },
    { id: "Rubro", title: "Rubro", width: 150, editable: true, group: "Establecimiento", icon: GridColumnIcon.HeaderString, cellType: "dropdown" },
    { id: "Apellido", title: "Apellido", width: 150, editable: true, group: "Establecimiento", icon: GridColumnIcon.HeaderString, cellType: "text" },
    { id: "Nombre", title: "Nombre", width: 150, editable: true, group: "Establecimiento", icon: GridColumnIcon.HeaderString, cellType: "text" },
    { id: "DNI", title: "DNI", width: 120, editable: true, group: "Establecimiento", icon: GridColumnIcon.HeaderNumber, cellType: "text" },
    { id: "Acta inspección", title: "Acta inspección", width: 150, editable: true, group: "Actas", icon: GridColumnIcon.HeaderNumber, cellType: "text" },
    { id: "Acta notificación", title: "Acta notificación", width: 150, editable: true, group: "Actas", icon: GridColumnIcon.HeaderNumber, cellType: "text" },
    { id: "Motivo notif 1", title: "Motivo notif 1", width: 150, editable: true, group: "Actas", icon: GridColumnIcon.HeaderString, cellType: "dropdown" },
    { id: "Motivo notif 2", title: "Motivo notif 2", width: 150, editable: true, group: "Actas", icon: GridColumnIcon.HeaderString, cellType: "dropdown" },
    { id: "Motivo notif 3", title: "Motivo notif 3", width: 150, editable: true, group: "Actas", icon: GridColumnIcon.HeaderString, cellType: "dropdown" },
    { id: "Acta comprobación", title: "Acta comprobación", width: 150, editable: true, group: "Actas", icon: GridColumnIcon.HeaderNumber, cellType: "text" },
    { id: "Motivo comprobación", title: "Motivo comprobación", width: 180, editable: true, group: "Actas", icon: GridColumnIcon.HeaderString, cellType: "dropdown" },
    { id: "Acta clausura", title: "Acta clausura", width: 150, editable: true, group: "Actas", icon: GridColumnIcon.HeaderNumber, cellType: "text" },
    { id: "Acta decomiso", title: "Acta decomiso", width: 150, editable: true, group: "Actas", icon: GridColumnIcon.HeaderNumber, cellType: "text" },
    { id: "Kilos decomiso", title: "Kilos decomiso", width: 120, editable: true, group: "Actas", icon: GridColumnIcon.HeaderNumber, cellType: "text" },
];

// Columnas de datos (excluyendo metadatos)
export const DATA_COLUMN_IDS = COLUMN_DEFINITIONS
    .filter(col => !col.id.startsWith("_"))
    .map(col => col.id);

/** Columnas propias de acta de notificación (se ocultan en foco Comprobación). */
const NOTIFICACION_COLUMN_IDS = new Set([
    "Acta notificación",
    "Motivo notif 1",
    "Motivo notif 2",
    "Motivo notif 3",
]);

/** Columnas propias de acta de comprobación (se ocultan en foco Notificación). */
const COMPROBACION_COLUMN_IDS = new Set(["Acta comprobación", "Motivo comprobación"]);

export type ActaCargaFocus = "notificacion" | "comprobacion" | "todas";

/**
 * Columnas visibles según el foco de carga: misma grilla, menos columnas del otro tipo de acta.
 * `todas`: todas las columnas (notificación y comprobación a la vez).
 * Los datos de fila siguen en memoria al cambiar de foco (sin borrar).
 */
export function getVisibleColumnDefinitions(actaFocus: ActaCargaFocus): typeof COLUMN_DEFINITIONS {
    if (actaFocus === "todas") {
        return COLUMN_DEFINITIONS;
    }
    return COLUMN_DEFINITIONS.filter((col) => {
        if (actaFocus === "notificacion" && COMPROBACION_COLUMN_IDS.has(col.id)) return false;
        if (actaFocus === "comprobacion" && NOTIFICACION_COLUMN_IDS.has(col.id)) return false;
        return true;
    });
}
