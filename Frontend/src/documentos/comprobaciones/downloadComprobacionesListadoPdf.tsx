import { pdf } from "@react-pdf/renderer";
import { saveAs } from "file-saver";

import { computeComprobacionesPdfResumenRows } from "../../Containers/ActasComprobacion/utils/comprobacionesExportPdfResumen";
import { buildComprobacionesVisualPdfRows } from "../../Containers/ActasComprobacion/utils/comprobacionesExportVisualRows";
import type { ComprobacionExportRow, ComprobacionExportSlice } from "../../Containers/ActasComprobacion/utils/comprobacionExportTypes";
import { fechaLocalHoyIso } from "../../utils/dateRange";
import { formatExportDatePreview } from "../../utils/exportPeriodRange";
import { registerDocumentosPdfFonts } from "../core/registerPdfFonts";
import { ComprobacionesListadoPdfDocument } from "../renderers/ComprobacionesListadoPdfDocument";

import membretePngUrl from "../assets/membrete-smt.png?url";

export type DownloadComprobacionesPdfOptions = {
  items: ComprobacionExportRow[];
  desde: string;
  hasta: string;
  slice: ComprobacionExportSlice;
  filtrosResumen?: string[];
};

function buildFileName(desde: string, hasta: string): string {
  return `comprobaciones_${desde}_${hasta}.pdf`;
}

function formatGeneradoEl(isoDate: string): string {
  const [y, m, d] = isoDate.split("-");
  return `${d}/${m}/${y}`;
}

/**
 * Genera y descarga PDF institucional del listado de actas de comprobación.
 */
export async function downloadComprobacionesListadoPdf(options: DownloadComprobacionesPdfOptions): Promise<void> {
  registerDocumentosPdfFonts();

  const rows = buildComprobacionesVisualPdfRows(options.items);
  const generadoEl = formatGeneradoEl(fechaLocalHoyIso());
  const periodoExportadoLine = `${formatExportDatePreview(options.desde)} al ${formatExportDatePreview(options.hasta)}`;
  const resumen = computeComprobacionesPdfResumenRows(options.items);

  const blob = await pdf(
    <ComprobacionesListadoPdfDocument
      model={{
        desde: options.desde,
        hasta: options.hasta,
        periodoExportadoLine,
        generadoEl,
        totalRegistros: options.items.length,
        filtrosResumen: options.filtrosResumen ?? [],
        resumen,
        rows,
      }}
      membreteSrc={membretePngUrl}
    />
  ).toBlob();

  saveAs(blob, buildFileName(options.desde, options.hasta));
}
