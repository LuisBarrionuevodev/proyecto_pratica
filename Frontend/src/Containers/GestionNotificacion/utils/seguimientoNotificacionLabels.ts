import type {
  IActuacionesPendientesItem,
  ISeguimientoNotificacion,
  SeguimientoNotificacionEstado,
} from "../../../api/actuacionesPendientesApi";

export function seguimientoNotificacionDeFila(
  row: IActuacionesPendientesItem | null | undefined
): ISeguimientoNotificacion {
  const seg = row?.seguimiento_notificacion;
  if (seg && typeof seg === "object") {
    return {
      estado: seg.estado ?? "SIN_REINSPECCION",
      actuacion_id: seg.actuacion_id ?? null,
      fecha_reinspeccion: seg.fecha_reinspeccion ?? null,
      acta_comprobacion_num: seg.acta_comprobacion_num ?? null,
      inspectores_texto: seg.inspectores_texto ?? null,
      faltas_subsanadas: typeof seg.faltas_subsanadas === "boolean" ? seg.faltas_subsanadas : null,
    };
  }
  return {
    estado: "SIN_REINSPECCION",
    actuacion_id: null,
    fecha_reinspeccion: null,
    acta_comprobacion_num: null,
    inspectores_texto: null,
    faltas_subsanadas: null,
  };
}

/** Chip compacto de la columna Seguimiento (historial). */
export function seguimientoNotificacionChipLabel(estado: SeguimientoNotificacionEstado | string | null | undefined): string {
  switch ((estado ?? "").toString()) {
    case "FALTAS_SUBSANADAS":
      return "Faltas subsanadas";
    case "FALTAS_NO_SUBSANADAS":
      return "Faltas no subsanadas";
    case "REINSPECCION_REALIZADA_SIN_RESULTADO":
      return "Reinspección realizada";
    default:
      return "Sin reinspección registrada";
  }
}

export function seguimientoNotificacionChipColor(
  estado: SeguimientoNotificacionEstado | string | null | undefined
): "default" | "info" | "success" | "error" {
  switch ((estado ?? "").toString()) {
    case "FALTAS_SUBSANADAS":
      return "success";
    case "FALTAS_NO_SUBSANADAS":
      return "error";
    case "REINSPECCION_REALIZADA_SIN_RESULTADO":
      return "info";
    default:
      return "default";
  }
}

/** Estado del trámite en el modal de cierre. */
export function cierreNotificacionEstadoTramiteLabel(seg: ISeguimientoNotificacion): string {
  switch (seg.estado) {
    case "FALTAS_SUBSANADAS":
      return "Faltas subsanadas";
    case "FALTAS_NO_SUBSANADAS":
      return "Faltas no subsanadas";
    case "REINSPECCION_REALIZADA_SIN_RESULTADO":
      return "Reinspección realizada · resultado no informado";
    default:
      return "Sin reinspección registrada";
  }
}

/** Resultado de las faltas: no inventa valor si no hay dato persistido. */
export function cierreNotificacionResultadoFaltasLabel(seg: ISeguimientoNotificacion): string {
  if (seg.estado === "SIN_REINSPECCION") return "—";
  if (seg.faltas_subsanadas === true) return "Subsanadas";
  if (seg.faltas_subsanadas === false) return "No subsanadas";
  return "No informado";
}

export function cierreNotificacionFilas(row: IActuacionesPendientesItem): { etiqueta: string; valor: string }[] {
  const seg = seguimientoNotificacionDeFila(row);
  const fecha =
    (seg.fecha_reinspeccion ?? "").trim() || (row.comprobacion_posterior_fecha ?? "").trim();
  const insp =
    (seg.inspectores_texto ?? "").trim() ||
    (row.comprobacion_posterior_inspectores_texto ?? "").trim();
  const acta =
    (seg.acta_comprobacion_num ?? "").trim() || (row.comprobacion_posterior_acta_num ?? "").trim();
  return [
    { etiqueta: "Estado del trámite", valor: cierreNotificacionEstadoTramiteLabel(seg) },
    { etiqueta: "Fecha de reinspección", valor: fecha || "—" },
    { etiqueta: "Inspectores", valor: insp || "—" },
    { etiqueta: "Acta de comprobación N.º", valor: acta || "—" },
    { etiqueta: "Resultado de las faltas", valor: cierreNotificacionResultadoFaltasLabel(seg) },
  ];
}
