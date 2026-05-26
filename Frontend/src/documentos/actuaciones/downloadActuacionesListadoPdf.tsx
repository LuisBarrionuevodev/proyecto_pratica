import { pdf } from "@react-pdf/renderer";
import { saveAs } from "file-saver";

import type { IActuacionListItem } from "../../api/actuacionesListApi";
import { fechaLocalHoyIso } from "../../utils/dateRange";
import { buildActuacionesVisualPdfRows } from "../../Containers/Actuaciones/utils/actuacionesExportVisualRows";
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
 * Genera y descarga PDF institucional del listado de actuaciones (vista compuesta).
 */
export async function downloadActuacionesListadoPdf(options: DownloadActuacionesPdfOptions): Promise<void> {
  registerDocumentosPdfFonts();

  const rows = buildActuacionesVisualPdfRows(options.items);
  const generadoEl = formatGeneradoEl(fechaLocalHoyIso());

  const blob = await pdf(
    <ActuacionesListadoPdfDocument
      model={{
        desde: options.desde,
        hasta: options.hasta,
        generadoEl,
        totalRegistros: options.items.length,
        filtrosResumen: options.filtrosResumen ?? [],
        rows,
      }}
      membreteSrc={membretePngUrl}
    />
  ).toBlob();

  saveAs(blob, buildFileName(options.desde, options.hasta));
}
