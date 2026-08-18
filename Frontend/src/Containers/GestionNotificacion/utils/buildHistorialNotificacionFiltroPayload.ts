import {
  getActuacionesPendientesExpediente,
  type IActuacionesPendientesExpedienteOpts,
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

/** Distrito seleccionado en el filtro. */
export function historialNotificacionHasDistritoChosen(form: HistorialNotificacionFiltroForm): boolean {
  return form.distritoId !== "";
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
  const distritoChosen = historialNotificacionHasDistritoChosen(form);
  const usePeriod = periodChosen && (!specific || form.combinarConPeriodo);

  if (!specific && !periodChosen && !distritoChosen) {
    return {
      ok: false,
      error: "Usá búsqueda específica, elegí un período o seleccioná un distrito y tocá Filtrar.",
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

export type HistorialNotificacionExpedienteCall = {
  desde?: string | null;
  hasta?: string | null;
  distritoId: number | null;
  opts: IActuacionesPendientesExpedienteOpts;
};

function docOptsFromPayload(payload: HistorialNotificacionFiltroPayload): IActuacionesPendientesExpedienteOpts {
  return {
    contribuyenteQ: payload.contribuyenteQ,
    calleQ: payload.calleQ,
    numeroNotificacion: payload.numeroNotificacion,
    motivoQ: payload.motivoQ,
  };
}

/** Params de `GET /actuaciones/pendientes/expediente` equivalentes al listado Historial. */
export function historialPayloadToExpedienteCall(
  payload: HistorialNotificacionFiltroPayload
): HistorialNotificacionExpedienteCall {
  const doc = docOptsFromPayload(payload);

  if (payload.period.kind === "month") {
    return {
      distritoId: payload.distritoId,
      opts: {
        mes: payload.period.mes,
        anio: payload.period.anio,
        ...doc,
      },
    };
  }

  if (payload.period.kind === "range") {
    return {
      desde: payload.period.desde,
      hasta: payload.period.hasta,
      distritoId: payload.distritoId,
      opts: doc,
    };
  }

  return {
    distritoId: payload.distritoId,
    opts: {
      omitirRangoFecha: true,
      ...doc,
    },
  };
}

/** Rango de fechas para nombre de archivo / encabezado PDF según período aplicado en Historial. */
export function historialExportFileRangeFromPayload(
  payload: HistorialNotificacionFiltroPayload
): { desde: string; hasta: string } {
  const period = payload.period;
  if (period.kind === "month") {
    const m = String(period.mes).padStart(2, "0");
    const lastDay = new Date(period.anio, period.mes, 0).getDate();
    return {
      desde: `${period.anio}-${m}-01`,
      hasta: `${period.anio}-${m}-${String(lastDay).padStart(2, "0")}`,
    };
  }
  if (period.kind === "range") {
    return { desde: period.desde, hasta: period.hasta };
  }
  const today = new Date().toISOString().slice(0, 10);
  return { desde: today, hasta: today };
}

/** Líneas de resumen de filtros aplicados en Historial (export PDF). */
export function buildHistorialExportFiltrosResumen(payload: HistorialNotificacionFiltroPayload): string[] {
  const out: string[] = ["Historial: filtros aplicados en pantalla"];
  const period = payload.period;
  if (period.kind === "month") {
    out.push(`Período: mes ${period.mes}/${period.anio} (acta de notificación)`);
  } else if (period.kind === "range") {
    out.push(`Período: ${period.desde} — ${period.hasta}`);
  } else {
    out.push("Período: búsqueda global (sin rango de fecha)");
  }
  if (payload.distritoId != null) out.push(`Distrito ID: ${payload.distritoId}`);
  if (payload.contribuyenteQ) out.push(`Contribuyente: ${payload.contribuyenteQ}`);
  if (payload.calleQ) out.push(`Calle: ${payload.calleQ}`);
  if (payload.numeroNotificacion) out.push(`Nº notif.: ${payload.numeroNotificacion}`);
  if (payload.motivoQ) out.push(`Motivo: ${payload.motivoQ}`);
  return out;
}

/** Ejecuta GET historial notificaciones según payload aplicado. */
export async function fetchHistorialNotificacionConPayload(
  payload: HistorialNotificacionFiltroPayload
): Promise<IActuacionesPendientesExpedienteResponse> {
  const call = historialPayloadToExpedienteCall(payload);
  return getActuacionesPendientesExpediente(
    call.desde,
    call.hasta,
    "notificacion",
    call.distritoId,
    call.opts
  );
}
