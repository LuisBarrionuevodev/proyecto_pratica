import type { ExportFormat } from "../../../ui/exportDataDialog.types";
import {
  fetchAllComprobacionesForExport,
  type ComprobacionesExportFilters,
} from "../../../api/comprobacionExportApi";
import { downloadComprobacionesListadoPdf } from "../../../documentos/comprobaciones/downloadComprobacionesListadoPdf";
import type { ComprobacionExportSlice } from "./comprobacionExportTypes";
import { sliceTabLabel } from "./comprobacionExportTypes";
import { downloadComprobacionesExcel } from "./downloadComprobacionesExcel";
import {
  buildRecorridoExportFiltrosResumen,
  recorridoExportFileRangeFromPayload,
  recorridoPayloadToApiParams,
  type RecorridoComprobacionFiltroPayload,
} from "./buildRecorridoComprobacionFiltroPayload";

export type ExportComprobacionesOptions = {
  format: ExportFormat;
  desde: string;
  hasta: string;
  slice: ComprobacionExportSlice;
  /** Filtros Recorrido ya aplicados en pantalla (Filtrar). */
  recorridoAppliedPayload?: RecorridoComprobacionFiltroPayload | null;
  distritoId?: number | null;
  contribuyenteQ?: string | null;
  calleQ?: string | null;
  actaComprobacion?: string | null;
  oficioNumero?: string | null;
  expedienteNumero?: string | null;
  tipoFinal?: string | null;
};

function buildFiltrosResumen(filters: ComprobacionesExportFilters): string[] {
  const out: string[] = [`Slice: ${sliceTabLabel(filters.slice)}`];
  if (filters.distritoId) out.push(`Distrito ID: ${filters.distritoId}`);
  if (filters.contribuyenteQ) out.push(`Contribuyente: ${filters.contribuyenteQ}`);
  if (filters.calleQ) out.push(`Calle: ${filters.calleQ}`);
  if (filters.actaComprobacion) out.push(`Nº comprobación: ${filters.actaComprobacion}`);
  if (filters.oficioNumero) out.push(`Nº oficio: ${filters.oficioNumero}`);
  if (filters.expedienteNumero) out.push(`Nº expediente: ${filters.expedienteNumero}`);
  if (filters.tipoFinal) out.push(`Tipo final: ${filters.tipoFinal}`);
  return out;
}

/**
 * Exporta actas de comprobación del rango indicado (fetch completo + Excel/PDF).
 * No usa filas visibles ni paginación de la grilla.
 */
export async function exportComprobacionesDataset(options: ExportComprobacionesOptions): Promise<void> {
  const useRecorridoApplied =
    options.slice === "recorrido" && options.recorridoAppliedPayload != null;

  const recorridoApiParams = useRecorridoApplied
    ? recorridoPayloadToApiParams(options.recorridoAppliedPayload!)
    : undefined;

  const fileRange = useRecorridoApplied
    ? recorridoExportFileRangeFromPayload(options.recorridoAppliedPayload!)
    : { desde: options.desde, hasta: options.hasta };

  const filters: ComprobacionesExportFilters = {
    desde: fileRange.desde,
    hasta: fileRange.hasta,
    slice: options.slice,
    recorridoApiParams,
    ...(useRecorridoApplied
      ? {}
      : {
          distritoId: options.distritoId,
          contribuyenteQ: options.contribuyenteQ,
          calleQ: options.calleQ,
          actaComprobacion: options.actaComprobacion,
          oficioNumero: options.oficioNumero,
          expedienteNumero: options.expedienteNumero,
          tipoFinal: options.tipoFinal,
        }),
  };

  const items = await fetchAllComprobacionesForExport(filters);

  if (items.length === 0) {
    throw new Error("No hay actas de comprobación para exportar con el rango y filtros seleccionados.");
  }

  const filtrosResumen = useRecorridoApplied
    ? buildRecorridoExportFiltrosResumen(options.recorridoAppliedPayload!)
    : buildFiltrosResumen(filters);

  if (options.format === "excel") {
    downloadComprobacionesExcel(items, fileRange, options.slice);
    return;
  }

  await downloadComprobacionesListadoPdf({
    items,
    desde: fileRange.desde,
    hasta: fileRange.hasta,
    slice: options.slice,
    filtrosResumen,
  });
}
