import type { ExportFormat } from "../../../ui/exportDataDialog.types";
import {
  fetchAllNotificacionesForExport,
  type NotificacionesExportFilters,
} from "../../../api/notificacionesExportApi";
import { downloadNotificacionesListadoPdf } from "../../../documentos/notificaciones/downloadNotificacionesListadoPdf";
import { sliceLabel, type PlazoOperativoSlice } from "../gestionNotificacionPlazo";
import { downloadNotificacionesExcel } from "./downloadNotificacionesExcel";
import {
  buildHistorialExportFiltrosResumen,
  historialExportFileRangeFromPayload,
  type HistorialNotificacionFiltroPayload,
} from "./buildHistorialNotificacionFiltroPayload";

export type ExportNotificacionesOptions = {
  format: ExportFormat;
  desde: string;
  hasta: string;
  plazoSlice: PlazoOperativoSlice;
  /** Filtros Historial ya aplicados en pantalla (Filtrar). */
  historialAppliedPayload?: HistorialNotificacionFiltroPayload | null;
  distritoId?: number | null;
  contribuyenteQ?: string | null;
  calleQ?: string | null;
  numeroNotificacion?: string | null;
  motivoQ?: string | null;
};

function buildFiltrosResumen(filters: NotificacionesExportFilters): string[] {
  const out: string[] = [];
  if (filters.plazoSlice !== "total") {
    out.push(`Slice: ${sliceLabel(filters.plazoSlice)}`);
  } else {
    out.push("Slice: Historial");
  }
  if (filters.distritoId) out.push(`Distrito ID: ${filters.distritoId}`);
  if (filters.contribuyenteQ) out.push(`Contribuyente: ${filters.contribuyenteQ}`);
  if (filters.calleQ) out.push(`Calle: ${filters.calleQ}`);
  if (filters.numeroNotificacion) out.push(`Nº notif.: ${filters.numeroNotificacion}`);
  if (filters.motivoQ) out.push(`Motivo: ${filters.motivoQ}`);
  return out;
}

/**
 * Exporta notificaciones del rango indicado (fetch completo + Excel/PDF).
 * No usa filas visibles ni paginación de la grilla.
 */
export async function exportNotificacionesDataset(options: ExportNotificacionesOptions): Promise<void> {
  const useHistorialApplied =
    options.plazoSlice === "total" && options.historialAppliedPayload != null;

  const fileRange = useHistorialApplied
    ? historialExportFileRangeFromPayload(options.historialAppliedPayload!)
    : { desde: options.desde, hasta: options.hasta };

  const filters: NotificacionesExportFilters = {
    desde: fileRange.desde,
    hasta: fileRange.hasta,
    plazoSlice: options.plazoSlice,
    historialAppliedPayload: useHistorialApplied ? options.historialAppliedPayload : undefined,
    ...(useHistorialApplied
      ? {}
      : {
          distritoId: options.distritoId,
          contribuyenteQ: options.contribuyenteQ,
          calleQ: options.calleQ,
          numeroNotificacion: options.numeroNotificacion,
          motivoQ: options.motivoQ,
        }),
  };

  const items = await fetchAllNotificacionesForExport(filters);

  if (items.length === 0) {
    throw new Error("No hay notificaciones para exportar con el rango y filtros seleccionados.");
  }

  const filtrosResumen = useHistorialApplied
    ? buildHistorialExportFiltrosResumen(options.historialAppliedPayload!)
    : buildFiltrosResumen(filters);

  if (options.format === "excel") {
    downloadNotificacionesExcel(items, fileRange, options.plazoSlice);
    return;
  }

  await downloadNotificacionesListadoPdf({
    items,
    desde: fileRange.desde,
    hasta: fileRange.hasta,
    plazoSlice: options.plazoSlice,
    filtrosResumen,
  });
}
