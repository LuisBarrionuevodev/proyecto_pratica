import type { ActuacionesExportFilters } from "../../../api/actuacionesExportApi";
import type { IActuacionesListFilters, IActuacionesListMeta } from "../../../api/actuacionesListApi";
import type { BandejaPeriodMode } from "../../../utils/bandejaFiltroPeriodUi";
import { monthYearToIsoRange } from "../../../utils/bandejaFiltroPeriodUi";

export interface ActuacionesFiltroFormState {
  periodMode: BandejaPeriodMode;
  mes: number | "";
  anio: number | "";
  desde: string;
  hasta: string;
  ordenTrabajo: string;
  calleQ: string;
  documentoQ: string;
  contribuyenteQ: string;
  tipo: string;
  inspectorId: number | "";
  actaInspeccion: string;
  actaNotificacion: string;
  actaComprobacion: string;
  actaClausura: string;
  actaDecomiso: string;
}

export const ACTUACIONES_TEXTO_MIN_CHARS = 2;

const trimOpt = (value: string): string | undefined => {
  const t = value.trim();
  return t.length > 0 ? t : undefined;
};

/** Convierte meta de respuesta a filtros para paginación/refetch. */
export function actuacionesMetaToListFilters(
  meta: IActuacionesListMeta,
  overrides?: Partial<IActuacionesListFilters>
): IActuacionesListFilters {
  return {
    desde: meta.desde,
    hasta: meta.hasta,
    tipo: meta.tipo,
    contraproducencia: meta.contraproducencia,
    orden_trabajo: meta.orden_trabajo,
    actuacion_id: meta.actuacion_id ?? null,
    q: meta.q ?? null,
    calle_q: meta.calle_q ?? null,
    documento_q: meta.documento_q ?? null,
    contribuyente_q: meta.contribuyente_q ?? null,
    inspector_id: meta.inspector_id ?? null,
    acta_inspeccion: meta.acta_inspeccion ?? null,
    acta_notificacion: meta.acta_notificacion ?? null,
    acta_comprobacion: meta.acta_comprobacion ?? null,
    acta_clausura: meta.acta_clausura ?? null,
    acta_decomiso: meta.acta_decomiso ?? null,
    page: meta.page,
    page_size: meta.page_size,
    ...overrides,
  };
}

/** Resuelve período activo según modo (una sola fuente temporal). */
export function resolveActuacionesPeriod(
  form: ActuacionesFiltroFormState
): { desde: string; hasta: string } | null {
  if (form.periodMode === "month") {
    if (form.mes === "" || form.anio === "") return null;
    return monthYearToIsoRange(form.mes as number, form.anio as number);
  }
  if (!form.desde || !form.hasta) return null;
  return { desde: form.desde, hasta: form.hasta };
}

/** Hay al menos un filtro específico (no período). */
export function actuacionesHasSpecificSearch(form: ActuacionesFiltroFormState): boolean {
  return Boolean(
    trimOpt(form.ordenTrabajo) ||
      (trimOpt(form.calleQ) && form.calleQ.trim().length >= ACTUACIONES_TEXTO_MIN_CHARS) ||
      (trimOpt(form.documentoQ) && form.documentoQ.trim().length >= ACTUACIONES_TEXTO_MIN_CHARS) ||
      (trimOpt(form.contribuyenteQ) &&
        form.contribuyenteQ.trim().length >= ACTUACIONES_TEXTO_MIN_CHARS) ||
      form.tipo ||
      form.inspectorId !== "" ||
      trimOpt(form.actaInspeccion) ||
      trimOpt(form.actaNotificacion) ||
      trimOpt(form.actaComprobacion) ||
      trimOpt(form.actaClausura) ||
      trimOpt(form.actaDecomiso)
  );
}

/** El usuario completó un período válido en el modo activo. */
export function actuacionesHasPeriodChosen(form: ActuacionesFiltroFormState): boolean {
  return resolveActuacionesPeriod(form) !== null;
}

export function actuacionesFiltroFormIsValid(form: ActuacionesFiltroFormState): boolean {
  return actuacionesHasSpecificSearch(form) || actuacionesHasPeriodChosen(form);
}

/**
 * Valida el formulario y arma payload API (PERF.1-A1 / A1.1).
 * Período y filtros específicos se combinan siempre con AND cuando ambos están presentes.
 */
export function validateActuacionesFiltroForm(
  form: ActuacionesFiltroFormState
): { ok: true; payload: IActuacionesListFilters } | { ok: false; error: string } {
  if (form.periodMode === "month") {
    const partialMonth = form.mes !== "" || form.anio !== "";
    if (partialMonth && (form.mes === "" || form.anio === "")) {
      return { ok: false, error: "Indicá mes y año completos." };
    }
  }

  if (form.periodMode === "range") {
    const partialRange = Boolean(form.desde || form.hasta);
    if (partialRange && (!form.desde || !form.hasta)) {
      return { ok: false, error: "Completá las fechas desde y hasta." };
    }
    if (form.desde && form.hasta && form.desde > form.hasta) {
      return { ok: false, error: "La fecha desde no puede ser posterior a la fecha hasta." };
    }
  }

  if (!actuacionesFiltroFormIsValid(form)) {
    return {
      ok: false,
      error: "Completá al menos un filtro específico o un período y tocá Filtrar.",
    };
  }

  return { ok: true, payload: buildActuacionesFiltroPayload(form) };
}

/**
 * Arma el payload del listado: filtros específicos + período (desde/hasta) cuando corresponde.
 */
export function buildActuacionesFiltroPayload(
  form: ActuacionesFiltroFormState
): IActuacionesListFilters {
  const payload: IActuacionesListFilters = {
    orden_trabajo: trimOpt(form.ordenTrabajo) ?? null,
    actuacion_id: null,
    q: null,
  };

  const period = resolveActuacionesPeriod(form);
  if (period) {
    payload.desde = period.desde;
    payload.hasta = period.hasta;
  }

  if (form.tipo) payload.tipo = form.tipo;

  const calle = trimOpt(form.calleQ);
  if (calle && calle.length >= ACTUACIONES_TEXTO_MIN_CHARS) payload.calle_q = calle;

  const documento = trimOpt(form.documentoQ);
  if (documento && documento.length >= ACTUACIONES_TEXTO_MIN_CHARS) payload.documento_q = documento;

  const contrib = trimOpt(form.contribuyenteQ);
  if (contrib && contrib.length >= ACTUACIONES_TEXTO_MIN_CHARS) payload.contribuyente_q = contrib;

  if (form.inspectorId !== "") payload.inspector_id = form.inspectorId;

  const actaInsp = trimOpt(form.actaInspeccion);
  if (actaInsp) payload.acta_inspeccion = actaInsp;

  const actaNotif = trimOpt(form.actaNotificacion);
  if (actaNotif) payload.acta_notificacion = actaNotif;

  const actaComp = trimOpt(form.actaComprobacion);
  if (actaComp) payload.acta_comprobacion = actaComp;

  const actaClaus = trimOpt(form.actaClausura);
  if (actaClaus) payload.acta_clausura = actaClaus;

  const actaDec = trimOpt(form.actaDecomiso);
  if (actaDec) payload.acta_decomiso = actaDec;

  return payload;
}

/** Meta con filtros ancla (sin depender solo de `q`). */
export function actuacionesMetaHasAnchorFilters(meta: IActuacionesListMeta): boolean {
  return Boolean(
    meta.q ||
      meta.orden_trabajo ||
      meta.actuacion_id ||
      meta.calle_q ||
      meta.documento_q ||
      meta.contribuyente_q ||
      meta.inspector_id ||
      meta.acta_inspeccion ||
      meta.acta_notificacion ||
      meta.acta_comprobacion ||
      meta.acta_clausura ||
      meta.acta_decomiso
  );
}

export const ACTUACIONES_FILTRO_FORM_VACIO: ActuacionesFiltroFormState = {
  periodMode: "month",
  mes: "",
  anio: "",
  desde: "",
  hasta: "",
  ordenTrabajo: "",
  calleQ: "",
  documentoQ: "",
  contribuyenteQ: "",
  tipo: "",
  inspectorId: "",
  actaInspeccion: "",
  actaNotificacion: "",
  actaComprobacion: "",
  actaClausura: "",
  actaDecomiso: "",
};

export function buildActuacionesExportFiltersFromMeta(
  meta: IActuacionesListMeta,
  dialogRange?: { desde: string; hasta: string }
): ActuacionesExportFilters {
  if (actuacionesMetaHasAnchorFilters(meta)) {
    return {
      q: meta.q ?? null,
      desde: meta.desde ?? null,
      hasta: meta.hasta ?? null,
      tipo: meta.tipo,
      contraproducencia: meta.contraproducencia,
      orden_trabajo: meta.orden_trabajo,
    };
  }

  return {
    q: null,
    desde: dialogRange?.desde ?? meta.desde,
    hasta: dialogRange?.hasta ?? meta.hasta,
    tipo: meta.tipo,
    contraproducencia: meta.contraproducencia,
    orden_trabajo: meta.orden_trabajo,
  };
}
