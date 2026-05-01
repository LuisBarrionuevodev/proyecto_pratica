import { GridColumnIcon } from "@glideapps/glide-data-grid";
import { COLORS } from "../../CargarActuaciones/styles/cargarActuacionesStyles";

export const GROUP_CONFIG = {
  Relevamiento: { icon: GridColumnIcon.HeaderArray, color: COLORS.grayDark },
};

export const COLUMN_DEFINITIONS = [
  /** Misma celda custom `date-picker-cell` que Cargar actas (teclado + calendario); valor interno ISO. */
  { id: "Fecha", title: "Fecha", width: 150, editable: true, group: "Relevamiento", icon: GridColumnIcon.HeaderDate, cellType: "date" },
  { id: "Inspector", title: "Inspector", width: 168, editable: true, group: "Relevamiento", icon: GridColumnIcon.HeaderString, cellType: "dropdown" },
  { id: "Calle", title: "Calle", width: 168, editable: true, group: "Relevamiento", icon: GridColumnIcon.HeaderString, cellType: "text" },
  { id: "Numero", title: "Numero", width: 96, editable: true, group: "Relevamiento", icon: GridColumnIcon.HeaderNumber, cellType: "text" },
  { id: "Rubro", title: "Rubro", width: 156, editable: true, group: "Relevamiento", icon: GridColumnIcon.HeaderString, cellType: "dropdown" },
  { id: "Turno", title: "Turno", width: 104, editable: true, group: "Relevamiento", icon: GridColumnIcon.HeaderString, cellType: "dropdown" },
  { id: "Está abierto", title: "Está abierto", width: 118, editable: true, group: "Relevamiento", icon: GridColumnIcon.HeaderString, cellType: "dropdown" },
];
