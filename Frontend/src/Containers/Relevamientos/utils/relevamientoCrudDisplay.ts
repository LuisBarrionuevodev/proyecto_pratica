import type { IRelevamientoListItem } from "../../../api/relevamientosListApi";
import { turnoCargaLabel } from "../../CargarRelevamientos/config/relevamientoTurnOptions";

/** Calle visible en ficha (normalizada si aplica). */
export function relevamientoCalleDisplay(row: IRelevamientoListItem): string | null {
  if (row.calle_estado === "OK" && row.calle_normalizada) {
    return row.calle_normalizada;
  }
  return row.calle;
}

/** Número o esquina visible en ficha. */
export function relevamientoNumeroDisplay(row: IRelevamientoListItem): string | null {
  if (
    row.numero_tipo === "ESQUINA" &&
    (row.numero_esquina || row.esquina_normalizada)
  ) {
    return row.numero_esquina ?? row.esquina_normalizada ?? null;
  }
  return row.numero ?? null;
}

/** Etiqueta Sí/No para «está abierto». */
export function relevamientoEstaAbiertoDisplay(value: IRelevamientoListItem["esta_abierto"]): string {
  if (value === true) return "Sí";
  if (value === false) return "No";
  return "—";
}

/** Turno legible para ficha. */
export function relevamientoTurnoDisplay(turno: string | null | undefined): string {
  return turnoCargaLabel(turno);
}
