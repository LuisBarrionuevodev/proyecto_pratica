import { GridColumnIcon } from "@glideapps/glide-data-grid";
import { COLORS } from "../../CargarActuaciones/styles/cargarActuacionesStyles";

export const GROUP_CONFIG = {
  Relevamiento: { icon: GridColumnIcon.HeaderArray, color: COLORS.grayDark },
};

/** Ancho mínimo para mostrar "Orientación" en header (sin reducir font). */
export const RELEVAMIENTO_ANGULO_ESQUINA_COL_WIDTH = 128;

/** Tooltips de ayuda para columnas de domicilio (header id → texto). */
export const RELEVAMIENTO_COLUMN_HEADER_TOOLTIPS: Partial<Record<string, string>> = {
  Numero:
    "Para una dirección normal ingresá la altura. Para una esquina, ingresá la segunda calle.",
  "Ángulo esquina": "Ubicación del local en la esquina: NE, NO, SE o SO.",
};

export const COLUMN_DEFINITIONS = [
  { id: "Relevador", title: "Relevador", width: 168, editable: true, group: "Relevamiento", cellType: "dropdown" },
  { id: "Calle", title: "Calle", width: 168, editable: true, group: "Relevamiento", cellType: "text" },
  { id: "Numero", title: "Número / esquina", width: 132, editable: true, group: "Relevamiento", cellType: "text" },
  { id: "Rubro", title: "Rubro", width: 156, editable: true, group: "Relevamiento", cellType: "dropdown" },
  { id: "Nombre fantasía", title: "Nombre fantasía", width: 168, editable: true, group: "Relevamiento", cellType: "text" },
  {
    id: "Ángulo esquina",
    title: "Orientación",
    width: RELEVAMIENTO_ANGULO_ESQUINA_COL_WIDTH,
    editable: true,
    group: "Relevamiento",
    cellType: "dropdown",
  },
  { id: "Turno", title: "Turno", width: 104, editable: true, group: "Relevamiento", cellType: "dropdown" },
  { id: "Está abierto", title: "Está abierto", width: 118, editable: true, group: "Relevamiento", cellType: "dropdown" },
];
