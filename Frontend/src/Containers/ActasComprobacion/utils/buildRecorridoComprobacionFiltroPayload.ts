import {
  fetchComprobacionRecorrido,
  type IComprobacionRecorridoListParams,
  type IComprobacionRecorridoListResponse,
} from "../../../api/actuacionesComprobacionActasApi";

export type RecorridoComprobacionPeriodMode = "month" | "range";

export type RecorridoComprobacionAppliedPeriod =
  | { kind: "month"; mes: number; anio: number }
  | { kind: "range"; desde: string; hasta: string }
  | { kind: "global" };

export interface RecorridoComprobacionFiltroForm {
  periodMode: RecorridoComprobacionPeriodMode;
  mes: number | "";
  anio: number | "";
  desde: string | null;
  hasta: string | null;
  distritoId: number | "";
  actaComprobacion: string;
  calleQ: string;
  contribuyenteQ: string;
  oficioNumero: string;
  expedienteNumero: string;
  tipoFinal: string;
  combinarConPeriodo: boolean;
}

export interface RecorridoComprobacionFiltroPayload {
  period: RecorridoComprobacionAppliedPeriod;
  distritoId: number | null;
  contrib_q?: string;
  calle_q?: string;
  acta_comprobacion?: string;
  oficio_numero?: string;
  expediente_numero?: string;
  tipo_final?: string;
}

function trimOpt(value: string): string | undefined {
  const t = value.trim();
  return t.length > 0 ? t : undefined;
}

export function recorridoComprobacionHasSpecificSearch(form: RecorridoComprobacionFiltroForm): boolean {
  return Boolean(
    trimOpt(form.actaComprobacion) ||
      trimOpt(form.calleQ) ||
      trimOpt(form.contribuyenteQ) ||
      trimOpt(form.oficioNumero) ||
      trimOpt(form.expedienteNumero) ||
      trimOpt(form.tipoFinal)
  );
}

export function recorridoComprobacionHasPeriodChosen(form: RecorridoComprobacionFiltroForm): boolean {
  if (form.periodMode === "month") {
    return form.mes !== "" && form.anio !== "";
  }
  return Boolean(form.desde && form.hasta);
}

export function recorridoComprobacionHasDistritoChosen(form: RecorridoComprobacionFiltroForm): boolean {
  return form.distritoId !== "";
}

function searchOptsFromForm(form: RecorridoComprobacionFiltroForm) {
  const opts: Pick<
    RecorridoComprobacionFiltroPayload,
    "contrib_q" | "calle_q" | "acta_comprobacion" | "oficio_numero" | "expediente_numero" | "tipo_final"
  > = {
    contrib_q: trimOpt(form.contribuyenteQ),
    calle_q: trimOpt(form.calleQ),
    acta_comprobacion: trimOpt(form.actaComprobacion),
    oficio_numero: trimOpt(form.oficioNumero),
    expediente_numero: trimOpt(form.expedienteNumero),
  };
  if (form.tipoFinal) opts.tipo_final = form.tipoFinal;
  return opts;
}

/**
 * Arma payload de recorrido separando búsqueda específica y período (PR8.1b).
 */
export function buildRecorridoComprobacionFiltroPayload(
  form: RecorridoComprobacionFiltroForm
): { ok: true; payload: RecorridoComprobacionFiltroPayload } | { ok: false; error: string } {
  const specific = recorridoComprobacionHasSpecificSearch(form);
  const periodChosen = recorridoComprobacionHasPeriodChosen(form);
  const distritoChosen = recorridoComprobacionHasDistritoChosen(form);
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
  const search = searchOptsFromForm(form);

  let period: RecorridoComprobacionAppliedPeriod;
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
      ...search,
    },
  };
}

export function recorridoPayloadToApiParams(
  payload: RecorridoComprobacionFiltroPayload
): IComprobacionRecorridoListParams {
  const params: IComprobacionRecorridoListParams = {
    distrito_id: payload.distritoId ?? undefined,
    contrib_q: payload.contrib_q,
    calle_q: payload.calle_q,
    acta_comprobacion: payload.acta_comprobacion,
    oficio_numero: payload.oficio_numero,
    expediente_numero: payload.expediente_numero,
    tipo_final: payload.tipo_final,
  };

  if (payload.period.kind === "month") {
    params.mes = payload.period.mes;
    params.anio = payload.period.anio;
  } else if (payload.period.kind === "range") {
    params.desde = payload.period.desde;
    params.hasta = payload.period.hasta;
  } else {
    params.omitirRangoFecha = true;
  }

  return params;
}

export async function fetchRecorridoComprobacionConPayload(
  payload: RecorridoComprobacionFiltroPayload
): Promise<IComprobacionRecorridoListResponse> {
  return fetchComprobacionRecorrido(recorridoPayloadToApiParams(payload));
}

/** Rango de fechas para nombre de archivo / encabezado PDF según período aplicado en Recorrido. */
export function recorridoExportFileRangeFromPayload(
  payload: RecorridoComprobacionFiltroPayload
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

/** Líneas de resumen de filtros aplicados en Recorrido (export PDF). */
export function buildRecorridoExportFiltrosResumen(payload: RecorridoComprobacionFiltroPayload): string[] {
  const out: string[] = ["Recorrido: filtros aplicados en pantalla"];
  const period = payload.period;
  if (period.kind === "month") {
    out.push(`Período: mes ${period.mes}/${period.anio}`);
  } else if (period.kind === "range") {
    out.push(`Período: ${period.desde} — ${period.hasta}`);
  } else {
    out.push("Período: búsqueda global (sin rango de fecha)");
  }
  if (payload.distritoId != null) out.push(`Distrito ID: ${payload.distritoId}`);
  if (payload.contrib_q) out.push(`Contribuyente: ${payload.contrib_q}`);
  if (payload.calle_q) out.push(`Calle: ${payload.calle_q}`);
  if (payload.acta_comprobacion) out.push(`Nº comprobación: ${payload.acta_comprobacion}`);
  if (payload.oficio_numero) out.push(`Nº oficio: ${payload.oficio_numero}`);
  if (payload.expediente_numero) out.push(`Nº expediente: ${payload.expediente_numero}`);
  if (payload.tipo_final) out.push(`Tipo final: ${payload.tipo_final}`);
  return out;
}
