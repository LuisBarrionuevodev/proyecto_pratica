import type { ExportFormat } from "../../../ui/exportDataDialog.types";
import {
  fetchAllComprobacionesForExport,
  type ComprobacionesExportFilters,
} from "../../../api/comprobacionExportApi";
import { downloadComprobacionesListadoPdf } from "../../../documentos/comprobaciones/downloadComprobacionesListadoPdf";
import type { ComprobacionExportSlice } from "./comprobacionExportTypes";
import { sliceTabLabel } from "./comprobacionExportTypes";
import { downloadComprobacionesExcel } from "./downloadComprobacionesExcel";

export type ExportComprobacionesOptions = {
  format: ExportFormat;
  desde: string;
  hasta: string;
  slice: ComprobacionExportSlice;
  distritoId?: number | null;
  contribuyenteQ?: string | null;
  calleQ?: string | null;
  actaComprobacion?: string | null;
  oficioNumero?: string | null;
  tipoFinal?: string | null;
};

function buildFiltrosResumen(filters: ComprobacionesExportFilters): string[] {
  const out: string[] = [`Slice: ${sliceTabLabel(filters.slice)}`];
  if (filters.distritoId) out.push(`Distrito ID: ${filters.distritoId}`);
  if (filters.contribuyenteQ) out.push(`Contribuyente: ${filters.contribuyenteQ}`);
  if (filters.calleQ) out.push(`Calle: ${filters.calleQ}`);
  if (filters.actaComprobacion) out.push(`Nº comprobación: ${filters.actaComprobacion}`);
  if (filters.oficioNumero) out.push(`Nº oficio: ${filters.oficioNumero}`);
  if (filters.tipoFinal) out.push(`Tipo final: ${filters.tipoFinal}`);
  return out;
}

/**
 * Exporta actas de comprobación del rango indicado (fetch completo + Excel/PDF).
 * No usa filas visibles ni paginación de la grilla.
 */
export async function exportComprobacionesDataset(options: ExportComprobacionesOptions): Promise<void> {
  const filters: ComprobacionesExportFilters = {
    desde: options.desde,
    hasta: options.hasta,
    slice: options.slice,
    distritoId: options.distritoId,
    contribuyenteQ: options.contribuyenteQ,
    calleQ: options.calleQ,
    actaComprobacion: options.actaComprobacion,
    oficioNumero: options.oficioNumero,
    tipoFinal: options.tipoFinal,
  };

  const items = await fetchAllComprobacionesForExport(filters);

  if (items.length === 0) {
    throw new Error("No hay actas de comprobación para exportar con el rango y filtros seleccionados.");
  }

  const range = { desde: options.desde, hasta: options.hasta };

  if (options.format === "excel") {
    downloadComprobacionesExcel(items, range, options.slice);
    return;
  }

  await downloadComprobacionesListadoPdf({
    items,
    desde: options.desde,
    hasta: options.hasta,
    slice: options.slice,
    filtrosResumen: buildFiltrosResumen(filters),
  });
}
