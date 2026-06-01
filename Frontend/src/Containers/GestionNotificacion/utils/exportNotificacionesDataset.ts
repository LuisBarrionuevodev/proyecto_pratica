import type { ExportFormat } from "../../../ui/exportDataDialog.types";
import {
  fetchAllNotificacionesForExport,
  type NotificacionesExportFilters,
} from "../../../api/notificacionesExportApi";
import { downloadNotificacionesListadoPdf } from "../../../documentos/notificaciones/downloadNotificacionesListadoPdf";
import { sliceLabel, type PlazoOperativoSlice } from "../gestionNotificacionPlazo";
import { downloadNotificacionesExcel } from "./downloadNotificacionesExcel";

export type ExportNotificacionesOptions = {
  format: ExportFormat;
  desde: string;
  hasta: string;
  plazoSlice: PlazoOperativoSlice;
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
  const filters: NotificacionesExportFilters = {
    desde: options.desde,
    hasta: options.hasta,
    plazoSlice: options.plazoSlice,
    distritoId: options.distritoId,
    contribuyenteQ: options.contribuyenteQ,
    calleQ: options.calleQ,
    numeroNotificacion: options.numeroNotificacion,
    motivoQ: options.motivoQ,
  };

  const items = await fetchAllNotificacionesForExport(filters);

  if (items.length === 0) {
    throw new Error("No hay notificaciones para exportar con el rango y filtros seleccionados.");
  }

  const range = { desde: options.desde, hasta: options.hasta };

  if (options.format === "excel") {
    downloadNotificacionesExcel(items, range, options.plazoSlice);
    return;
  }

  await downloadNotificacionesListadoPdf({
    items,
    desde: options.desde,
    hasta: options.hasta,
    plazoSlice: options.plazoSlice,
    filtrosResumen: buildFiltrosResumen(filters),
  });
}
