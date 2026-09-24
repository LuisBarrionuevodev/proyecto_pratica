import type { IActuacionesPendientesItem } from "../../../api/actuacionesPendientesApi";
import type { PlazoOperativoSlice } from "../gestionNotificacionPlazo";
import {
  contribuyenteExport,
  diasRestantesText,
  domicilioLinea,
  estadoPlazoText,
  fechaVencimientoRow,
  inspectoresTexto,
  motivosNotificacionConcat,
  motivosNotificacionList,
  notificacionOrigenActaText,
  parseAnioMes,
  plazoInicialDias,
  sliceExportLabel,
} from "./notificacionesExportShared";

export type NotificacionNormalizedExcelRow = Record<string, string | number>;

function cell(value: unknown): string | number {
  if (value === null || value === undefined) return "";
  if (typeof value === "number" && !Number.isNaN(value)) return value;
  return String(value).trim();
}

export function buildNotificacionesNormalizedExcelRows(
  items: IActuacionesPendientesItem[],
  plazoSlice: PlazoOperativoSlice
): NotificacionNormalizedExcelRow[] {
  const sliceLabel = sliceExportLabel(plazoSlice);
  const motivos = (row: IActuacionesPendientesItem) => motivosNotificacionList(row);

  return items.map((row) => {
    const { anio, mes } = parseAnioMes(row.fecha_actuacion);
    const m = motivos(row);
    const plazoD = plazoInicialDias(row);

    return {
      "Fecha actuación": cell(row.fecha_actuacion),
      Año: anio,
      Mes: mes,
      "Orden de trabajo": cell(row.orden_trabajo_numero),
      "Número de notificación": cell(row.acta_notificacion_num),
      "Notificación origen": notificacionOrigenActaText(row),
      "Estado / slice": sliceLabel,
      "Estado plazo": estadoPlazoText(row),
      Contribuyente: contribuyenteExport(row),
      Documento: cell(row.doc_nro),
      Domicilio: domicilioLinea(row),
      Calle: cell(row.calle ?? row.calle_mostrar),
      Número: cell(row.numero ?? row.numero_esquina),
      Rubro: cell(row.rubro_nombre),
      "Motivo 1": cell(m[0]),
      "Motivo 2": cell(m[1]),
      "Motivo 3": cell(m[2]),
      "Motivos concatenados": motivosNotificacionConcat(row),
      "Plazo inicial (días)": plazoD ?? "",
      "Fecha vencimiento": fechaVencimientoRow(row),
      "Días restantes": diasRestantesText(row),
      "Cantidad de prórrogas": cell(row.plazos_otorgados),
      Inspectores: inspectoresTexto(row),
      "Actuación ID": cell(row.id),
      "Notificación ID": cell(row.notificacion_id),
    };
  });
}
