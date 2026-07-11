import type { IRutaIniciadorPendienteRow, IRutaItemMin } from "../../../../api/rutasTrabajoApi";

/** Campos operativos de establecimiento (relevamiento origen). */
export type EstablecimientoDiscriminadores = {
  nombre_fantasia?: string | null;
  angulo_esquina?: string | null;
};

function trimOrNull(value: string | null | undefined): string | null {
  const t = value?.trim();
  return t || null;
}

/**
 * Línea secundaria opcional para distinguir establecimientos en la misma dirección/esquina.
 * Solo para Ruta de Trabajo; no usar en Completar Trabajo ni actas.
 */
export function buildEstablecimientoSecundario(item: EstablecimientoDiscriminadores): string | null {
  const nf = trimOrNull(item.nombre_fantasia);
  const ang = trimOrNull(item.angulo_esquina);
  const parts: string[] = [];
  if (nf) parts.push(`Nombre fantasía: ${nf}`);
  if (ang) parts.push(`Esquina: ${ang}`);
  return parts.length ? parts.join(" · ") : null;
}

/** Extrae discriminadores desde fila de planificación o ítem de ruta. */
export function establecimientoDiscriminadoresDesdeRow(
  row: IRutaIniciadorPendienteRow | IRutaItemMin | EstablecimientoDiscriminadores
): EstablecimientoDiscriminadores {
  return {
    nombre_fantasia: row.nombre_fantasia ?? null,
    angulo_esquina: row.angulo_esquina ?? null,
  };
}

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

/** Formato operativo `número/año` o solo número. */
export function formatoNumeroConAnio(numero: string | null | undefined, anio?: number | null): string | null {
  const n = numero?.trim();
  if (!n) return null;
  if (anio != null && Number.isFinite(anio)) return `${n}/${anio}`;
  return n;
}

/**
 * Líneas compactas de identificación (oficio, comprobación, notificación) para cards.
 * Solo devuelve entradas con valor; nunca null/undefined en texto.
 */
export function lineasIdentificadoresPendiente(row: IRutaIniciadorPendienteRow): string[] {
  const id = row.identificadores;
  if (!id) return [];

  const lines: string[] = [];
  const oficioTxt = formatoNumeroConAnio(id.numero_oficio, id.anio_oficio);
  if (oficioTxt) lines.push(`Nº oficio: ${oficioTxt}`);

  const compTxt = formatoNumeroConAnio(id.numero_comprobacion, id.anio_comprobacion);
  if (compTxt) lines.push(`Nº comprobación: ${compTxt}`);

  const notiTxt = formatoNumeroConAnio(id.numero_notificacion, id.anio_notificacion);
  if (notiTxt) lines.push(`Nº notificación: ${notiTxt}`);

  const venc = id.fecha_vencimiento_notificacion?.trim();
  if (venc) lines.push(`Vence: ${venc}`);

  const den = id.numero_denuncia?.trim();
  if (den) lines.push(`Nº denuncia: ${den}`);

  return lines;
}
