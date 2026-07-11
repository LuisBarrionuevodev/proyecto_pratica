import type { IRelevamientoListItem } from "../../../api/relevamientosListApi";
import { turnoCargaLabel } from "../../CargarRelevamientos/config/relevamientoTurnOptions";
import {
  normalizarNombreFantasiaFrontend,
  relevamientoAnguloEsAplicable,
} from "./relevamientoCamposForm";

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

/** Nombre de fantasía visible (sin null ni vacío). */
export function relevamientoNombreFantasiaDisplay(row: IRelevamientoListItem): string | null {
  return normalizarNombreFantasiaFrontend(row.nombre_fantasia ?? null);
}

/** Ángulo de esquina visible (sin null ni vacío). */
export function relevamientoAnguloEsquinaDisplay(row: IRelevamientoListItem): string | null {
  const ang = (row.angulo_esquina ?? "").trim().toUpperCase();
  if (!ang) return null;
  if (!relevamientoAnguloEsAplicable(row)) return null;
  return ang;
}

/** Etiqueta corta para chip de ángulo en listado. */
export function relevamientoAnguloChipLabel(row: IRelevamientoListItem): string | null {
  const ang = relevamientoAnguloEsquinaDisplay(row);
  return ang ? `Esquina ${ang}` : null;
}

export type RelevamientoEstablecimientoLines = {
  primary: string;
  secondary: string | null;
  anguloChip: string | null;
};

/** Líneas para columna rubro/establecimiento en bandeja. */
export function relevamientoEstablecimientoLines(row: IRelevamientoListItem): RelevamientoEstablecimientoLines {
  const primary = row.rubro?.trim() || "—";
  const bits: string[] = [];
  const nf = relevamientoNombreFantasiaDisplay(row);
  if (nf) bits.push(`Nombre fantasía: ${nf}`);
  const anguloChip = relevamientoAnguloChipLabel(row);
  return {
    primary,
    secondary: bits.length ? bits.join(" · ") : null,
    anguloChip,
  };
}

/** Texto compacto de establecimiento para export o helpers. */
export function relevamientoEstablecimientoDisplay(row: IRelevamientoListItem): string {
  const { primary, secondary, anguloChip } = relevamientoEstablecimientoLines(row);
  const parts = [primary];
  if (secondary) parts.push(secondary);
  if (anguloChip) parts.push(anguloChip);
  return parts.join(" · ");
}
