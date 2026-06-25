/** Etiquetas humanas para errores del modal de actuación. */
export const ACTUACION_FIELD_LABELS: Record<string, string> = {
  orden_trabajo_numero: "OT",
  fecha_actuacion: "Fecha de la visita",
  tipo_actuacion: "Tipo de actuación",
  contraproducencia: "Contraproducencia",
  inspectores: "Inspectores a cargo",
  inspector1: "Inspector 1",
  inspector2: "Inspector 2",
  inspector3: "Inspector 3",
  calle: "Calle",
  numero: "Número o referencia",
  numero_tipo: "Tipo de numeración",
  nombre_local: "Nombre de fantasía",
  rubro_nombre: "Rubro",
  doc_nro: "N.º de documento",
  contrib_apellido: "Apellido",
  contrib_nombre: "Nombre",
  razon_social: "Razón social",
  acta_inspeccion_num: "Acta de inspección",
  acta_notificacion_num: "Acta de notificación",
  notificacion_motivo_1: "Motivo de notificación",
  notificacion_motivo_2: "Motivo de notificación 2",
  notificacion_motivo_3: "Motivo de notificación 3",
  acta_comprobacion_num: "Acta de comprobación",
  comprobacion_motivo: "Motivo de comprobación",
  acta_clausura_num: "Acta de clausura",
  acta_decomiso_num: "Acta de decomiso",
  decomiso_kilos_total: "Kilos decomisados",
  notificacion_previa_num: "Acta notificación previa",
  comprobacion_previa_num: "Acta comprobación previa",
  expediente_numero: "Expediente",
  expediente_anio: "Año expediente",
  oficio_numero: "Número de oficio",
  oficio_anio: "Año de oficio",
  oficio_causa: "Causa de oficio",
  numero_oficio: "Número de oficio",
};

/** Campos documentales del canal actas: no se envían en PUT desde esta pantalla. */
export const ACTUACION_CANAL_DOCUMENTAL_FIELD_KEYS = new Set<string>([
  "expediente_numero",
  "expediente_anio",
  "oficio_numero",
  "oficio_anio",
  "oficio_causa",
  "numero_oficio",
]);

/** Campos obsoletos en Editar Actuación: el backend puede rechazarlos pero no se editan en el CRUD. */
export const ACTUACION_CRUD_OBSOLETE_FIELD_KEYS = new Set<string>([
  "notificacion_previa_num",
  "comprobacion_previa_num",
]);

/** Campos que el backend puede invalidar pero no tienen control editable en el modal. */
export const ACTUACION_HIDDEN_DIALOG_FIELDS = new Set<string>([
  ...ACTUACION_CRUD_OBSOLETE_FIELD_KEYS,
  "expediente_numero",
  "expediente_anio",
  "oficio_numero",
  "oficio_anio",
  "oficio_causa",
]);

export const ACTUACION_ROW_ONLY_ERROR_KEYS = new Set<string>(["_row", "_global", "detail"]);

/**
 * Separa errores inline de mensajes de fila/global.
 *
 * Parámetros: mapa crudo ya normalizado a claves del formulario.
 * Retorno: fieldErrors para inputs + mensajes globales de fila.
 */
export function splitActuacionFormErrors(errors: Record<string, string>): {
  fieldErrors: Record<string, string>;
  rowMessages: string[];
} {
  const fieldErrors: Record<string, string> = {};
  const rowMessages: string[] = [];

  for (const [key, msg] of Object.entries(errors)) {
    const text = msg?.trim();
    if (!text) continue;
    if (ACTUACION_ROW_ONLY_ERROR_KEYS.has(key)) {
      rowMessages.push(text);
      continue;
    }
    fieldErrors[key] = text;
  }

  return { fieldErrors, rowMessages };
}

/**
 * Filtra falsos positivos de oficio/expediente en canal actas y normaliza claves API.
 *
 * @param errors Mapa crudo de errores.
 * @param options.ignoreCrudObsoleteFields Omite actas previas u otros campos no editables en CRUD.
 */
export function finalizeActuacionFormErrors(
  errors: Record<string, string>,
  options?: { ignoreCrudObsoleteFields?: boolean }
): {
  fieldErrors: Record<string, string>;
  rowMessages: string[];
} {
  const fieldErrors: Record<string, string> = {};
  const rowMessages: string[] = [];
  const ignoreObsolete = options?.ignoreCrudObsoleteFields === true;

  for (const [rawKey, rawMsg] of Object.entries(errors)) {
    const msg = rawMsg?.trim();
    if (!msg) continue;

    const key = rawKey === "numero_oficio" ? "oficio_numero" : rawKey;

    if (ignoreObsolete && ACTUACION_CRUD_OBSOLETE_FIELD_KEYS.has(key)) {
      continue;
    }

    if (ACTUACION_ROW_ONLY_ERROR_KEYS.has(key)) {
      rowMessages.push(msg);
      continue;
    }

    const isCanalDocumental = ACTUACION_CANAL_DOCUMENTAL_FIELD_KEYS.has(key);
    const isCanalRejection =
      msg.includes("no admite") ||
      msg.includes("Esperando oficio") ||
      msg.includes("Esperando expediente");

    if (isCanalDocumental && isCanalRejection) {
      rowMessages.push(
        "Esta pantalla no carga oficio ni expediente administrativo. Usá «Esperando oficio» o «Esperando expediente» si corresponde."
      );
      continue;
    }

    if (key === "oficio_numero" && (msg.includes("obligatorio") || msg.includes("obligatorios"))) {
      rowMessages.push(
        `${ACTUACION_FIELD_LABELS.oficio_numero}: ${msg} Gestioná el oficio desde «Esperando oficio», no desde el detalle de actuación.`
      );
      continue;
    }

    fieldErrors[key] = msg;
  }

  return { fieldErrors, rowMessages };
}

/**
 * Arma un resumen global accionable (nunca genérico sin nombres de campo).
 */
export function buildActuacionFormGlobalError(
  fieldErrors: Record<string, string>,
  rowMessages: string[] = []
): string | null {
  const chunks: string[] = [];
  const keys = Object.keys(fieldErrors).filter((k) => fieldErrors[k]?.trim());

  if (keys.length > 0) {
    const labels = keys.map((k) => ACTUACION_FIELD_LABELS[k] ?? k);
    chunks.push(`Revisá: ${labels.join(", ")}.`);

    const hiddenDetails = keys
      .filter((k) => ACTUACION_HIDDEN_DIALOG_FIELDS.has(k))
      .map((k) => `${ACTUACION_FIELD_LABELS[k] ?? k}: ${fieldErrors[k]}`);
    if (hiddenDetails.length > 0) {
      chunks.push(hiddenDetails.join(" "));
    }
  }

  if (rowMessages.length > 0) {
    chunks.push(...rowMessages);
  }

  return chunks.length > 0 ? chunks.join(" ") : null;
}
