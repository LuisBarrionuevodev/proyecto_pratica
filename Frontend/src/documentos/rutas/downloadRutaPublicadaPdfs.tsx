import { pdf } from "@react-pdf/renderer";
import { saveAs } from "file-saver";

import { apiClient } from "../../api/apiClient";
import type { IRutaGrupoMin, IRutaItemMin, IRutaTrabajo } from "../../api/rutasTrabajoApi";
import { buildRutaPublicadaDocumentModel } from "../builders/buildRutaPublicadaDocumentModel";
import { buildOrdenTrabajoDepartamentalDocumentModel, listRutaItemsSinOtAsignada } from "../builders/buildOrdenTrabajoDepartamentalDocumentModel";
import { registerDocumentosPdfFonts } from "../core/registerPdfFonts";
import { OrdenTrabajoDepartamentalPdfDocument } from "../renderers/OrdenTrabajoDepartamentalPdfDocument";
import { OrdenesSalidaPdfDocument } from "../renderers/OrdenesSalidaPdfDocument";
import { RutaResumenPdfDocument } from "../renderers/RutaResumenPdfDocument";
import { buildOsmStaticMapUrl, computeStaticMapView, fetchStaticMapAsDataUrl } from "./osmStaticMapImage";

import logoPngUrl from "../assets/logo-smt.png?url";
import membretePngUrl from "../assets/membrete-smt.png?url";

function buildRutaPdfBasename(ruta: IRutaTrabajo): string {
  const fecha = ruta.fecha.replace(/[^\d-]/g, "") || "fecha";
  const turno =
    ruta.turno === "MANIANA"
      ? "manana"
      : ruta.turno === "TARDE"
        ? "tarde"
        : String(ruta.turno).toLowerCase().replace(/[^a-z0-9_-]/gi, "-");
  return `ruta-${ruta.numero}-id${ruta.id}-${fecha}-${turno}`;
}

/**
 * Descarga el PDF «Resumen de ruta» (membrete + datos + mini-mapa estático OSM cuando aplique).
 */
export async function downloadRutaResumenPdf(
  ruta: IRutaTrabajo,
  grupos: IRutaGrupoMin[],
  itemsActivos: IRutaItemMin[]
): Promise<void> {
  registerDocumentosPdfFonts();
  const model = buildRutaPublicadaDocumentModel(ruta, grupos, itemsActivos);
  const view = computeStaticMapView(model.puntosMapa);
  let mapImageDataUrl: string | null = null;
  if (view) {
    const size = { width: 520, height: 280 };
    const n = Math.min(view.markers.length, model.puntosMapa.length);
    const pinGrupo1Based =
      n > 0 ? model.puntosMapa.slice(0, n).map((p) => p.grupoIx + 1) : undefined;
    const pinOrden = n > 0 ? model.puntosMapa.slice(0, n).map((p) => p.ordenEnGrupo) : undefined;
    const apiBase = (apiClient.defaults.baseURL ?? "").replace(/\/+$/, "");
    const osmFull = buildOsmStaticMapUrl({ ...view, ...size, pinGrupo1Based, pinOrden });
    const search = new URL(osmFull).search;
    const proxyAbsoluteUrl = apiBase ? `${apiBase}/map/osm-static${search}` : null;
    const token = typeof localStorage !== "undefined" ? localStorage.getItem("access_token") : null;
    const proxyFetchInit: RequestInit | undefined = token
      ? { headers: { Authorization: `Bearer ${token}` } }
      : undefined;
    mapImageDataUrl = await fetchStaticMapAsDataUrl(view, size, {
      proxyAbsoluteUrl,
      proxyFetchInit,
      pinGrupo1Based,
      pinOrden,
    });
  }

  const blob = await pdf(
    <RutaResumenPdfDocument model={model} membreteSrc={membretePngUrl} mapImageDataUrl={mapImageDataUrl} />
  ).toBlob();

  saveAs(blob, `${buildRutaPdfBasename(ruta)}-resumen.pdf`);
}

/**
 * Descarga el PDF «Órdenes de salida del personal» (hasta 3 inspectores por hoja A4).
 */
export async function downloadOrdenesSalidaPdf(
  ruta: IRutaTrabajo,
  grupos: IRutaGrupoMin[],
  itemsActivos: IRutaItemMin[]
): Promise<void> {
  registerDocumentosPdfFonts();
  const model = buildRutaPublicadaDocumentModel(ruta, grupos, itemsActivos);

  const blob = await pdf(<OrdenesSalidaPdfDocument model={model} logoSrc={logoPngUrl} />).toBlob();

  saveAs(blob, `${buildRutaPdfBasename(ruta)}-ordenes-salida.pdf`);
}

/**
 * Descarga el PDF «Orden de Trabajo Departamental» (una OT por ítem; hasta 4 por hoja A4).
 */
export async function downloadOrdenTrabajoDepartamentalPdf(
  ruta: IRutaTrabajo,
  grupos: IRutaGrupoMin[],
  itemsActivos: IRutaItemMin[]
): Promise<void> {
  registerDocumentosPdfFonts();
  const model = buildOrdenTrabajoDepartamentalDocumentModel(ruta, grupos, itemsActivos);

  const blob = await pdf(
    <OrdenTrabajoDepartamentalPdfDocument model={model} logoSrc={logoPngUrl} />
  ).toBlob();

  saveAs(blob, `${buildRutaPdfBasename(ruta)}-ordenes-trabajo-departamental.pdf`);
}

export type DownloadOrdenesRutaPublicadaResult = {
  /** Ítems omitidos del PDF departamental por no tener OT asignada. */
  itemsSinOt: Array<{ itemId: number; domicilioTexto: string }>;
  /** Cantidad de órdenes de trabajo departamentales incluidas en el segundo PDF. */
  ordenesTrabajoIncluidas: number;
};

/**
 * Descarga en secuencia Orden de Salida y Órdenes de Trabajo Departamentales (dos archivos PDF).
 * Los ítems sin número de OT se omiten del segundo documento; el resultado informa cuáles fueron.
 */
export async function downloadOrdenesSalidaYTrabajoDepartamentalPdfs(
  ruta: IRutaTrabajo,
  grupos: IRutaGrupoMin[],
  itemsActivos: IRutaItemMin[]
): Promise<DownloadOrdenesRutaPublicadaResult> {
  const itemsSinOt = listRutaItemsSinOtAsignada(itemsActivos);
  const modelOt = buildOrdenTrabajoDepartamentalDocumentModel(ruta, grupos, itemsActivos);

  await downloadOrdenesSalidaPdf(ruta, grupos, itemsActivos);
  await downloadOrdenTrabajoDepartamentalPdf(ruta, grupos, itemsActivos);

  return {
    itemsSinOt,
    ordenesTrabajoIncluidas: modelOt.ordenes.length,
  };
}
