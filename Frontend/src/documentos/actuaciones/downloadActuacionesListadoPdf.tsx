import { pdf } from "@react-pdf/renderer";
import { saveAs } from "file-saver";

import type { IActuacionListItem } from "../../api/actuacionesListApi";
import { computeActuacionesPdfResumenRows } from "../../Containers/Actuaciones/utils/actuacionesExportPdfResumen";
import { buildActuacionesVisualPdfRows } from "../../Containers/Actuaciones/utils/actuacionesExportVisualRows";
import { fechaLocalHoyIso } from "../../utils/dateRange";
import { formatExportDatePreview } from "../../utils/exportPeriodRange";
import { registerDocumentosPdfFonts } from "../core/registerPdfFonts";
import { ActuacionesListadoPdfDocument } from "../renderers/ActuacionesListadoPdfDocument";

import membretePngUrl from "../assets/membrete-smt.png?url";

export type DownloadActuacionesPdfOptions = {
  items: IActuacionListItem[];
  desde: string;
  hasta: string;
  filtrosResumen?: string[];
};

function buildFileName(desde: string, hasta: string): string {
  return `actuaciones_${desde}_${hasta}.pdf`;
}

function formatGeneradoEl(isoDate: string): string {
  const [y, m, d] = isoDate.split("-");
  return `${d}/${m}/${y}`;
}

/**
 * Genera y descarga PDF institucional del listado de actuaciones con resumen y detalle tipo grilla.
 */
export async function downloadActuacionesListadoPdf(options: DownloadActuacionesPdfOptions): Promise<void> {
  registerDocumentosPdfFonts();

  const rows = buildActuacionesVisualPdfRows(options.items);
  const generadoEl = formatGeneradoEl(fechaLocalHoyIso());
  const periodoExportadoLine = `${formatExportDatePreview(options.desde)} al ${formatExportDatePreview(options.hasta)}`;
  const resumen = computeActuacionesPdfResumenRows(options.items);

  const blob = await pdf(
    <ActuacionesListadoPdfDocument
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
