/**
 * Formato de valores de catálogo / backend para la ficha documental de comprobación.
 * Evita mostrar snake_case, SCREAMING_SNAKE o claves crudas tal cual llegan del API.
 */

const TIPO_EXPEDIENTE_LABEL: Record<string, string> = {
  ENVIO_ACTA: "Envío de acta",
  RESPUESTA_OFICIO: "Respuesta de oficio",
  PRORROGA_NOTIFICACION: "Prórroga de notificación",
  OTRO: "Otro",
};

const CUMPLIMIENTO_OFICIO_LABEL: Record<string, string> = {
  CUMPLE: "Cumple",
  NO_CUMPLE: "No cumple",
};

const ESTADO_INICIADOR_LABEL: Record<string, string> = {
  CUMPLIDO: "Cumplido",
  PENDIENTE: "Pendiente",
};

function esTokenBackend(s: string): boolean {
  return /^[A-Z0-9_]+$/.test(s) && s.length > 1;
}

/** Palabras técnicas en MAYÚSCULAS → título legible (p. ej. REINSPECCION_OFICIO → Reinspeccion oficio). */
export function humanizarTokenBackend(val: unknown): string {
  if (val === null || val === undefined) return "—";
  const s = String(val).trim();
  if (!s) return "—";
  if (!esTokenBackend(s)) return s;
  return s
    .split("_")
    .filter(Boolean)
    .map((w) => w.charAt(0) + w.slice(1).toLowerCase())
    .join(" ");
}

export function humanizarTipoExpediente(val: unknown): string {
  if (val === null || val === undefined) return "—";
  const s = String(val).trim();
  if (!s) return "—";
  return TIPO_EXPEDIENTE_LABEL[s] ?? humanizarTokenBackend(s);
}

export function humanizarCumplimientoOficio(val: unknown): string {
  if (val === null || val === undefined) return "—";
  const s = String(val).trim();
  if (!s) return "—";
  const u = s.toUpperCase();
  return CUMPLIMIENTO_OFICIO_LABEL[u] ?? (esTokenBackend(u) ? humanizarTokenBackend(u) : s);
}

export function humanizarEstadoIniciador(val: unknown): string {
  if (val === null || val === undefined) return "—";
  const s = String(val).trim();
  if (!s) return "—";
  const u = s.toUpperCase();
  return ESTADO_INICIADOR_LABEL[u] ?? (esTokenBackend(u) ? humanizarTokenBackend(u) : s);
}

/** Tipo de actuación u otros códigos en mayúsculas con guiones bajos. */
export function humanizarTipoActuacion(val: unknown): string {
  if (val === null || val === undefined) return "—";
  const s = String(val).trim();
  if (!s) return "—";
  return esTokenBackend(s) ? humanizarTokenBackend(s) : s;
}

const TIPO_VISITA_RECORRIDO: Record<string, string> = {
  "RATIFICACION DE CLAUSURA": "Ratificación de clausura",
  "RATIFICACION DE DECOMISO": "Ratificación de decomiso",
  "VERIFICAR E INFORMAR": "Verificar e informar",
};

/** Catálogo de visita por oficio y tokens REINSPECCION / INSPECCION para recorrido documental. */
export function humanizarTipoVisitaRecorrido(val: unknown): string {
  if (val === null || val === undefined) return "—";
  const s = String(val).trim();
  if (!s) return "—";
  const u = s.toUpperCase().replace(/\s+/g, " ").trim();
  const key = Object.keys(TIPO_VISITA_RECORRIDO).find((k) => k.toUpperCase() === u);
  if (key) return TIPO_VISITA_RECORRIDO[key];
  return humanizarTipoActuacion(s);
}
