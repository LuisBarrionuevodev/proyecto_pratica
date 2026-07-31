import type { IActuacionesPendientesItem, IPendientesOficioItem } from "../../../api/actuacionesPendientesApi";
import type {
  IComprobacionRecorridoRow,
  IReinspeccionOficioPendienteRow,
} from "../../../api/actuacionesComprobacionActasApi";
import type { ComprobacionExportRow, ComprobacionExportSlice } from "./comprobacionExportTypes";
import {
  cellStr,
  contribuyenteFromParts,
  domicilioFromParts,
  inspectoresFromParts,
} from "./comprobacionesExportShared";

function baseRow(
  slice: ComprobacionExportSlice,
  partial: Omit<ComprobacionExportRow, "exportSlice">
): ComprobacionExportRow {
  return { exportSlice: slice, ...partial };
}

/**
 * Mapea fila de pendientes de expediente (`source_type=comprobacion`).
 */
export function mapExpedientePendienteRow(row: IActuacionesPendientesItem): ComprobacionExportRow {
  return baseRow("expediente", {
    actuacionId: row.id,
    comprobacionId: row.comprobacion_id ?? null,
    fechaActuacion: cellStr(row.fecha_actuacion),
    ordenTrabajo: cellStr(row.orden_trabajo_numero),
    actaComprobacionNum: cellStr(row.acta_comprobacion_num),
    contribuyente: contribuyenteFromParts(row.contrib_apellido, row.contrib_nombre, row.razon_social),
    documento: cellStr(row.doc_nro),
    domicilio: domicilioFromParts(row.calle ?? row.calle_mostrar, row.numero ?? row.numero_esquina, row),
    calle: cellStr(row.calle ?? row.calle_mostrar),
    numero: cellStr(row.numero ?? row.numero_esquina),
    rubro: cellStr(row.rubro_nombre),
    comprobacionMotivo: cellStr(row.comprobacion_motivo),
    expedienteEnvioNumero: "",
    expedienteEnvioAnio: "",
    fechaExpedienteEnvio: "",
    oficioNumero: cellStr(row.oficio_numero),
    oficioAnio: row.oficio_anio != null ? String(row.oficio_anio) : "",
    fechaOficio: "",
    causa: cellStr(row.oficio_causa),
    juzgado: "",
    expedienteRespuestaNumero: "",
    expedienteRespuestaAnio: "",
    fechaExpedienteRespuesta: "",
    resultadoCumplimiento: cellStr(row.resultado_cumplimiento_oficio),
    estadoRecorrido: "Pendiente expediente",
    reinspeccionEstado: "",
    inspectores: inspectoresFromParts(row),
  });
}

/**
 * Mapea fila de pendientes de oficio.
 */
export function mapOficioPendienteRow(row: IPendientesOficioItem): ComprobacionExportRow {
  return baseRow("oficio", {
    actuacionId: row.id,
    comprobacionId: null,
    fechaActuacion: cellStr(row.fecha_actuacion),
    ordenTrabajo: cellStr(row.orden_trabajo_numero),
    actaComprobacionNum: cellStr(row.acta_comprobacion_num),
    contribuyente: contribuyenteFromParts(row.contrib_apellido, row.contrib_nombre, row.razon_social),
    documento: cellStr(row.doc_nro),
    domicilio: domicilioFromParts(row.calle, row.numero, row),
    calle: cellStr(row.calle),
    numero: cellStr(row.numero),
    rubro: cellStr(row.rubro_nombre),
    comprobacionMotivo: cellStr(row.comprobacion_motivo),
    expedienteEnvioNumero: cellStr(row.expediente_original_numero),
    expedienteEnvioAnio: cellStr(row.expediente_original_anio),
    fechaExpedienteEnvio: cellStr(row.expediente_original_fecha),
    oficioNumero: "",
    oficioAnio: "",
    fechaOficio: "",
    causa: "",
    juzgado: "",
    expedienteRespuestaNumero: "",
    expedienteRespuestaAnio: "",
    fechaExpedienteRespuesta: "",
    resultadoCumplimiento: "",
    estadoRecorrido: "Pendiente oficio",
    reinspeccionEstado: "",
    inspectores: inspectoresFromParts(row),
  });
}

/**
 * Mapea fila de pendientes de reinspección por oficio.
 */
export function mapReinspeccionPendienteRow(row: IReinspeccionOficioPendienteRow): ComprobacionExportRow {
  return baseRow("reinspeccion", {
    actuacionId: row.id,
    comprobacionId: null,
    fechaActuacion: cellStr(row.fecha_actuacion),
    ordenTrabajo: cellStr(row.orden_trabajo_numero),
    actaComprobacionNum: cellStr(row.acta_comprobacion_num),
    contribuyente: contribuyenteFromParts(row.contrib_apellido, row.contrib_nombre, row.razon_social),
    documento: cellStr(row.doc_nro),
    domicilio: domicilioFromParts(row.calle, row.numero, row),
    calle: cellStr(row.calle),
    numero: cellStr(row.numero),
    rubro: cellStr(row.rubro_nombre),
    comprobacionMotivo: cellStr(row.comprobacion_motivo),
    expedienteEnvioNumero: cellStr(row.expediente_envio_numero ?? row.expediente_numero),
    expedienteEnvioAnio: cellStr(row.expediente_envio_anio ?? row.expediente_anio),
    fechaExpedienteEnvio: cellStr(row.fecha_expediente_envio),
    oficioNumero: cellStr(row.oficio_numero),
    oficioAnio: row.oficio_anio != null ? String(row.oficio_anio) : "",
    fechaOficio: cellStr(row.fecha_oficio),
    causa: cellStr(row.oficio_causa),
    juzgado: cellStr(row.juzgado_nombre),
    expedienteRespuestaNumero: cellStr(row.expediente_respuesta_numero),
    expedienteRespuestaAnio: cellStr(row.expediente_respuesta_anio),
    fechaExpedienteRespuesta: cellStr(row.fecha_expediente_respuesta),
    resultadoCumplimiento: "",
    estadoRecorrido: cellStr(row.estado_recorrido) || "Pendiente reinspección",
    reinspeccionEstado: cellStr(row.documento_pendiente),
    inspectores: inspectoresFromParts(row),
  });
}

/**
 * Mapea fila del listado Recorrido.
 */
export function mapRecorridoRow(row: IComprobacionRecorridoRow): ComprobacionExportRow {
  const resultado = cellStr(
    (row as { resultado_cumplimiento_oficio?: string | null }).resultado_cumplimiento_oficio
  );
  return baseRow("recorrido", {
    actuacionId: row.id,
    comprobacionId: null,
    fechaActuacion: cellStr(row.fecha_actuacion),
    ordenTrabajo: cellStr(row.orden_trabajo_numero),
    actaComprobacionNum: cellStr(row.acta_comprobacion_num),
    contribuyente: contribuyenteFromParts(row.contrib_apellido, row.contrib_nombre, row.razon_social),
    documento: cellStr(row.doc_nro),
    domicilio: domicilioFromParts(row.calle, row.numero, row),
    calle: cellStr(row.calle),
    numero: cellStr(row.numero),
    rubro: cellStr(row.rubro_nombre),
    comprobacionMotivo: cellStr(row.comprobacion_motivo),
    expedienteEnvioNumero: cellStr(row.expediente_numero),
    expedienteEnvioAnio: row.expediente_anio != null ? String(row.expediente_anio) : "",
    fechaExpedienteEnvio: "",
    oficioNumero: cellStr(row.oficios_texto ?? row.oficio_numero),
    oficioAnio: row.oficios_texto ? "" : row.oficio_anio != null ? String(row.oficio_anio) : "",
    fechaOficio: cellStr((row as { fecha_oficio?: string | null }).fecha_oficio),
    causa: cellStr((row as { oficio_causa?: string | null }).oficio_causa),
    juzgado: cellStr((row as { juzgado_nombre?: string | null }).juzgado_nombre),
    expedienteRespuestaNumero: cellStr(row.expediente_respuesta_numero),
    expedienteRespuestaAnio: cellStr(row.expediente_respuesta_anio),
    fechaExpedienteRespuesta: "",
    resultadoCumplimiento: resultado,
    estadoRecorrido: cellStr(row.estado_recorrido),
    reinspeccionEstado: cellStr((row as { tipo_visita_resultado?: string | null }).tipo_visita_resultado),
    inspectores: inspectoresFromParts(row),
  });
}
