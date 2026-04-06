import type { IRutaIniciadorPendienteRow } from "../../../../api/rutasTrabajoApi";

/** Etiqueta corta de tipo para badges (misma línea que backend `badges.tipo_label` pero más compacta). */
const TIPO_CORTO: Record<string, string> = {
  RELEVAMIENTO: "RELEVAMIENTO",
  DENUNCIA: "DENUNCIA",
  REINSPECCION_NOTIFICACION: "REINSPECCIÓN NOTIF.",
  REINSPECCION_OFICIO: "REINSPECCIÓN OFICIO",
  VERIFICAR_INFORMAR_OFICIO: "VERIFICAR / INFORMAR",
  RATIFICACION_CLAUSURA_OFICIO: "RATIF. CLAUSURA",
  RATIFICACION_DECOMISO_OFICIO: "RATIF. DECOMISO",
};

/**
 * Texto principal del pendiente: domicilio compuesto o fallback.
 */
export function lineaPrincipalPendiente(row: IRutaIniciadorPendienteRow): string {
  const t = row.domicilio_texto?.trim();
  if (t) return t;
  const c = row.domicilio?.calle;
  const n = row.domicilio?.numero;
  if (c || n) return [c, n].filter(Boolean).join(" ");
  return "—";
}

/**
 * Subtítulo rubro · fecha (solo segmentos presentes).
 */
export function subtituloRubroFecha(row: IRutaIniciadorPendienteRow): string | null {
  const rubro = row.rubro_nombre ?? row.domicilio?.rubro ?? "";
  const fecha = row.fecha_origen ?? "";
  const parts: string[] = [];
  if (rubro.trim()) parts.push(rubro.trim());
  if (fecha) parts.push(fecha);
  return parts.length ? parts.join(" · ") : null;
}

export function etiquetaTipoCorta(row: IRutaIniciadorPendienteRow): string {
  const key = row.tipo_iniciador ?? "";
  if (TIPO_CORTO[key]) return TIPO_CORTO[key];
  return key.replace(/_/g, " ");
}

export type PrioridadCat = "BAJA" | "MEDIA" | "ALTA";

export function prioridadCategoriaRow(row: IRutaIniciadorPendienteRow): PrioridadCat {
  const p = row.prioridad_categoria;
  if (p === "BAJA" || p === "MEDIA" || p === "ALTA") return p;
  const n = row.prioridad ?? 1;
  if (n <= 1) return "BAJA";
  if (n === 2) return "MEDIA";
  return "ALTA";
}

/**
 * Abre búsqueda en OpenStreetMap con el texto de domicilio (sin coords en el row del pendiente).
 */
export function abrirUbicacionEnMapaExterno(row: IRutaIniciadorPendienteRow): void {
  const q = lineaPrincipalPendiente(row);
  if (q === "—") return;
  const url = `https://www.openstreetmap.org/search?query=${encodeURIComponent(q)}`;
  window.open(url, "_blank", "noopener,noreferrer");
}
