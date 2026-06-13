import {
  DEFAULT_FIELD_ERROR_SUMMARY,
  applyFormErrorsFromApi,
  mapApiErrorsToFormState,
  type FormErrorsFromApi,
} from "./parseApiError";
export type OficioAltaPayloadLike = {
  numero_oficio: string;
  fecha_oficio: string;
  juzgado_id: number;
  causa: string | null;
  numero_expediente_oficio: string;
  fecha_expediente_oficio: string;
};

/** Claves API → campos del formulario de alta (ComprobacionOficioAltaFields). */
export const OFICIO_ALTA_FIELD_ALIASES: Record<string, string> = {
  numero_oficio: "numero_oficio",
  fecha_oficio: "fecha_oficio",
  juzgado_id: "juzgado_id",
  causa: "causa",
  numero_expediente_oficio: "numero_expediente_oficio",
  numero_expediente_respuesta: "numero_expediente_oficio",
  fecha_expediente_oficio: "fecha_oficio",
  fecha_expediente_respuesta: "fecha_oficio",
};

/** Claves API → campos del modal PendientesOficioView (camelCase local). */
export const OFICIO_PENDIENTES_FIELD_ALIASES: Record<string, string> = {
  numero_oficio: "numeroOficio",
  fecha_oficio: "fechaOficio",
  juzgado_id: "juzgadoId",
  causa: "causa",
  numero_expediente_oficio: "expNumero",
  numero_expediente_respuesta: "expNumero",
  fecha_expediente_oficio: "fechaOficio",
  fecha_expediente_respuesta: "fechaOficio",
};

export const OFICIO_ALTA_ERROR_OPTIONS = {
  fieldKeyAliases: OFICIO_ALTA_FIELD_ALIASES,
  fieldErrorSummary: DEFAULT_FIELD_ERROR_SUMMARY,
  fallbackMessage: "No se pudo guardar el oficio.",
} as const;

export const OFICIO_PENDIENTES_ERROR_OPTIONS = {
  fieldKeyAliases: OFICIO_PENDIENTES_FIELD_ALIASES,
  fieldErrorSummary: DEFAULT_FIELD_ERROR_SUMMARY,
  fallbackMessage: "No se pudo cargar el oficio.",
} as const;

export function applyOficioAltaErrorsFromApi(err: unknown): FormErrorsFromApi {
  return mapApiErrorsToFormState(err, OFICIO_ALTA_ERROR_OPTIONS);
}

export function applyOficioPendientesErrorsFromApi(err: unknown): FormErrorsFromApi {
  return mapApiErrorsToFormState(err, OFICIO_PENDIENTES_ERROR_OPTIONS);
}

/** Validación cliente mínima antes de POST (alta de oficio). */
export function validateOficioAltaPayloadClient(
  payload: OficioAltaPayloadLike,
  fieldAliases: Record<string, string> = OFICIO_ALTA_FIELD_ALIASES
): Record<string, string> {
  const next: Record<string, string> = {};
  if (!payload.numero_oficio.trim()) {
    next[fieldAliases.numero_oficio] = "Completá el número de oficio.";
  }
  if (!payload.fecha_oficio) {
    next[fieldAliases.fecha_oficio] = "Completá la fecha.";
  }
  if (!payload.juzgado_id) {
    next[fieldAliases.juzgado_id] = "Seleccioná un juzgado.";
  }
  if (!payload.numero_expediente_oficio.trim()) {
    next[fieldAliases.numero_expediente_oficio] = "Completá el número de expediente de respuesta.";
  }
  return next;
}
