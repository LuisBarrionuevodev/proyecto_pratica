import { pdf } from "@react-pdf/renderer";
import { saveAs } from "file-saver";

import type { IActuacionesPendientesItem } from "../../api/actuacionesPendientesApi";
import { computeNotificacionesPdfResumenRows } from "../../Containers/GestionNotificacion/utils/notificacionesExportPdfResumen";
import { buildNotificacionesVisualPdfRows } from "../../Containers/GestionNotificacion/utils/notificacionesExportVisualRows";
import type { PlazoOperativoSlice } from "../../Containers/GestionNotificacion/gestionNotificacionPlazo";
import { fechaLocalHoyIso } from "../../utils/dateRange";
import { formatExportDatePreview } from "../../utils/exportPeriodRange";
import { registerDocumentosPdfFonts } from "../core/registerPdfFonts";
import { NotificacionesListadoPdfDocument } from "../renderers/NotificacionesListadoPdfDocument";

import membretePngUrl from "../assets/membrete-smt.png?url";

export type DownloadNotificacionesPdfOptions = {
  items: IActuacionesPendientesItem[];
  desde: string;
  hasta: string;
  plazoSlice: PlazoOperativoSlice;
  filtrosResumen?: string[];
};

function buildFileName(desde: string, hasta: string): string {
  return `notificaciones_${desde}_${hasta}.pdf`;
}

function formatGeneradoEl(isoDate: string): string {
  const [y, m, d] = isoDate.split("-");
  return `${d}/${m}/${y}`;
}

/**
 * Genera y descarga PDF institucional del listado de notificaciones.
 */
export async function downloadNotificacionesListadoPdf(options: DownloadNotificacionesPdfOptions): Promise<void> {
  registerDocumentosPdfFonts();

  const rows = buildNotificacionesVisualPdfRows(options.items);
  const generadoEl = formatGeneradoEl(fechaLocalHoyIso());
  const periodoExportadoLine = `${formatExportDatePreview(options.desde)} al ${formatExportDatePreview(options.hasta)}`;
  const resumen = computeNotificacionesPdfResumenRows(options.items);

  const blob = await pdf(
    <NotificacionesListadoPdfDocument
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
