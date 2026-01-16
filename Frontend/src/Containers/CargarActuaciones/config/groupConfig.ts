/**
 * Configuración de grupos de columnas para la grilla
 * Define íconos y colores para cada grupo
 */

import { GridColumnIcon } from "@glideapps/glide-data-grid";
import { COLORS } from "../styles/cargarActuacionesStyles";
import type { GroupConfigMap } from "../types";

// =============================================================================
// CONFIGURACIÓN DE GRUPOS DE COLUMNAS
// Cada grupo tiene un ícono y color distintivo (Neo-Brutalista)
// =============================================================================

export const GROUP_CONFIG: GroupConfigMap = {
    "Actuación": {
        icon: GridColumnIcon.HeaderArray,
        color: COLORS.groupBlue,      // Azul pastel
    },
    "Inspectores": {
        icon: GridColumnIcon.HeaderCode,
        color: COLORS.groupPurple,    // Púrpura
    },
    "Establecimiento": {
        icon: GridColumnIcon.HeaderUri,
        color: COLORS.groupOrange,    // Naranja
    },
    "Actas": {
        icon: GridColumnIcon.HeaderString,
        color: COLORS.groupGreen,     // Verde
    },
    "Reinspección": {
        icon: GridColumnIcon.HeaderReference,
        color: COLORS.groupYellow,    // Amarillo
    },
    "Expediente": {
        icon: GridColumnIcon.HeaderMarkdown,
        color: COLORS.groupPink,      // Rosa
    },
};

/**
 * Obtiene la configuración de un grupo por nombre
 */
export function getGroupConfig(groupName: string) {
    return GROUP_CONFIG[groupName] || null;
}

/**
 * Obtiene los detalles del grupo para Glide Data Grid
 */
export function getGroupDetails(groupName: string) {
    const config = GROUP_CONFIG[groupName];
    return config 
        ? { name: groupName, icon: config.icon }
        : { name: groupName };
}
