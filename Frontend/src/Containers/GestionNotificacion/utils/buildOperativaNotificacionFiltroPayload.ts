/** Payload de filtros operativos compartidos entre tabs de notificación (OPER-RUTA.3). */

export type OperativaNotificacionFiltroPayload = {
  desde: string | null;
  hasta: string | null;
  numeroNotificacion: string | null;
  calleQ: string | null;
};

function trimOpt(value: string): string | null {
  const t = value.trim();
  return t.length > 0 ? t : null;
}

export function buildOperativaNotificacionFiltroPayload(input: {
  desde: string | null;
  hasta: string | null;
  numeroNotificacion: string;
  calleQ: string;
}): OperativaNotificacionFiltroPayload {
  const desde = input.desde?.trim() || null;
  const hasta = input.hasta?.trim() || null;
  return {
    desde,
    hasta,
    numeroNotificacion: trimOpt(input.numeroNotificacion),
    calleQ: trimOpt(input.calleQ),
  };
}

export function operativaNotificacionTieneFiltro(payload: OperativaNotificacionFiltroPayload): boolean {
  return Boolean(
    payload.desde || payload.hasta || payload.numeroNotificacion || payload.calleQ
  );
}

/** Valores vacíos de campos de búsqueda operativa (Nº notificación + Calle). */
export const OPERATIVA_FILTRO_BUSQUEDA_VACIA = {
  numeroNotificacion: "",
  calleQ: "",
} as const;
