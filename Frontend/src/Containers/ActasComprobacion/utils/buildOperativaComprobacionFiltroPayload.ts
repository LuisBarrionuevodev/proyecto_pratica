/** Payload base de filtros operativos (fecha + Nº comprobación). */

import type { OperativaComprobacionTabKey } from "./operativaComprobacionTabChange";

export type OperativaComprobacionFiltroBase = {
  desde: string | null;
  hasta: string | null;
  numeroComprobacion: string | null;
};

export type OperativaComprobacionFiltroExpedientePayload = OperativaComprobacionFiltroBase;

export type OperativaComprobacionFiltroOficioPayload = OperativaComprobacionFiltroBase & {
  expedienteEnvioNumero: string | null;
};

export type OperativaComprobacionFiltroReinspeccionPayload = OperativaComprobacionFiltroBase & {
  numeroOficio: string | null;
  expedienteRespuestaNumero: string | null;
};

export type OperativaComprobacionFiltroPayload =
  | OperativaComprobacionFiltroExpedientePayload
  | OperativaComprobacionFiltroOficioPayload
  | OperativaComprobacionFiltroReinspeccionPayload;

export type OperativaComprobacionFiltroInputs = {
  desde: string | null;
  hasta: string | null;
  numeroComprobacion: string;
  expedienteEnvioNumero: string;
  numeroOficio: string;
  expedienteRespuestaNumero: string;
};

function trimOrNull(s: string): string | null {
  const t = s.trim();
  return t || null;
}

function baseFromInputs(input: OperativaComprobacionFiltroInputs): OperativaComprobacionFiltroBase {
  return {
    desde: input.desde?.trim() || null,
    hasta: input.hasta?.trim() || null,
    numeroComprobacion: trimOrNull(input.numeroComprobacion),
  };
}

/** Arma el payload aplicable al tab activo (solo campos del tab). */
export function buildOperativaComprobacionFiltroPayloadForTab(
  tab: OperativaComprobacionTabKey,
  input: OperativaComprobacionFiltroInputs
): OperativaComprobacionFiltroPayload {
  const base = baseFromInputs(input);
  if (tab === "oficio") {
    return { ...base, expedienteEnvioNumero: trimOrNull(input.expedienteEnvioNumero) };
  }
  if (tab === "reinspeccion") {
    return {
      ...base,
      numeroOficio: trimOrNull(input.numeroOficio),
      expedienteRespuestaNumero: trimOrNull(input.expedienteRespuestaNumero),
    };
  }
  return base;
}

/** @deprecated Usar buildOperativaComprobacionFiltroPayloadForTab. */
export function buildOperativaComprobacionFiltroPayload(input: {
  desde: string | null;
  hasta: string | null;
  numeroComprobacion: string;
}): OperativaComprobacionFiltroExpedientePayload {
  return baseFromInputs({
    ...input,
    expedienteEnvioNumero: "",
    numeroOficio: "",
    expedienteRespuestaNumero: "",
  });
}

export function operativaComprobacionTieneFiltro(
  tab: OperativaComprobacionTabKey,
  payload: OperativaComprobacionFiltroPayload | null
): boolean {
  if (!payload) return false;
  if (payload.desde || payload.hasta || payload.numeroComprobacion) return true;
  if (tab === "oficio") {
    const p = payload as OperativaComprobacionFiltroOficioPayload;
    return Boolean(p.expedienteEnvioNumero);
  }
  if (tab === "reinspeccion") {
    const p = payload as OperativaComprobacionFiltroReinspeccionPayload;
    return Boolean(p.numeroOficio || p.expedienteRespuestaNumero);
  }
  return false;
}

export function operativaComprobacionExpedienteApiOpts(
  filters: OperativaComprobacionFiltroPayload | null,
  hasDateRange: boolean
) {
  return {
    omitirRangoFecha: !hasDateRange,
    numeroComprobacion: filters?.numeroComprobacion ?? null,
  };
}

export function operativaComprobacionOficioApiOpts(
  filters: OperativaComprobacionFiltroPayload | null,
  hasDateRange: boolean
) {
  const f = filters as OperativaComprobacionFiltroOficioPayload | null;
  return {
    omitirRangoFecha: !hasDateRange,
    numeroComprobacion: filters?.numeroComprobacion ?? null,
    expedienteEnvioNumero: f?.expedienteEnvioNumero ?? null,
  };
}

export function operativaComprobacionReinspeccionApiOpts(
  filters: OperativaComprobacionFiltroPayload | null,
  hasDateRange: boolean
) {
  const f = filters as OperativaComprobacionFiltroReinspeccionPayload | null;
  return {
    omitirRangoFecha: !hasDateRange,
    numeroComprobacion: filters?.numeroComprobacion ?? null,
    numeroOficio: f?.numeroOficio ?? null,
    expedienteRespuestaNumero: f?.expedienteRespuestaNumero ?? null,
  };
}

export const EMPTY_OPERATIVA_FILTRO_INPUTS: OperativaComprobacionFiltroInputs = {
  desde: null,
  hasta: null,
  numeroComprobacion: "",
  expedienteEnvioNumero: "",
  numeroOficio: "",
  expedienteRespuestaNumero: "",
};
