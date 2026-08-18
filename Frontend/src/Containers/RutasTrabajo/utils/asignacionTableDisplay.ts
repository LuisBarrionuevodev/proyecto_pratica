import type { IRutaIniciadorPendienteRow } from "../../../api/rutasTrabajoApi";
import {
  distritoNombrePendiente,
  lineaPrincipalPendiente,
  rubroLineaPendiente,
} from "../planificacion/utils/iniciadorDisplay";
import { tipoLabelOperativo } from "./iniciadorDetalleOperativo";

export const ASIGNACION_COL_TIPO_PRIORIDAD = "Tipo / prioridad";
export const ASIGNACION_COL_DETALLE_OPERATIVO = "Detalle operativo";
export const ASIGNACION_COL_DOMICILIO_RUBRO = "Domicilio / rubro";

const PRIORIDAD_CHIP = {
  alta: { label: "Alta", color: "#ffd9a2", bg: "rgba(184,120,34,0.30)" },
  media: { label: "Media", color: "#c8dcff", bg: "rgba(58,103,182,0.30)" },
  baja: { label: "Baja", color: "#bdf2d7", bg: "rgba(28,115,80,0.30)" },
} as const;

export type PrioridadChipStyle = { label: string; color: string; bg: string };

function chipFromCategoria(cat: "BAJA" | "MEDIA" | "ALTA"): PrioridadChipStyle {
  if (cat === "ALTA") return PRIORIDAD_CHIP.alta;
  if (cat === "MEDIA") return PRIORIDAD_CHIP.media;
  return PRIORIDAD_CHIP.baja;
}

function chipFromNumero(p: number): PrioridadChipStyle | null {
  if (p >= 3) return PRIORIDAD_CHIP.alta;
  if (p === 2) return PRIORIDAD_CHIP.media;
  if (p <= 1) return PRIORIDAD_CHIP.baja;
  return null;
}

/** Etiqueta y estilo de prioridad sin inventar valores cuando no hay dato real. */
export function prioridadDisplayOperativo(row: IRutaIniciadorPendienteRow): PrioridadChipStyle | null {
  const labelDirecto = row.prioridad_label?.trim();
  if (labelDirecto) {
    const cat = row.prioridad_categoria;
    if (cat === "BAJA" || cat === "MEDIA" || cat === "ALTA") {
      return { ...chipFromCategoria(cat), label: labelDirecto };
    }
    const inferred = chipFromNumero(row.prioridad ?? NaN);
    return inferred ? { ...inferred, label: labelDirecto } : { label: labelDirecto, ...PRIORIDAD_CHIP.media };
  }

  const cat = row.prioridad_categoria;
  if (cat === "BAJA" || cat === "MEDIA" || cat === "ALTA") {
    return chipFromCategoria(cat);
  }

  const p = row.prioridad;
  if (p === null || p === undefined) return null;
  return chipFromNumero(p);
}

/** Domicilio normalizado para columna compacta (incluye distrito si está disponible). */
export function domicilioLineaAsignacion(row: IRutaIniciadorPendienteRow): string {
  const base = lineaPrincipalPendiente(row);
  const distrito = distritoNombrePendiente(row);
  if (base === "—") return "—";
  if (distrito !== "—") return `${base} · ${distrito}`;
  return base;
}

/** Rubro para segunda línea de la columna domicilio/rubro. */
export function rubroLineaAsignacion(row: IRutaIniciadorPendienteRow): string | null {
  const rubro = rubroLineaPendiente(row);
  return rubro !== "—" ? rubro : null;
}

export { tipoLabelOperativo };
