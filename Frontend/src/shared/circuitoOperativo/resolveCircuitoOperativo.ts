import type { IActuacionListItem } from "../../api/actuacionesListApi";

export type CircuitoOperativo =
  | "NORMAL"
  | "RELEVAMIENTO"
  | "DENUNCIA"
  | "REINSPECCION_NOTIFICACION"
  | "REINSPECCION_OFICIO";

const TIPOS_INICIADOR_OFICIO = new Set([
  "REINSPECCION_OFICIO",
  "RATIFICACION_CLAUSURA_OFICIO",
  "RATIFICACION_DECOMISO_OFICIO",
  "VERIFICAR_INFORMAR_OFICIO",
]);

const MAPA_DOCUMENTAL: Record<string, CircuitoOperativo> = {
  REINSPECCION_NOTIFICACION: "REINSPECCION_NOTIFICACION",
  REINSPECCION_OFICIO: "REINSPECCION_OFICIO",
};

export type CircuitoOperativoRowInput = Pick<
  IActuacionListItem,
  "documentacion_contexto" | "origen_reinspeccion_notificacion" | "origen_reinspeccion_oficio"
> & {
  tipo_iniciador?: string | null;
};

/**
 * Resuelve el circuito operativo canónico de una fila de actuación.
 * Prioridad: documentacion_contexto.circuito → origen RN/Oficio → NORMAL.
 */
export function resolveCircuitoOperativo(row: CircuitoOperativoRowInput): CircuitoOperativo {
  const docCircuito = row.documentacion_contexto?.circuito?.trim().toUpperCase();
  if (docCircuito && MAPA_DOCUMENTAL[docCircuito]) {
    return MAPA_DOCUMENTAL[docCircuito];
  }
  if (row.origen_reinspeccion_notificacion) {
    return "REINSPECCION_NOTIFICACION";
  }
  if (row.origen_reinspeccion_oficio) {
    return "REINSPECCION_OFICIO";
  }
  const tIni = (row.tipo_iniciador ?? "").trim().toUpperCase();
  if (tIni === "RELEVAMIENTO") return "RELEVAMIENTO";
  if (tIni === "DENUNCIA") return "DENUNCIA";
  if (tIni === "REINSPECCION_NOTIFICACION") return "REINSPECCION_NOTIFICACION";
  if (TIPOS_INICIADOR_OFICIO.has(tIni)) return "REINSPECCION_OFICIO";
  return "NORMAL";
}

/** True si el CRUD no debe exigir ni enviar identidad operativa del establecimiento. */
export function omiteIdentidadOperativa(circuito: CircuitoOperativo): boolean {
  return circuito === "REINSPECCION_NOTIFICACION" || circuito === "REINSPECCION_OFICIO";
}

export function omiteIdentidadOperativaRow(row: CircuitoOperativoRowInput): boolean {
  return omiteIdentidadOperativa(resolveCircuitoOperativo(row));
}
