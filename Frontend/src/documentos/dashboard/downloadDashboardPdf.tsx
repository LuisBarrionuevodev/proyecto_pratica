import { pdf } from "@react-pdf/renderer";
import { saveAs } from "file-saver";

import type { DashboardExportPayload } from "../../Containers/Dashboard/utils/buildDashboardExportPayload";
import { buildDashboardPdfModel } from "../../Containers/Dashboard/utils/dashboardPdfMappers";
import { fechaLocalHoyIso } from "../../utils/dateRange";
import { formatExportDatePreview } from "../../utils/exportPeriodRange";
import { registerDocumentosPdfFonts } from "../core/registerPdfFonts";
import { DashboardIndicadoresPdfDocument } from "../renderers/DashboardIndicadoresPdfDocument";

import membretePngUrl from "../assets/membrete-smt.png?url";

export type DownloadDashboardPdfOptions = {
  payload: DashboardExportPayload;
  desde: string;
  hasta: string;
};

function formatGeneradoEl(isoDate: string): string {
  const [y, m, d] = isoDate.split("-");
  return `${d}/${m}/${y}`;
}

function buildFileName(desde: string, hasta: string): string {
  return `indicadores-operativos_${desde}_${hasta}.pdf`;
}

/**
 * Genera y descarga el PDF institucional del dashboard de indicadores.
 * Consume el mismo payload que Excel; no consulta backend adicional.
 */
export async function downloadDashboardPdf(options: DownloadDashboardPdfOptions): Promise<void> {
  registerDocumentosPdfFonts();

  const generadoEl = formatGeneradoEl(fechaLocalHoyIso());
  const periodoLine = `${formatExportDatePreview(options.desde)} al ${formatExportDatePreview(options.hasta)}`;
  const model = buildDashboardPdfModel(
    options.payload,
    options.desde,
    options.hasta,
    generadoEl,
    periodoLine
  );

  const blob = await pdf(
    <DashboardIndicadoresPdfDocument model={model} membreteSrc={membretePngUrl} />
  ).toBlob();

  saveAs(blob, buildFileName(options.desde, options.hasta));
}
