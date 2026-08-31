import type { ActaCanalQuitarTipo, IActuacionListItem } from "../../../api/actuacionesListApi";
import { motivosNotificacionFromSlots } from "../../../utils/motivosNotificacionSlots";
import { isReinspeccionPorNotificacion } from "../utils/actuacionesExportPdfResumen";
/** Campos de número de acta labrada en el formulario CRUD. */
export const ACTUACION_ACTA_NUM_FIELDS = [
  "acta_inspeccion_num",
  "acta_notificacion_num",
  "acta_comprobacion_num",
  "acta_clausura_num",
  "acta_decomiso_num",
] as const;

export type ActuacionActaNumField = (typeof ACTUACION_ACTA_NUM_FIELDS)[number];

export const ACTUACION_ACTA_NUM_INVALID_MSG =
  "El número de acta debe ser numérico, de hasta 6 dígitos, sin letras ni guiones.";

export const ACTUACION_DOC_NRO_INVALID_MSG =
  "El documento o CUIT debe tener al menos 7 números, sin puntos ni guiones.";

function trim(value: unknown): string {
  if (value == null) return "";
  return String(value).trim();
}

/**
 * Valida formato de número de acta (≤6 dígitos, solo números).
 * Retorna valor normalizado con ceros a la izquierda si es válido.
 */
export function validateAndNormalizeActaNum(
  value: unknown
): { ok: true; normalized: string | null } | { ok: false; message: string } {
  const raw = trim(value);
  if (!raw) return { ok: true, normalized: null };

  if (!/^\d+$/.test(raw)) {
    return { ok: false, message: ACTUACION_ACTA_NUM_INVALID_MSG };
  }
  if (raw.length > 6) {
    return { ok: false, message: ACTUACION_ACTA_NUM_INVALID_MSG };
  }
  return { ok: true, normalized: raw.padStart(6, "0") };
}

/** Valor a persistir al salir del campo de número de acta (blur / guardar). */
export function commitActaNumInputValue(local: string): string | null {
  const trimmed = local.trim();
  if (!trimmed) return null;
  const parsed = validateAndNormalizeActaNum(trimmed);
  if (parsed.ok && parsed.normalized != null) return parsed.normalized;
  return trimmed;
}

/** Valida documento/CUIT: mínimo 7 dígitos, sin separadores. */
export function validateDocNro(value: unknown): string | null {
  const raw = trim(value);
  if (!raw) return ACTUACION_DOC_NRO_INVALID_MSG;
  if (/[^\d]/.test(raw)) return ACTUACION_DOC_NRO_INVALID_MSG;
  if (raw.length < 7) return ACTUACION_DOC_NRO_INVALID_MSG;
  return null;
}

/** Normaliza documento/CUIT a solo dígitos si cumple mínimo (≥7). */
export function normalizeDocNro(value: unknown): string | null {
  const raw = trim(value);
  if (!raw) return null;
  const digits = raw.replace(/\D/g, "");
  return digits.length >= 7 ? digits : raw;
}

/** True si hay apellido+nombre o razón social. */
export function hasTitularPersonaOrazonSocial(form: {
  contrib_apellido?: string | null;
  contrib_nombre?: string | null;
  razon_social?: string | null;
}): boolean {
  const rs = trim(form.razon_social);
  if (rs) return true;
  return Boolean(trim(form.contrib_apellido) && trim(form.contrib_nombre));
}

function motivosNotificacionVacios(row: IActuacionListItem): boolean {
  return motivosNotificacionFromSlots(
    row.notificacion_motivo_1,
    row.notificacion_motivo_2,
    row.notificacion_motivo_3
  ).length === 0;
}

/**
 * Omite actas sin datos relevantes antes del PUT (no requiere botón Eliminar).
 */
export function sanitizeEmptyActasForPut(row: IActuacionListItem): IActuacionListItem {
  const out: IActuacionListItem = { ...row };

  if (!trim(out.acta_inspeccion_num)) {
    out.acta_inspeccion_num = null;
  }

  if (!trim(out.acta_notificacion_num) && motivosNotificacionVacios(out)) {
    out.acta_notificacion_num = null;
    out.notificacion_motivo_1 = null;
    out.notificacion_motivo_2 = null;
    out.notificacion_motivo_3 = null;
  } else if (!trim(out.acta_notificacion_num)) {
    out.acta_notificacion_num = null;
  }

  if (!trim(out.acta_comprobacion_num) && !trim(out.comprobacion_motivo)) {
    out.acta_comprobacion_num = null;
    out.comprobacion_motivo = null;
  } else if (!trim(out.acta_comprobacion_num)) {
    out.acta_comprobacion_num = null;
  }

  if (!trim(out.acta_clausura_num)) {
    out.acta_clausura_num = null;
  }

  const kilos = out.decomiso_kilos_total;
  const kilosVacios = kilos == null || Number(kilos) === 0;
  if (!trim(out.acta_decomiso_num) && kilosVacios) {
    out.acta_decomiso_num = null;
    out.decomiso_kilos_total = null;
  } else if (!trim(out.acta_decomiso_num)) {
    out.acta_decomiso_num = null;
  }

  return out;
}

export type ActaClearDetection = {
  tipo: ActaCanalQuitarTipo;
  field: ActuacionActaNumField;
};

function trimActaNum(value: unknown): string {
  return trim(value);
}

/**
 * Detecta actas que existían al abrir edición y el usuario vació en el draft.
 * Requiere POST `quitar-acta` además del PUT (el mapper backend omite null y no borra).
 */
export function detectActasClearedByUser(
  original: IActuacionListItem,
  draft: IActuacionListItem
): ActaClearDetection[] {
  const cleared: ActaClearDetection[] = [];
  const skipNotificacionOrigen = isReinspeccionPorNotificacion(original);

  if (trimActaNum(original.acta_inspeccion_num) && !trimActaNum(draft.acta_inspeccion_num)) {
    cleared.push({ tipo: "INSPECCION", field: "acta_inspeccion_num" });
  }

  if (
    !skipNotificacionOrigen &&
    trimActaNum(original.acta_notificacion_num) &&
    !trimActaNum(draft.acta_notificacion_num) &&
    motivosNotificacionVacios(draft)
  ) {
    cleared.push({ tipo: "NOTIFICACION", field: "acta_notificacion_num" });
  }

  if (
    trimActaNum(original.acta_comprobacion_num) &&
    !trimActaNum(draft.acta_comprobacion_num) &&
    !trim(draft.comprobacion_motivo)
  ) {
    cleared.push({ tipo: "COMPROBACION", field: "acta_comprobacion_num" });
  }

  if (trimActaNum(original.acta_clausura_num) && !trimActaNum(draft.acta_clausura_num)) {
    cleared.push({ tipo: "CLAUSURA", field: "acta_clausura_num" });
  }

  const kilosVacios = draft.decomiso_kilos_total == null || Number(draft.decomiso_kilos_total) === 0;
  if (trimActaNum(original.acta_decomiso_num) && !trimActaNum(draft.acta_decomiso_num) && kilosVacios) {
    cleared.push({ tipo: "DECOMISO", field: "acta_decomiso_num" });
  }

  return cleared;
}

/**
 * Aplica normalizaciones de actas y documento antes de validar en backend / PUT.
 */
export function normalizeActuacionRowForCrudSubmit(row: IActuacionListItem): IActuacionListItem {
  const out = sanitizeEmptyActasForPut(row);

  const doc = normalizeDocNro(out.doc_nro);
  if (doc) out.doc_nro = doc;

  for (const key of ACTUACION_ACTA_NUM_FIELDS) {
    const current = out[key];
    const parsed = validateAndNormalizeActaNum(current);
    if (parsed.ok && parsed.normalized != null) {
      out[key] = parsed.normalized;
    } else if (parsed.ok && parsed.normalized == null) {
      out[key] = null;
    }
  }

  return out;
}
