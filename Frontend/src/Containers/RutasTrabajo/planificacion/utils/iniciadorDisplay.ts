import type { IRutaIniciadorPendienteRow } from "../../../../api/rutasTrabajoApi";

/** Etiquetas de tipo de iniciador (sin enums crudos visibles). */
const TIPO_INICIADOR_LABELS: Record<string, string> = {
  RELEVAMIENTO: "Relevamiento",
  DENUNCIA: "Denuncia",
  REINSPECCION_NOTIFICACION: "Reinspección por notificación",
  REINSPECCION_OFICIO: "Reinspección por oficio",
  VERIFICAR_INFORMAR_OFICIO: "Verificar e informar (oficio)",
  RATIFICACION_CLAUSURA_OFICIO: "Ratificación clausura (oficio)",
  RATIFICACION_DECOMISO_OFICIO: "Ratificación decomiso (oficio)",
};

function humanizarCodigoTipoDesconocido(codigo: string): string {
  return codigo
    .split("_")
    .filter(Boolean)
    .map((w) => w.charAt(0) + w.slice(1).toLowerCase())
    .join(" ");
}

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
 * Rubro operativo para listados (pool / cards / tabla asignación).
 */
export function rubroLineaPendiente(row: IRutaIniciadorPendienteRow): string {
  const r = row.rubro_nombre ?? row.domicilio?.rubro ?? "";
  return r.trim() || "—";
}

/**
 * Nombre de distrito desde fila planificada (top-level o anidado en domicilio).
 */
export function distritoNombrePendiente(row: IRutaIniciadorPendienteRow): string {
  const d = row.distrito_nombre ?? row.domicilio?.distrito_nombre ?? "";
  return d.trim() || "—";
}

/** Fecha de origen si viene del API; `null` si no hay nada que mostrar. */
export function fechaOrigenPendiente(row: IRutaIniciadorPendienteRow): string | null {
  const f = row.fecha_origen?.trim();
  return f || null;
}

/**
 * Subtítulo rubro · fecha (solo segmentos presentes).
 * @deprecated Preferir `rubroLineaPendiente` + `fechaOrigenPendiente` en UI con jerarquía propia.
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
  if (TIPO_INICIADOR_LABELS[key]) return TIPO_INICIADOR_LABELS[key];
  if (!key.trim()) return "—";
  return humanizarCodigoTipoDesconocido(key);
}

/**
 * Humaniza el código `tipo_iniciador` del API (ítem de ruta o pendiente) sin fila completa.
 */
export function tipoIniciadorDesdeCodigoApi(codigo: string | null | undefined): string | null {
  if (codigo == null || !String(codigo).trim()) return null;
  const c = String(codigo).trim();
  if (TIPO_INICIADOR_LABELS[c]) return TIPO_INICIADOR_LABELS[c];
  return humanizarCodigoTipoDesconocido(c);
}

/**
 * Tipo de iniciador para UI desde fila de planificación: prioriza `tipo_iniciador` humanizado; si no hay código, `badges.tipo_label`.
 *
 * @param row — Fila de pendiente; si falta, retorna `null`.
 * @returns Etiqueta corta sin enums crudos, o `null` si no hay tipo en datos.
 */
export function tipoIniciadorEtiquetaOperativa(row: IRutaIniciadorPendienteRow | undefined): string | null {
  if (!row) return null;
  const codigo = row.tipo_iniciador?.trim();
  if (codigo) return tipoIniciadorDesdeCodigoApi(codigo);
  const badge = row.badges?.tipo_label?.trim();
  return badge || null;
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
