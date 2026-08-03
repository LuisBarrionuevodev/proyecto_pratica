import type { IActuacionesPendientesItem } from "../../../api/actuacionesPendientesApi";
import {
  contribuyenteExport,
  domicilioLinea,
  estadoPlazoText,
  fechaVencimientoRow,
  motivosNotificacionConcat,
  notificacionExportPdfText,
} from "./notificacionesExportShared";

export type NotificacionVisualPdfRow = {
  fechaOt: string;
  notificacion: string;
  domicilioRubro: string;
  contribuyente: string;
  motivos: string;
  plazoVencimiento: string;
  estado: string;
};

function fechaOtText(row: IActuacionesPendientesItem): string {
  const fecha = (row.fecha_actuacion ?? "").trim() || "—";
  const ot = (row.orden_trabajo_numero ?? "").trim();
  return ot ? `${fecha} · OT ${ot}` : fecha;
}

function plazoVencimientoText(row: IActuacionesPendientesItem): string {
  const segs: string[] = [];
  const plazo = row.documentacion_contexto?.propia?.notificacion_plazo_dias;
  if (plazo != null) segs.push(`Plazo: ${plazo} días`);
  const venc = fechaVencimientoRow(row);
  if (venc) segs.push(`Vence: ${venc}`);
  const d = row.dias_restantes;
  if (d !== null && d !== undefined) {
    segs.push(d === 1 ? "1 día restante" : `${d} días restantes`);
  }
  const pr = row.plazos_otorgados;
  if (pr != null && pr > 0) {
    segs.push(pr === 1 ? "1 prórroga" : `${pr} prórrogas`);
  }
  return segs.join("\n") || "—";
}

export function buildNotificacionesVisualPdfRows(
  items: IActuacionesPendientesItem[]
): NotificacionVisualPdfRow[] {
  return items.map((row) => {
    const dom = domicilioLinea(row);
    const rubro = (row.rubro_nombre ?? "").trim();

    return {
      fechaOt: fechaOtText(row),
      notificacion: notificacionExportPdfText(row),
      domicilioRubro: rubro ? `${dom || "—"} · ${rubro}` : dom || "—",
      contribuyente: contribuyenteExport(row) || "—",
      motivos: motivosNotificacionConcat(row) || "—",
      plazoVencimiento: plazoVencimientoText(row),
      estado: estadoPlazoText(row) || "—",
    };
  });
}
