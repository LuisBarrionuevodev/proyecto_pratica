import {
  getActuacionesPendientesExpediente,
  type IActuacionesPendientesExpedienteResponse,
} from "../../../api/actuacionesPendientesApi";

export type HistorialNotificacionPeriodMode = "month" | "range";

export type HistorialNotificacionAppliedPeriod =
  | { kind: "month"; mes: number; anio: number }
  | { kind: "range"; desde: string; hasta: string }
  | { kind: "global" };

export interface HistorialNotificacionFiltroForm {
  periodMode: HistorialNotificacionPeriodMode;
  mes: number | "";
  anio: number | "";
  desde: string | null;
  hasta: string | null;
  distritoId: number | "";
  numeroNotificacion: string;
  calleQ: string;
  contribuyenteQ: string;
  motivoQ: string;
  combinarConPeriodo: boolean;
}

export interface HistorialNotificacionFiltroPayload {
  period: HistorialNotificacionAppliedPeriod;
  distritoId: number | null;
  contribuyenteQ?: string;
  calleQ?: string;
  numeroNotificacion?: string;
  motivoQ?: string;
}

function trimOpt(value: string): string | undefined {
  const t = value.trim();
  return t.length > 0 ? t : undefined;
}

/** Hay al menos un criterio de búsqueda específica (documental). */
export function historialNotificacionHasSpecificSearch(form: HistorialNotificacionFiltroForm): boolean {
  return Boolean(
    trimOpt(form.numeroNotificacion) ||
      trimOpt(form.calleQ) ||
      trimOpt(form.contribuyenteQ) ||
      trimOpt(form.motivoQ)
  );
}

/** El usuario eligió mes/año o rango desde-hasta. */
export function historialNotificacionHasPeriodChosen(form: HistorialNotificacionFiltroForm): boolean {
  if (form.periodMode === "month") {
    return form.mes !== "" && form.anio !== "";
  }
  return Boolean(form.desde && form.hasta);
}

function docOptsFromForm(form: HistorialNotificacionFiltroForm) {
  return {
    contribuyenteQ: trimOpt(form.contribuyenteQ),
    calleQ: trimOpt(form.calleQ),
    numeroNotificacion: trimOpt(form.numeroNotificacion),
    motivoQ: trimOpt(form.motivoQ),
  };
}

/**
 * Arma payload de historial separando búsqueda específica y período (PR8.1b).
 */
export function buildHistorialNotificacionFiltroPayload(
  form: HistorialNotificacionFiltroForm
): { ok: true; payload: HistorialNotificacionFiltroPayload } | { ok: false; error: string } {
  const specific = historialNotificacionHasSpecificSearch(form);
  const periodChosen = historialNotificacionHasPeriodChosen(form);
  const usePeriod = periodChosen && (!specific || form.combinarConPeriodo);

  if (!specific && !periodChosen) {
    return {
      ok: false,
      error: "Usá búsqueda específica o elegí un período y tocá Filtrar.",
    };
  }

  if (usePeriod && form.periodMode === "month") {
    if (form.mes === "" || form.anio === "" || form.mes < 1 || form.mes > 12 || form.anio < 1970) {
      return { ok: false, error: "Indicá un mes y año válidos." };
    }
  }

  if (usePeriod && form.periodMode === "range") {
    if (!form.desde || !form.hasta) {
      return { ok: false, error: "Completá las fechas desde y hasta." };
    }
    if (form.desde > form.hasta) {
      return { ok: false, error: "La fecha desde no puede ser posterior a la fecha hasta." };
    }
  }

  const distritoId = form.distritoId === "" ? null : form.distritoId;
  const doc = docOptsFromForm(form);

  let period: HistorialNotificacionAppliedPeriod;
  if (usePeriod) {
    period =
      form.periodMode === "month"
        ? { kind: "month", mes: form.mes as number, anio: form.anio as number }
        : { kind: "range", desde: form.desde!, hasta: form.hasta! };
  } else {
    period = { kind: "global" };
  }

  return {
    ok: true,
    payload: {
      period,
      distritoId,
      ...doc,
    },
  };
}

/** Ejecuta GET historial notificaciones según payload aplicado. */
export async function fetchHistorialNotificacionConPayload(
  payload: HistorialNotificacionFiltroPayload
): Promise<IActuacionesPendientesExpedienteResponse> {
  const doc = {
    contribuyenteQ: payload.contribuyenteQ,
    calleQ: payload.calleQ,
    numeroNotificacion: payload.numeroNotificacion,
    motivoQ: payload.motivoQ,
  };

  if (payload.period.kind === "month") {
    return getActuacionesPendientesExpediente(undefined, undefined, "notificacion", payload.distritoId, {
      mes: payload.period.mes,
      anio: payload.period.anio,
      ...doc,
    });
  }

  if (payload.period.kind === "range") {
    return getActuacionesPendientesExpediente(
      payload.period.desde,
      payload.period.hasta,
      "notificacion",
      payload.distritoId,
      doc
    );
  }

  return getActuacionesPendientesExpediente(undefined, undefined, "notificacion", payload.distritoId, {
    omitirRangoFecha: true,
    ...doc,
  });
}
