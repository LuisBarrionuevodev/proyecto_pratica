/** Payload de filtros operativos compartidos entre tabs pendientes de comprobación (OPER-RUTA.4). */

export type OperativaComprobacionFiltroPayload = {
  desde: string | null;
  hasta: string | null;
  numeroComprobacion: string | null;
};

export function buildOperativaComprobacionFiltroPayload(input: {
  desde: string | null;
  hasta: string | null;
  numeroComprobacion: string;
}): OperativaComprobacionFiltroPayload {
  const desde = input.desde?.trim() || null;
  const hasta = input.hasta?.trim() || null;
  const numeroComprobacion = input.numeroComprobacion.trim() || null;
  return { desde, hasta, numeroComprobacion };
}

export function operativaComprobacionTieneFiltro(payload: OperativaComprobacionFiltroPayload): boolean {
  return Boolean(payload.desde || payload.hasta || payload.numeroComprobacion);
}
