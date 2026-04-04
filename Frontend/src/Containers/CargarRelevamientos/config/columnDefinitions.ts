import { GridColumnIcon } from "@glideapps/glide-data-grid";
import { COLORS } from "../../CargarActuaciones/styles/cargarActuacionesStyles";

export const GROUP_CONFIG = {
  Relevamiento: { icon: GridColumnIcon.HeaderArray, color: COLORS.grayDark },
};

export const COLUMN_DEFINITIONS = [
  { id: "Fecha", title: "Fecha", width: 140, editable: true, group: "Relevamiento", icon: GridColumnIcon.HeaderDate, cellType: "date" },
  { id: "Inspector", title: "Inspector", width: 200, editable: true, group: "Relevamiento", icon: GridColumnIcon.HeaderString, cellType: "dropdown" },
  { id: "Calle", title: "Calle", width: 200, editable: true, group: "Relevamiento", icon: GridColumnIcon.HeaderString, cellType: "text" },
  { id: "Numero", title: "Numero", width: 120, editable: true, group: "Relevamiento", icon: GridColumnIcon.HeaderNumber, cellType: "text" },
  { id: "Rubro", title: "Rubro", width: 200, editable: true, group: "Relevamiento", icon: GridColumnIcon.HeaderString, cellType: "dropdown" },
  { id: "Turno", title: "Turno", width: 130, editable: true, group: "Relevamiento", icon: GridColumnIcon.HeaderString, cellType: "dropdown" },
  { id: "Está abierto", title: "Está abierto", width: 140, editable: true, group: "Relevamiento", icon: GridColumnIcon.HeaderString, cellType: "dropdown" },
];
